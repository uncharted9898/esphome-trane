#include "trane_bus.h"

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <vector>

namespace esphome {
namespace trane_bus {

static const char *const TAG = "trane_bus";
static constexpr size_t MAX_RX_JSON_PAYLOAD = 4096;
static constexpr size_t MAX_TX_JSON_PAYLOAD = 512;
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
  ESP_LOGCONFIG(TAG, "  Max RX JSON payload: %u bytes", static_cast<unsigned>(MAX_RX_JSON_PAYLOAD));
  ESP_LOGCONFIG(TAG, "  Max TX JSON payload: %u bytes", static_cast<unsigned>(MAX_TX_JSON_PAYLOAD));
  ESP_LOGCONFIG(TAG, "  Capture: %s, capacity %u frames", YESNO(capture_enabled_),
                static_cast<unsigned>(capture_capacity_));
  ESP_LOGCONFIG(TAG, "  CAN census: fixed 11-bit table, %u IDs currently seen",
                static_cast<unsigned>(unique_standard_ids_seen_));
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

void TraneBus::clear_id_census() {
  id_counts_.fill(0);
  id_last_dlc_.fill(0);
  for (auto &payload : id_last_data_)
    payload.fill(0);
  unique_standard_ids_seen_ = 0;
  ESP_LOGI(TAG, "CAN ID census cleared");
}

void TraneBus::dump_id_census() const {
  ESP_LOGI(TAG, "TRANE_ID_CENSUS_BEGIN unique=%u", static_cast<unsigned>(unique_standard_ids_seen_));
  for (uint16_t can_id = 0; can_id < STANDARD_CAN_ID_COUNT; can_id++) {
    if (id_counts_[can_id] == 0)
      continue;
    char bytes[17] = {0};
    for (uint8_t i = 0; i < id_last_dlc_[can_id] && i < 8; i++)
      snprintf(bytes + i * 2, sizeof(bytes) - i * 2, "%02X", id_last_data_[can_id][i]);
    ESP_LOGI(TAG, "TRANE_ID,%03X,%lu,%u,%s", static_cast<unsigned>(can_id),
             static_cast<unsigned long>(id_counts_[can_id]), static_cast<unsigned>(id_last_dlc_[can_id]), bytes);
  }
  ESP_LOGI(TAG, "TRANE_ID_CENSUS_END");
}

uint32_t TraneBus::get_can_id_count(uint16_t can_id) const {
  return can_id < STANDARD_CAN_ID_COUNT ? id_counts_[can_id] : 0;
}

uint8_t TraneBus::get_last_can_dlc(uint16_t can_id) const {
  return can_id < STANDARD_CAN_ID_COUNT ? id_last_dlc_[can_id] : 0;
}

float TraneBus::get_last_float_le_or_nan(uint16_t can_id, uint8_t offset) const {
  if (can_id >= STANDARD_CAN_ID_COUNT || offset > 4 || id_last_dlc_[can_id] < static_cast<uint8_t>(offset + 4))
    return std::numeric_limits<float>::quiet_NaN();
  float value;
  std::memcpy(&value, &id_last_data_[can_id][offset], sizeof(value));
  return std::isfinite(value) ? value : std::numeric_limits<float>::quiet_NaN();
}

float TraneBus::get_last_u16_le_or_nan(uint16_t can_id, uint8_t offset) const {
  if (can_id >= STANDARD_CAN_ID_COUNT || offset > 6 || id_last_dlc_[can_id] < static_cast<uint8_t>(offset + 2))
    return std::numeric_limits<float>::quiet_NaN();
  const uint16_t value = static_cast<uint16_t>(id_last_data_[can_id][offset]) |
                         (static_cast<uint16_t>(id_last_data_[can_id][offset + 1]) << 8);
  return static_cast<float>(value);
}

float TraneBus::get_last_byte_or_nan(uint16_t can_id, uint8_t offset) const {
  if (can_id >= STANDARD_CAN_ID_COUNT || offset >= 8 || id_last_dlc_[can_id] <= offset)
    return std::numeric_limits<float>::quiet_NaN();
  return static_cast<float>(id_last_data_[can_id][offset]);
}

uint32_t TraneBus::get_last_u32_le_or_zero(uint16_t can_id, uint8_t offset) const {
  if (can_id >= STANDARD_CAN_ID_COUNT || offset > 4 || id_last_dlc_[can_id] < static_cast<uint8_t>(offset + 4))
    return 0;
  return static_cast<uint32_t>(id_last_data_[can_id][offset]) |
         (static_cast<uint32_t>(id_last_data_[can_id][offset + 1]) << 8) |
         (static_cast<uint32_t>(id_last_data_[can_id][offset + 2]) << 16) |
         (static_cast<uint32_t>(id_last_data_[can_id][offset + 3]) << 24);
}

std::string TraneBus::get_last_frame_hex(uint16_t can_id) const {
  if (can_id >= STANDARD_CAN_ID_COUNT || id_counts_[can_id] == 0)
    return {};
  char bytes[24] = {0};
  size_t pos = 0;
  for (uint8_t i = 0; i < id_last_dlc_[can_id] && i < 8 && pos + 3 < sizeof(bytes); i++)
    pos += snprintf(bytes + pos, sizeof(bytes) - pos, "%02X%s", id_last_data_[can_id][i],
                    i + 1 < id_last_dlc_[can_id] ? " " : "");
  return bytes;
}

std::string TraneBus::get_last_json_value(const std::string &root, const std::string &scope,
                                          const std::string &key) const {
  const JsonSnapshot *snapshot = nullptr;
  for (const auto &candidate : json_snapshots_) {
    if (candidate.root == root) {
      snapshot = &candidate;
      break;
    }
  }
  if (snapshot == nullptr || snapshot->json.empty())
    return {};

  const std::string &json = snapshot->json;
  size_t start = 0;
  size_t end = json.size();

  auto find_object_range = [&](const std::string &object_key, size_t from, size_t limit, size_t &out_start,
                               size_t &out_end) -> bool {
    const std::string needle = "\"" + object_key + "\"";
    const size_t key_pos = json.find(needle, from);
    if (key_pos == std::string::npos || key_pos >= limit)
      return false;
    const size_t brace = json.find('{', key_pos + needle.size());
    if (brace == std::string::npos || brace >= limit)
      return false;
    int depth = 0;
    bool quoted = false;
    bool escaped = false;
    for (size_t pos = brace; pos < limit; pos++) {
      const char c = json[pos];
      if (quoted) {
        if (escaped) { escaped = false; continue; }
        if (c == '\\') { escaped = true; continue; }
        if (c == '"') quoted = false;
        continue;
      }
      if (c == '"') { quoted = true; continue; }
      if (c == '{') depth++;
      else if (c == '}' && --depth == 0) {
        out_start = brace + 1;
        out_end = pos;
        return true;
      }
    }
    return false;
  };

  size_t root_start = 0, root_end = json.size();
  if (!find_object_range(root, 0, json.size(), root_start, root_end))
    return {};
  start = root_start;
  end = root_end;

  if (!scope.empty()) {
    size_t scope_start = 0, scope_end = 0;
    if (!find_object_range(scope, start, end, scope_start, scope_end))
      return {};
    start = scope_start;
    end = scope_end;
  }

  const std::string field = "\"" + key + "\":\"";
  size_t pos = json.find(field, start);
  if (pos == std::string::npos || pos >= end)
    return {};
  pos += field.size();
  const size_t value_end = json.find('"', pos);
  if (value_end == std::string::npos || value_end > end)
    return {};
  return json.substr(pos, value_end - pos);
}

void TraneBus::dump_json_snapshots() const {
  ESP_LOGI(TAG, "TRANE_JSON_SNAPSHOTS_BEGIN count=%u", static_cast<unsigned>(json_snapshot_count_));
  for (const auto &snapshot : json_snapshots_) {
    if (!snapshot.root.empty())
      ESP_LOGI(TAG, "TRANE_JSON_SNAPSHOT,%s,%s", snapshot.root.c_str(), snapshot.json.c_str());
  }
  ESP_LOGI(TAG, "TRANE_JSON_SNAPSHOTS_END");
}

bool TraneBus::is_known_trane_id_(uint32_t can_id) const {
  if (can_id == 0x641 || can_id == 0x649 || can_id == 0x5C1 || can_id == 0x5C9 || can_id == 0x283 ||
      can_id == 0x308 || can_id == 0x490 || can_id == 0x410 || can_id == 0x430 || can_id == 0x450)
    return true;
  return can_id >= 0x380 && can_id <= 0x38F;
}

void TraneBus::observe_standard_frame_(uint32_t can_id, const std::vector<uint8_t> &data) {
  if (can_id >= STANDARD_CAN_ID_COUNT)
    return;
  if (id_counts_[can_id] == 0)
    unique_standard_ids_seen_++;
  id_counts_[can_id]++;
  const uint8_t dlc = static_cast<uint8_t>(std::min<size_t>(data.size(), 8));
  id_last_dlc_[can_id] = dlc;
  id_last_data_[can_id].fill(0);
  for (uint8_t i = 0; i < dlc; i++)
    id_last_data_[can_id][i] = data[i];
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

  observe_standard_frame_(can_id, data);
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

  // Target-system SC360 headers carry a uint32 little-endian wire length in
  // bytes 4..7. The wire length includes the trailing NUL, while expected_len
  // tracks JSON bytes only. Example captures:
  //   0x649: C2 0A 30 00 2D 00 00 00  -> 45 wire bytes / 44 JSON bytes
  //   0x641: 21 0A 30 00 0E 00 00 00  -> 14 wire bytes / 13 JSON bytes
  auto target_payload_length = [&]() -> size_t {
    if (data.size() < 8)
      return 0;
    const uint32_t wire_len = static_cast<uint32_t>(data[4]) |
                              (static_cast<uint32_t>(data[5]) << 8) |
                              (static_cast<uint32_t>(data[6]) << 16) |
                              (static_cast<uint32_t>(data[7]) << 24);
    if (wire_len == 0)
      return 0;
    return static_cast<size_t>(wire_len - 1U);
  };

  // Process an in-flight payload before interpreting an otherwise ambiguous
  // marker as a new header. Long transfers legitimately use sequence 0x21,
  // for example, which is also the short-response header when the receiver is
  // idle. The long sequence is seven-bit 1..0x7F and wraps 0x7F -> 0x01.
  if (state.expected_len != 0) {
    if (state.expected_seq & 0x80) {
      // Short 0x641 response framing: 0x0n continuation, 0x1n final.
      const uint8_t expected = state.expected_seq & 0x0F;
      const uint8_t frame_type = marker & 0xF0;
      const uint8_t sequence = marker & 0x0F;
      if ((frame_type != 0x00 && frame_type != 0x10) || sequence != expected) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      bool saw_nul = false;
      for (size_t i = 1; i < data.size() && state.buffer.size() < state.expected_len; i++) {
        if (data[i] == 0) {
          saw_nul = true;
          break;
        }
        state.buffer.push_back(static_cast<char>(data[i]));
      }

      const bool final_frame = frame_type == 0x10 || saw_nul || state.buffer.size() == state.expected_len;
      if (final_frame) {
        if (state.buffer.size() == state.expected_len) {
          complete = state.buffer;
          state.reset();
          return true;
        }
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      state.expected_seq = static_cast<uint8_t>(0x80 | ((expected + 1U) & 0x0F));
      return false;
    }

    // Long 0x641/0x649 framing. Bit 7 marks the final frame; the lower seven
    // bits are the sequence number, not a byte-count. This is why final marker
    // 0xAD means sequence 45 rather than "44 payload bytes in this frame".
    if (marker & 0x80) {
      const uint8_t sequence = marker & 0x7F;
      if (sequence != state.expected_seq) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }
      for (size_t i = 1; i < data.size() && state.buffer.size() < state.expected_len; i++) {
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
    for (size_t i = 1; i < data.size() && state.buffer.size() < state.expected_len; i++) {
      if (data[i] == 0)
        break;
      state.buffer.push_back(static_cast<char>(data[i]));
    }
    state.expected_seq = state.expected_seq == 0x7F ? 1 : static_cast<uint8_t>(state.expected_seq + 1U);
    return false;
  }

  // Idle-state header recognition is deliberately exact. C1/CD/D1/D5/D9 and
  // similar markers observed on the target are transport control/status frames,
  // not payload starts, and should not inflate RX transport errors.
  if (marker == 0xC2) {
    size_t payload_len = target_payload_length();
    if (payload_len == 0 || payload_len > MAX_RX_JSON_PAYLOAD) {
      // Backward-compatible receive fallback for earlier experimental captures
      // that encoded JSON length in bytes 1..2.
      if (data.size() >= 3)
        payload_len = static_cast<size_t>(data[1]) | (static_cast<size_t>(data[2]) << 8);
    }
    if (payload_len == 0 || payload_len > MAX_RX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    state.expected_len = payload_len;
    state.expected_seq = 1;
    state.buffer.reserve(state.expected_len);
    return false;
  }

  if (marker == 0x21) {
    const size_t payload_len = target_payload_length();
    if (payload_len == 0 || payload_len > MAX_RX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    state.expected_len = payload_len;
    state.expected_seq = 0x80;  // short framing flag + expected sequence 0
    state.buffer.reserve(state.expected_len);
    return false;
  }

  return false;
}

void TraneBus::remember_json_snapshot_(const std::string &root, const std::string &json) {
  if (root.empty() || json.empty() || json.size() > MAX_JSON_SNAPSHOT_BYTES ||
      !std::isalpha(static_cast<unsigned char>(root[0])))
    return;

  JsonSnapshot *slot = nullptr;
  for (auto &candidate : json_snapshots_) {
    if (candidate.root == root) {
      slot = &candidate;
      break;
    }
    if (slot == nullptr && candidate.root.empty())
      slot = &candidate;
  }
  if (slot == nullptr) {
    slot = &json_snapshots_[0];
    for (auto &candidate : json_snapshots_) {
      if (candidate.sequence < slot->sequence)
        slot = &candidate;
    }
  }
  const bool was_empty = slot->root.empty();
  slot->root = root;
  slot->json = json;
  slot->sequence = ++json_snapshot_sequence_;
  if (was_empty && json_snapshot_count_ < JSON_SNAPSHOT_SLOTS)
    json_snapshot_count_++;
}

void TraneBus::handle_json_message_(uint32_t can_id, const std::string &json) {
  if (!validate_payload_shape_(json)) {
    rx_transport_errors_++;
    ESP_LOGW(TAG, "Discarding non-JSON segmented payload on 0x%03" PRIX32, can_id);
    return;
  }

  last_json_can_id_ = can_id;
  const size_t root_start = json.find('"');
  if (root_start != std::string::npos) {
    const size_t root_end = json.find('"', root_start + 1);
    if (root_end != std::string::npos) {
      last_json_root_ = json.substr(root_start + 1, root_end - root_start - 1);
      if (can_id == 0x641 && last_json_root_ == "GetProfile") {
        const size_t colon = json.find(':', root_end + 1);
        const size_t value_start = colon == std::string::npos ? std::string::npos : json.find('"', colon + 1);
        const size_t value_end = value_start == std::string::npos ? std::string::npos : json.find('"', value_start + 1);
        if (value_start != std::string::npos && value_end != std::string::npos)
          last_profile_request_ = json.substr(value_start + 1, value_end - value_start - 1);
      }
    }
  }

  remember_json_snapshot_(last_json_root_, json);
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
                                         "SCHEDULE", "VERSION", "ZONECARD", "ZONING", "WEATHERDATA", "UNITID",
                                         "THERMOSETTINGS"};
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
  if (!validate_payload_shape_(payload) || payload.size() > MAX_TX_JSON_PAYLOAD) {
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
