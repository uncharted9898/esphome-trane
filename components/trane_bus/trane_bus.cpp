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

  if (capture_capacity_ > 0)
    capture_frames_.reserve(capture_capacity_);

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
  ESP_LOGCONFIG(TAG, "  Capture: %s, capacity %u frames", YESNO(capture_enabled_),
                static_cast<unsigned>(capture_capacity_));
}

bool TraneBus::has_recent_trane_activity() const {
  return seen_sc360_ && last_sc360_frame_ms_ != 0 && (millis() - last_sc360_frame_ms_) <= bus_activity_timeout_ms_;
}

void TraneBus::start_capture(bool clear_first) {
  if (clear_first)
    clear_capture();
  if (capture_capacity_ == 0) {
    ESP_LOGW(TAG, "Capture cannot start: capture_capacity is 0");
    return;
  }
  capture_enabled_ = true;
  ESP_LOGI(TAG, "CAN capture started (%u-frame ring)", static_cast<unsigned>(capture_capacity_));
}

void TraneBus::clear_capture() {
  capture_frames_.clear();
  capture_write_index_ = 0;
  capture_overwrites_ = 0;
}

void TraneBus::dump_capture() const {
  ESP_LOGI(TAG, "TRANE_CAPTURE_BEGIN frames=%u overwrites=%u", static_cast<unsigned>(capture_frames_.size()),
           static_cast<unsigned>(capture_overwrites_));
  if (capture_frames_.empty()) {
    ESP_LOGI(TAG, "TRANE_CAPTURE_END");
    return;
  }

  const bool wrapped = capture_frames_.size() == capture_capacity_ && capture_overwrites_ > 0;
  const size_t start = wrapped ? capture_write_index_ : 0;
  for (size_t n = 0; n < capture_frames_.size(); n++) {
    const CapturedFrame &frame = capture_frames_[(start + n) % capture_frames_.size()];
    char bytes[25] = {0};
    size_t pos = 0;
    for (uint8_t i = 0; i < frame.dlc && i < 8 && pos + 3 < sizeof(bytes); i++)
      pos += snprintf(bytes + pos, sizeof(bytes) - pos, "%02X", frame.data[i]);
    ESP_LOGI(TAG, "TRANE_CAN,%lu,%03lX,%u,%s", static_cast<unsigned long>(frame.timestamp_ms),
             static_cast<unsigned long>(frame.can_id), static_cast<unsigned>(frame.dlc), bytes);
  }
  ESP_LOGI(TAG, "TRANE_CAPTURE_END");
}

bool TraneBus::is_known_trane_id_(uint32_t can_id) const {
  if (can_id == 0x641 || can_id == 0x649 || can_id == 0x5C1 || can_id == 0x5C9 || can_id == 0x283 ||
      can_id == 0x308 || can_id == 0x490 || can_id == 0x410 || can_id == 0x430 || can_id == 0x450)
    return true;
  return can_id >= 0x380 && can_id <= 0x38F;
}

void TraneBus::capture_frame_(uint32_t can_id, const std::vector<uint8_t> &data) {
  if (!capture_enabled_ || capture_capacity_ == 0)
    return;

  CapturedFrame frame;
  frame.timestamp_ms = millis();
  frame.can_id = can_id;
  frame.dlc = static_cast<uint8_t>(std::min<size_t>(data.size(), 8));
  for (uint8_t i = 0; i < frame.dlc; i++)
    frame.data[i] = data[i];

  if (capture_frames_.size() < capture_capacity_) {
    capture_frames_.push_back(frame);
    if (capture_frames_.size() == capture_capacity_)
      capture_write_index_ = 0;
    return;
  }

  capture_frames_[capture_write_index_] = frame;
  capture_write_index_ = (capture_write_index_ + 1) % capture_capacity_;
  capture_overwrites_++;
}

