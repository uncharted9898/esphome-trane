#include "trane_climate.h"
#include "esphome/core/log.h"

#include <cmath>

namespace esphome {
namespace trane_hvac {

static const char *const TAG = "trane_hvac.climate";

bool TraneClimate::is_supported_control_mode_(climate::ClimateMode mode) {
  return mode == climate::CLIMATE_MODE_OFF ||
         mode == climate::CLIMATE_MODE_HEAT ||
         mode == climate::CLIMATE_MODE_COOL;
}

bool TraneClimate::apply_observed_mode_(const std::string &state) {
  if (state == "heat") {
    this->mode = climate::CLIMATE_MODE_HEAT;
  } else if (state == "cool") {
    this->mode = climate::CLIMATE_MODE_COOL;
  } else if (state == "off") {
    this->mode = climate::CLIMATE_MODE_OFF;
  } else {
    return false;
  }
  return true;
}

void TraneClimate::dump_config() {
  LOG_CLIMATE("", "Trane HVAC Climate", this);
  ESP_LOGCONFIG(TAG, "Control state: observed/SC360-authoritative (non-optimistic)");
}

climate::ClimateTraits TraneClimate::traits() {
  auto traits = climate::ClimateTraits();
  traits.add_feature_flags(climate::CLIMATE_SUPPORTS_CURRENT_TEMPERATURE |
                           climate::CLIMATE_REQUIRES_TWO_POINT_TARGET_TEMPERATURE |
                           climate::CLIMATE_SUPPORTS_ACTION);

  // Only expose modes whose actual SystemMode commands are decoded and verified.
  // In particular, do not advertise HEAT_COOL or FAN_ONLY: the legacy YAML
  // fallback maps unknown modes to SystemMode=C (off).
  traits.set_supported_modes({
    climate::CLIMATE_MODE_OFF,
    climate::CLIMATE_MODE_HEAT,
    climate::CLIMATE_MODE_COOL,
  });

  // Home/Away/Sleep/Boost were previously implemented as manual SpOverride
  // setpoints, not as native Trane presets. Do not advertise misleading presets.
  traits.set_visual_min_temperature(15.5f);   // 60 degF
  traits.set_visual_max_temperature(29.4f);   // 85 degF
  traits.set_visual_target_temperature_step(0.5f);
  traits.set_visual_current_temperature_step(0.1f);
  return traits;
}

void TraneClimate::setup() {
  if (current_temp_sensor_ != nullptr) {
    current_temp_sensor_->add_on_state_callback([this](float state) {
      if (!std::isnan(state)) {
        this->current_temperature = (state - 32.0f) * 5.0f / 9.0f;
        this->publish_state();
      }
    });
  }

  if (heat_setpoint_sensor_ != nullptr) {
    heat_setpoint_sensor_->add_on_state_callback([this](float state) {
      if (!std::isnan(state)) {
        this->target_temperature_low = (state - 32.0f) * 5.0f / 9.0f;
        this->publish_state();
      }
    });
  }

  if (cool_setpoint_sensor_ != nullptr) {
    cool_setpoint_sensor_->add_on_state_callback([this](float state) {
      if (!std::isnan(state)) {
        this->target_temperature_high = (state - 32.0f) * 5.0f / 9.0f;
        this->publish_state();
      }
    });
  }

  if (mode_sensor_ != nullptr) {
    mode_sensor_->add_on_state_callback([this](const std::string &state) {
      if (!this->apply_observed_mode_(state)) {
        ESP_LOGW(TAG, "Ignoring unknown observed system mode '%s'", state.c_str());
        return;
      }
      this->publish_state();
    });
  }

  // Demand stage sensor -- maps SystemOpStatus.C to ClimateAction.
  if (demand_sensor_ != nullptr) {
    demand_sensor_->add_on_state_callback([this](const std::string &state) {
      if (this->mode == climate::CLIMATE_MODE_OFF) {
        this->action = climate::CLIMATE_ACTION_OFF;
      } else if (state == "--" || state.empty()) {
        this->action = climate::CLIMATE_ACTION_IDLE;
      } else if (state.find("Cool") != std::string::npos) {
        this->action = climate::CLIMATE_ACTION_COOLING;
      } else if (state.find("HP") != std::string::npos ||
                 state.find("ID") != std::string::npos) {
        this->action = (this->mode == climate::CLIMATE_MODE_COOL)
                         ? climate::CLIMATE_ACTION_COOLING
                         : climate::CLIMATE_ACTION_HEATING;
      } else {
        this->action = climate::CLIMATE_ACTION_IDLE;
      }
      this->publish_state();
    });
  }

  if (indoor_unit_state_sensor_ != nullptr) {
    indoor_unit_state_sensor_->add_on_state_callback([this](const std::string &state) {
      if (state == "B" && this->action == climate::CLIMATE_ACTION_IDLE) {
        this->action = climate::CLIMATE_ACTION_FAN;
        this->publish_state();
      } else if (state == "A" && this->action == climate::CLIMATE_ACTION_FAN) {
        this->action = climate::CLIMATE_ACTION_IDLE;
        this->publish_state();
      }
    });
  }

  // Seed only directly observed sensor values. Requested control values never
  // become climate state until the bus publishes the resulting SC360 state.
  if (current_temp_sensor_ != nullptr && !std::isnan(current_temp_sensor_->state))
    this->current_temperature = (current_temp_sensor_->state - 32.0f) * 5.0f / 9.0f;
  if (heat_setpoint_sensor_ != nullptr && !std::isnan(heat_setpoint_sensor_->state))
    this->target_temperature_low = (heat_setpoint_sensor_->state - 32.0f) * 5.0f / 9.0f;
  if (cool_setpoint_sensor_ != nullptr && !std::isnan(cool_setpoint_sensor_->state))
    this->target_temperature_high = (cool_setpoint_sensor_->state - 32.0f) * 5.0f / 9.0f;
}

void TraneClimate::control(const climate::ClimateCall &call) {
  // Requests are deliberately non-optimistic. The UX360 and SC360 remain
  // authoritative; state is updated only when observed back from the CAN bus.
  if (call.get_mode().has_value()) {
    const climate::ClimateMode requested_mode = *call.get_mode();
    if (!is_supported_control_mode_(requested_mode)) {
      ESP_LOGW(TAG, "Rejecting unsupported climate mode request: %d",
               static_cast<int>(requested_mode));
    } else {
      ESP_LOGI(TAG, "Requesting climate mode %d; waiting for SC360 echo",
               static_cast<int>(requested_mode));
      mode_trigger_.trigger(requested_mode);
    }
  }

  if (call.get_target_temperature_low().has_value() ||
      call.get_target_temperature_high().has_value()) {
    float hsp_c = this->target_temperature_low;
    float csp_c = this->target_temperature_high;
    if (call.get_target_temperature_low().has_value())
      hsp_c = *call.get_target_temperature_low();
    if (call.get_target_temperature_high().has_value())
      csp_c = *call.get_target_temperature_high();

    if (std::isnan(hsp_c) || std::isnan(csp_c)) {
      ESP_LOGW(TAG, "Rejecting setpoint request before both observed setpoints are known");
    } else if (hsp_c > csp_c) {
      ESP_LOGW(TAG, "Rejecting inverted setpoints: heat %.2f C > cool %.2f C", hsp_c, csp_c);
    } else {
      const float hsp_f = hsp_c * 9.0f / 5.0f + 32.0f;
      const float csp_f = csp_c * 9.0f / 5.0f + 32.0f;
      ESP_LOGI(TAG, "Requesting setpoints Hsp=%.0f degF Csp=%.0f degF; waiting for SC360 echo",
               hsp_f, csp_f);
      temperature_trigger_.trigger(hsp_f, csp_f);
    }
  }

  if (call.get_preset().has_value()) {
    ESP_LOGW(TAG, "Ignoring preset request: native Trane preset command is not decoded yet");
  }
}

}  // namespace trane_hvac
}  // namespace esphome
