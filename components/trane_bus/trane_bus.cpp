#include "trane_bus.h"

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

namespace esphome {
namespace trane_bus {

static const char *const TAG = "trane_bus";
static constexpr size_t MAX_JSON_PAYLOAD = 512;
static constexpr uint32_t INTER_FRAME_DELAY_MS = 2;

void TraneBus::setup() {
  if (canbus_ == nullptr) {
    ESP_LOGE(TAG, "CAN bus is not configured");
    this->mark_failed();
    return;
  }

  canbus_->add_callback([this](uint32_t can_id, bool extended_id, bool rtr, const std::vector<uint8_t> &data) {
    this->on_can_frame_(can_id, extended_id, rtr, data);
  });
}

void TraneBus::loop() {
  if (pending_ack_ && (millis() - pending_ack_since_ms_) > ack_timeout_ms_) {
    ESP_LOGW(TAG, "Timed out waiting for SC360 ACK for %s", pending_kind_.c_str());
    ack_timeouts_++;
    clear_pending_ack_();
  }
}

void TraneBus::dump_config() {
  ESP_LOGCONFIG(TAG, "Trane Link transport:");
  ESP_LOGCONFIG(TAG, "  Command CAN ID: 0x%03" PRIX32, command_can_id_);
  ESP_LOGCONFIG(TAG, "  TX enabled: %s", YESNO(tx_enabled_));
  ESP_LOGCONFIG(TAG, "  Raw JSON enabled: %s", YESNO(raw_json_enabled_));
  ESP_LOGCONFIG(TAG, "  Require SC360 before TX: %s", YESNO(require_sc360_before_tx_));
  ESP_LOGCONFIG(TAG, "  Bus activity timeout: %u ms", static_cast<unsigned>(bus_activity_timeout_ms_));
  ESP_LOGCONFIG(TAG, "  ACK timeout: %u ms", static_cast<unsigned>(ack_timeout_ms_));
  ESP_LOGCONFIG(TAG, "  Setpoint bounds: %.1f..%.1f degF, min deadband %.1f degF", setpoint_min_f_, setpoint_max_f_,
                min_deadband_f_);
  ESP_LOGCONFIG(TAG, "  Max JSON payload: %u bytes", static_cast<unsigned>(MAX_JSON_PAYLOAD));
}

bool TraneBus::has_recent_trane_activity() const {
  return seen_sc360_ && last_sc360_frame_ms_ != 0 && (millis() - last_sc360_frame_ms_) <= bus_activity_timeout_ms_;
}

bool TraneBus::is_known_trane_id_(uint32_t can_id) const {
  if (can_id == 0x641 || can_id == 0x649 || can_id == 0x5C1 || can_id == 0x5C9 || can_id == 0x283 ||
      can_id == 0x308 || can_id == 0x490 || can_id == 0x410 || can_id == 0x430 || can_id == 0x450)
    return true;
  return can_id >= 0x380 && can_id <= 0x38F;
}

void TraneBus::on_can_frame_(uint32_t can_id, bool extended_id, bool rtr, const std::vector<uint8_t> &data) {
  rx_frames_++;
  if (extended_id || rtr)
    return;

  if (is_known_trane_id_(can_id)) {
    trane_frames_++;
    last_trane_frame_ms_ = millis();
  }

  if (can_id == 0x649 || can_id == 0x641 || can_id == 0x5C9) {
    seen_sc360_ = true;
    sc360_frames_++;
    last_sc360_frame_ms_ = millis();
  }

  if (can_id == 0x641)
    handle_641_frame_(data);
}

void TraneBus::handle_641_frame_(const std::vector<uint8_t> &data) {
  if (data.empty())
    return;

  const uint8_t marker = data[0];
  if ((marker & 0xF0) == 0xC0) {
    rx_641_buf_.clear();
    rx_641_expected_seq_ = 1;
    rx_641_expected_len_ = data.size() >= 3 ? static_cast<size_t>(data[1]) | (static_cast<size_t>(data[2]) << 8) : 0;
    if (rx_641_expected_len_ > MAX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      rx_641_buf_.clear();
      rx_641_expected_len_ = 0;
      return;
    }
    for (size_t i = 5; i < data.size() && rx_641_buf_.size() < rx_641_expected_len_; i++) {
      if (data[i] != 0)
        rx_641_buf_.push_back(static_cast<char>(data[i]));
    }
    return;
  }

  if (rx_641_expected_len_ == 0)
    return;

  if (marker & 0x80) {
    size_t used = (marker & 0x7F);
    if (used == 0) {
      rx_transport_errors_++;
      return;
    }
    used -= 1;
    for (size_t i = 1; i < data.size() && i <= used && rx_641_buf_.size() < rx_641_expected_len_; i++) {
      if (data[i] == 0)
        break;
      rx_641_buf_.push_back(static_cast<char>(data[i]));
    }

    if (rx_641_buf_.size() == rx_641_expected_len_)
      handle_641_message_(rx_641_buf_);
    else
      rx_transport_errors_++;

    rx_641_buf_.clear();
    rx_641_expected_len_ = 0;
    rx_641_expected_seq_ = 1;
    return;
  }

  if (marker != rx_641_expected_seq_) {
    rx_transport_errors_++;
    rx_641_buf_.clear();
    rx_641_expected_len_ = 0;
    rx_641_expected_seq_ = 1;
    return;
  }
  rx_641_expected_seq_++;

  for (size_t i = 1; i < data.size() && rx_641_buf_.size() < rx_641_expected_len_; i++) {
    if (data[i] == 0)
      break;
    rx_641_buf_.push_back(static_cast<char>(data[i]));
  }
}

void TraneBus::handle_641_message_(const std::string &json) {
  const auto ack_pos = json.find("\"Ack\":");
  if (ack_pos == std::string::npos || !pending_ack_)
    return;

  if (json.find("200", ack_pos) != std::string::npos) {
    ack_ok_++;
    ESP_LOGI(TAG, "SC360 acknowledged %s", pending_kind_.c_str());
  } else {
    ack_error_++;
    ESP_LOGW(TAG, "SC360 returned non-200 ACK for %s: %s", pending_kind_.c_str(), json.c_str());
  }
  clear_pending_ack_();
}

void TraneBus::clear_pending_ack_() {
  pending_ack_ = false;
  pending_ack_since_ms_ = 0;
  pending_kind_.clear();
}

bool TraneBus::send_frame_(const std::vector<uint8_t> &frame) {
  if (canbus_ == nullptr) {
    ESP_LOGE(TAG, "Cannot transmit: CAN bus is not configured");
    tx_errors_++;
    return false;
  }

  const canbus::Error result = canbus_->send_data(command_can_id_, false, frame);
  if (result != canbus::ERROR_OK) {
    ESP_LOGE(TAG, "CAN transmit failed on 0x%03" PRIX32 " with error %u", command_can_id_,
             static_cast<unsigned>(result));
    tx_errors_++;
    return false;
  }

  tx_frames_++;
  return true;
}

bool TraneBus::validate_payload_shape_(const std::string &payload) const {
  return payload.size() >= 2 && payload.front() == '{' && payload.back() == '}';
}

bool TraneBus::validate_profile_name_(const std::string &profile) const {
  static const char *const ALLOWED[] = {"SYSOP", "INDOOR", "ZONE", "ALARMS", "SPOVERRIDE", "PRESET", "SYSTEM",
                                         "SCHEDULE", "VERSION", "ZONECARD", "ZONING", "WEATHERDATA", "UNITID"};
  for (const char *allowed : ALLOWED) {
    if (profile == allowed)
      return true;
  }
  return false;
}

bool TraneBus::send_json_internal_(const std::string &payload, bool expect_ack, const char *kind) {
  tx_attempts_++;

  if (!tx_enabled_) {
    tx_blocked_++;
    ESP_LOGW(TAG, "TX blocked (monitor-only mode): %s", kind);
    return false;
  }

  if (require_sc360_before_tx_ && !has_recent_trane_activity()) {
    tx_blocked_++;
    ESP_LOGW(TAG, "TX blocked: no recent SC360 activity observed");
    return false;
  }

  if (pending_ack_) {
    tx_busy_blocked_++;
    ESP_LOGW(TAG, "TX blocked: waiting for ACK for %s", pending_kind_.c_str());
    return false;
  }

  if (!validate_payload_shape_(payload) || payload.size() > MAX_JSON_PAYLOAD) {
    tx_errors_++;
    ESP_LOGE(TAG, "Refusing malformed or oversized JSON payload for %s", kind);
    return false;
  }

  const uint32_t total = static_cast<uint32_t>(payload.size());
  std::vector<uint8_t> header = {0xC2, static_cast<uint8_t>(total & 0xFF), static_cast<uint8_t>((total >> 8) & 0xFF),
                                 0x00, 0x00, 0x00, 0x00, 0x00};
  if (!send_frame_(header))
    return false;

  delay(INTER_FRAME_DELAY_MS);
  size_t offset = 0;
  uint8_t seq = 1;
  while (offset < payload.size()) {
    const size_t remaining = payload.size() - offset;
    std::vector<uint8_t> frame(8, 0);
    if (remaining <= 7) {
      frame[0] = static_cast<uint8_t>(0x80 | (remaining + 1));
      std::copy_n(payload.begin() + offset, remaining, frame.begin() + 1);
      if (!send_frame_(frame))
        return false;
      offset += remaining;
    } else {
      frame[0] = seq++;
      std::copy_n(payload.begin() + offset, 7, frame.begin() + 1);
      if (!send_frame_(frame))
        return false;
      offset += 7;
      delay(INTER_FRAME_DELAY_MS);
    }
  }

  tx_messages_++;
  if (expect_ack) {
    pending_ack_ = true;
    pending_ack_since_ms_ = millis();
    pending_kind_ = kind;
  }
  ESP_LOGI(TAG, "Transmitted %s on 0x%03" PRIX32, kind, command_can_id_);
  return true;
}

bool TraneBus::send_json(const std::string &payload) {
  if (!raw_json_enabled_) {
    tx_blocked_++;
    ESP_LOGW(TAG, "Raw JSON transmit is disabled");
    return false;
  }
  return send_json_internal_(payload, true, "raw-json");
}

bool TraneBus::set_system_mode(const std::string &mode) {
  const char *value = nullptr;
  if (mode == "heat")
    value = "A";
  else if (mode == "cool")
    value = "B";
  else if (mode == "off")
    value = "C";
  else {
    ESP_LOGW(TAG, "Refusing unsupported Trane system mode: %s", mode.c_str());
    tx_errors_++;
    return false;
  }

  char payload[64];
  snprintf(payload, sizeof(payload), "{\"SystemMode\":{\"Put\":{\"B\":\"%s\"}}}", value);
  return send_json_internal_(payload, true, "system-mode");
}

bool TraneBus::set_setpoints(float heat_f, float cool_f, int zone, int hold_type, int source) {
  if (!std::isfinite(heat_f) || !std::isfinite(cool_f) || heat_f < setpoint_min_f_ || cool_f > setpoint_max_f_ ||
      cool_f - heat_f < min_deadband_f_ || zone < 1 || zone > 6 || hold_type < 0 || hold_type > 2 || source < 0 ||
      source > 2) {
    ESP_LOGW(TAG, "Refusing invalid setpoint request: heat=%.1f cool=%.1f zone=%d hold=%d source=%d", heat_f, cool_f,
             zone, hold_type, source);
    tx_errors_++;
    return false;
  }

  char payload[180];
  snprintf(payload, sizeof(payload),
           "{\"SpOverride\":{\"Put\":{\"%d\":{\"Hsp\":\"%.0f\",\"Csp\":\"%.0f\",\"HoldType\":\"%d\",\"Source\":\"%d\"}}}}",
           zone, heat_f, cool_f, hold_type, source);
  return send_json_internal_(payload, true, "setpoints");
}

bool TraneBus::request_profile(const std::string &profile) {
  if (!validate_profile_name_(profile)) {
    ESP_LOGW(TAG, "Refusing unknown profile request: %s", profile.c_str());
    tx_errors_++;
    return false;
  }
  std::string payload = "{\"GetProfile\":\"" + profile + "\"}";
  return send_json_internal_(payload, false, "get-profile");
}

}  // namespace trane_bus
}  // namespace esphome