void TraneBus::on_can_frame_(uint32_t can_id, bool extended_id, bool rtr, const std::vector<uint8_t> &data) {
  rx_frames_++;
  if (extended_id || rtr)
    return;

  capture_frame_(can_id, data);

  if (is_known_trane_id_(can_id)) {
    trane_frames_++;
    last_trane_frame_ms_ = millis();
  }

  if (can_id == 0x649 || can_id == 0x5C9 || can_id == 0x641) {
    seen_sc360_ = true;
    sc360_frames_++;
    last_sc360_frame_ms_ = millis();
  }

  if (can_id == 0x641 || can_id == 0x649) {
    std::string complete;
    SegmentedRxState &state = can_id == 0x641 ? rx_641_ : rx_649_;
    if (feed_segmented_json_(state, data, complete))
      handle_json_message_(can_id, complete);
  }
}

bool TraneBus::feed_segmented_json_(SegmentedRxState &state, const std::vector<uint8_t> &data,
                                    std::string &complete) {
  complete.clear();
  if (data.empty())
    return false;

  const uint8_t marker = data[0];
  if ((marker & 0xF0) == 0xC0) {
    state.reset();
    if (data.size() < 3) {
      rx_transport_errors_++;
      return false;
    }
    state.expected_len = static_cast<size_t>(data[1]) | (static_cast<size_t>(data[2]) << 8);
    if (state.expected_len == 0 || state.expected_len > MAX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    state.buffer.reserve(state.expected_len);
    for (size_t i = 5; i < data.size() && state.buffer.size() < state.expected_len; i++) {
      if (data[i] != 0)
        state.buffer.push_back(static_cast<char>(data[i]));
    }
    return false;
  }

  if (state.expected_len == 0)
    return false;

  if (marker & 0x80) {
    size_t used = marker & 0x7F;
    if (used == 0) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    used -= 1;
    if (used > 7) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    for (size_t i = 1; i < data.size() && i <= used && state.buffer.size() < state.expected_len; i++) {
      if (data[i] == 0)
        break;
      state.buffer.push_back(static_cast<char>(data[i]));
    }
    if (state.buffer.size() == state.expected_len) {
      complete = state.buffer;
      state.reset();
      return true;
    }
    rx_transport_errors_++;
    state.reset();
    return false;
  }

  if (marker != state.expected_seq) {
    rx_transport_errors_++;
    state.reset();
    return false;
  }
  state.expected_seq++;
  for (size_t i = 1; i < data.size() && state.buffer.size() < state.expected_len; i++) {
    if (data[i] == 0)
      break;
    state.buffer.push_back(static_cast<char>(data[i]));
  }
  return false;
}

void TraneBus::handle_json_message_(uint32_t can_id, const std::string &json) {
  if (!validate_payload_shape_(json)) {
    rx_transport_errors_++;
    ESP_LOGW(TAG, "Discarding non-JSON segmented payload on 0x%03" PRIX32, can_id);
    return;
  }
  rx_json_messages_++;
  json_trigger_.trigger(json, can_id);
  if (can_id == 0x641)
    handle_641_message_(json);
}

void TraneBus::handle_641_message_(const std::string &json) {
  const auto ack_pos = json.find("\"Ack\":");
  if (ack_pos == std::string::npos || !pending_ack_)
    return;
  size_t value = ack_pos + 6;
  while (value < json.size() && (json[value] == ' ' || json[value] == '\"'))
    value++;
  const bool ok = value + 3 <= json.size() && json.compare(value, 3, "200") == 0;
  if (ok) {
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
  if (!std::isfinite(heat_f) || !std::isfinite(cool_f) || heat_f < setpoint_min_f_ || heat_f > setpoint_max_f_ ||
      cool_f < setpoint_min_f_ || cool_f > setpoint_max_f_ || cool_f - heat_f < min_deadband_f_ || zone < 1 ||
      zone > 6 || hold_type < 0 || hold_type > 2 || source < 0 || source > 2) {
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
