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
  // Eight bytes rendered as "AA BB CC DD EE FF 00 11" require 23
  // characters plus the terminating NUL. Keep one extra byte of slack so the
  // conservative pos + 3 < sizeof(bytes) guard does not reject byte eight.
  char bytes[3 * 8 + 1] = {0};
  size_t pos = 0;
  for (uint8_t i = 0; i < id_last_dlc_[can_id] && i < 8 && pos + 3 < sizeof(bytes); i++)
    pos += snprintf(bytes + pos, sizeof(bytes) - pos, "%02X%s", id_last_data_[can_id][i],
                    i + 1 < id_last_dlc_[can_id] ? " " : "");
  return bytes;
}

float TraneBus::get_last_json_age_seconds() const {
  if (last_json_ms_ == 0)
    return NAN;
  return static_cast<float>(millis() - last_json_ms_) / 1000.0f;
}

float TraneBus::get_json_snapshot_age_seconds(const std::string &root) const {
  for (const auto &snapshot : json_snapshots_) {
    if (snapshot.root == root && snapshot.updated_ms != 0)
      return static_cast<float>(millis() - snapshot.updated_ms) / 1000.0f;
  }
  return NAN;
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
  // Target-observed 11-bit Trane Link families. "Known" here means observed
  // and classified as belonging to this HVAC bus, not that every byte has a
  // promoted semantic name. Keeping this list in the transport component gives
  // the HA discovery surface one authoritative novel-ID boundary.
  if ((can_id >= 0x250 && can_id <= 0x252) || (can_id >= 0x260 && can_id <= 0x262) ||
      (can_id >= 0x280 && can_id <= 0x285) || (can_id >= 0x2D0 && can_id <= 0x2D2) ||
      (can_id >= 0x380 && can_id <= 0x38F) || (can_id >= 0x490 && can_id <= 0x495) ||
      (can_id >= 0x4B0 && can_id <= 0x4B4) || (can_id >= 0x4C0 && can_id <= 0x4C5) ||
      (can_id >= 0x701 && can_id <= 0x705))
    return true;

  switch (can_id) {
    case 0x200:
    case 0x201:
    case 0x203:
    case 0x208:
    case 0x20D:
    case 0x240:
    case 0x300:
    case 0x308:
    case 0x310:
    case 0x318:
    case 0x320:
    case 0x328:
    case 0x330:
    case 0x3D0:
    case 0x3E0:
    case 0x410:
    case 0x420:
    case 0x430:
    case 0x450:
    case 0x460:
    case 0x53D:
    case 0x53E:
    case 0x581:
    case 0x5A1:
    case 0x5C1:
    case 0x5C9:
    case 0x601:
    case 0x621:
    case 0x641:
    case 0x649:
    case 0x7E5:
      return true;
    default:
      return false;
  }
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

  SegmentedRxState *sdo_state = nullptr;
  uint32_t sdo_request_id = 0;
  bool sdo_response = false;
  switch (can_id) {
    case 0x601:
    case 0x581:
      sdo_state = &rx_601_;
      sdo_request_id = 0x601;
      sdo_response = can_id == 0x581;
      break;
    case 0x621:
    case 0x5A1:
      sdo_state = &rx_621_;
      sdo_request_id = 0x621;
      sdo_response = can_id == 0x5A1;
      break;
    case 0x641:
    case 0x5C1:
      sdo_state = &rx_641_;
      sdo_request_id = 0x641;
      sdo_response = can_id == 0x5C1;
      break;
    case 0x649:
    case 0x5C9:
      sdo_state = &rx_649_;
      sdo_request_id = 0x649;
      sdo_response = can_id == 0x5C9;
      break;
    default:
      break;
  }

  if (sdo_state != nullptr) {
    if (sdo_response) {
      feed_sdo_json_response_(*sdo_state, data);
    } else {
      std::string complete;
      if (feed_segmented_json_(*sdo_state, data, complete))
        handle_json_message_(sdo_request_id, complete);
    }
  }
}

bool TraneBus::feed_segmented_json_(SegmentedRxState &state, const std::vector<uint8_t> &data,
                                    std::string &complete) {
  complete.clear();
  if (data.empty())
    return false;

  const uint8_t marker = data[0];

  auto is_trane_json_object = [&]() -> bool {
    return data.size() >= 4 && data[1] == 0x0A && data[2] == 0x30 && data[3] == 0x00;
  };

  auto indicated_json_length = [&]() -> size_t {
    if (data.size() < 8)
      return 0;
    const uint32_t wire_len = static_cast<uint32_t>(data[4]) |
                              (static_cast<uint32_t>(data[5]) << 8) |
                              (static_cast<uint32_t>(data[6]) << 16) |
                              (static_cast<uint32_t>(data[7]) << 24);
    // Object 0x300A:00 carries a NUL-terminated JSON string. CANopen's
    // indicated size includes that NUL; the application string does not.
    return wire_len > 0 ? static_cast<size_t>(wire_len - 1U) : 0;
  };

  if (state.expected_len != 0) {
    if (state.mode == SegmentedRxState::Mode::SEGMENTED_DOWNLOAD) {
      // CANopen segmented SDO download request: 000tnnnc.
      if ((marker & 0xE0) != 0x00) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      const uint8_t toggle = (marker >> 4) & 0x01;
      const uint8_t unused = (marker >> 1) & 0x07;
      const bool last = (marker & 0x01) != 0;
      if (toggle != state.expected_toggle || (!last && unused != 0)) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      size_t data_bytes = data.size() > 1 ? data.size() - 1 : 0;
      if (last) {
        if (unused > data_bytes) {
          rx_transport_errors_++;
          state.reset();
          return false;
        }
        data_bytes -= unused;
      }

      for (size_t i = 0; i < data_bytes && state.buffer.size() < state.expected_len; i++) {
        const uint8_t byte = data[i + 1];
        if (byte == 0)
          break;
        state.buffer.push_back(static_cast<char>(byte));
      }

      if (last) {
        if (state.buffer.size() == state.expected_len) {
          complete = state.buffer;
          state.reset();
          return true;
        }
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      state.expected_toggle ^= 0x01;
      return false;
    }

    if (state.mode == SegmentedRxState::Mode::BLOCK_DOWNLOAD) {
      // Block payload segments use cnnnnnnn. Sequence numbers restart at 1
      // after each server A2 sub-block acknowledgement.
      if (state.awaiting_block_ack) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      const uint8_t sequence = marker & 0x7F;
      const bool last = (marker & 0x80) != 0;
      if (sequence == 0 || sequence != state.expected_seq) {
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      for (size_t i = 1; i < data.size() && state.buffer.size() < state.expected_len; i++) {
        if (data[i] == 0)
          break;
        state.buffer.push_back(static_cast<char>(data[i]));
      }

      state.block_last_seq = sequence;
      if (last) {
        if (state.buffer.size() == state.expected_len) {
          complete = state.buffer;
          state.reset();
          return true;
        }
        rx_transport_errors_++;
        state.reset();
        return false;
      }

      if (state.block_size != 0 && sequence == state.block_size) {
        state.awaiting_block_ack = true;
      } else {
        state.expected_seq = sequence == 0x7F ? 1 : static_cast<uint8_t>(sequence + 1U);
      }
      return false;
    }

    rx_transport_errors_++;
    state.reset();
    return false;
  }

  // Only SDO downloads to the target-observed Trane JSON mailbox are parsed as
  // JSON. Other SDO objects on the same COB-ID remain visible in raw capture
  // diagnostics but cannot poison the structured JSON state.
  if ((marker == 0xC2 || marker == 0x21) && !is_trane_json_object())
    return false;

  if (marker == 0xC2) {
    const size_t payload_len = indicated_json_length();
    if (payload_len == 0 || payload_len > MAX_RX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    state.reset();
    state.expected_len = payload_len;
    state.mode = SegmentedRxState::Mode::BLOCK_DOWNLOAD;
    state.expected_seq = 1;
    state.buffer.reserve(state.expected_len);
    return false;
  }

  if (marker == 0x21) {
    const size_t payload_len = indicated_json_length();
    if (payload_len == 0 || payload_len > MAX_RX_JSON_PAYLOAD) {
      rx_transport_errors_++;
      state.reset();
      return false;
    }
    state.reset();
    state.expected_len = payload_len;
    state.mode = SegmentedRxState::Mode::SEGMENTED_DOWNLOAD;
    state.expected_toggle = 0;
    state.buffer.reserve(state.expected_len);
    return false;
  }

  // Standard SDO end/ack/control frames are handled on the paired response
  // COB-ID or ignored while idle. They are not JSON payload starts.
  return false;
}

void TraneBus::feed_sdo_json_response_(SegmentedRxState &state, const std::vector<uint8_t> &data) {
  if (data.empty() || state.expected_len == 0)
    return;

  const uint8_t marker = data[0];

  if (marker == 0x80) {
    // Standard SDO abort terminates the current transfer.
    rx_transport_errors_++;
    state.reset();
    return;
  }

  if (state.mode == SegmentedRxState::Mode::BLOCK_DOWNLOAD) {
    if (marker == 0xA0) {
      if (data.size() < 5 || data[1] != 0x0A || data[2] != 0x30 || data[3] != 0x00 ||
          data[4] == 0 || data[4] > 0x7F) {
        rx_transport_errors_++;
        state.reset();
        return;
      }
      state.block_size = data[4];
      return;
    }

    if (marker == 0xA2) {
      if (data.size() < 3 || !state.awaiting_block_ack ||
          data[1] != state.block_last_seq || data[2] == 0 || data[2] > 0x7F) {
        rx_transport_errors_++;
        state.reset();
        return;
      }
      state.block_size = data[2];
      state.expected_seq = 1;
      state.awaiting_block_ack = false;
      return;
    }

    // A1 is the end response. The JSON extractor normally completed on the
    // final request segment, so seeing A1 while state is still active means the
    // indicated payload length did not match the received data.
    if (marker == 0xA1) {
      rx_transport_errors_++;
      state.reset();
    }
    return;
  }

  if (state.mode == SegmentedRxState::Mode::SEGMENTED_DOWNLOAD) {
    // 0x60 is initiate response; 0x20/0x30 acknowledge toggle 0/1 segments.
    // The request-side parser owns payload assembly, so only aborts need to
    // mutate state here.
    return;
  }
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
  slot->updated_ms = millis();
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
  last_json_ms_ = millis();
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

  if (last_json_root_ == "Debug") {
    auto remember_debug_value = [&](const char *key, std::string &target) {
      const std::string needle = std::string("\"") + key + "\":\"";
      const size_t key_pos = json.find(needle);
      if (key_pos == std::string::npos)
        return;
      const size_t value_start = key_pos + needle.size();
      const size_t value_end = json.find('"', value_start);
      if (value_end != std::string::npos)
        target = json.substr(value_start, value_end - value_start);
    };
    remember_debug_value("IDBLE", debug_idble_);
    remember_debug_value("ODBLE", debug_odble_);
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
  // Names observed verbatim in the target SC360's stock 0x641
  // GetProfile sweep are listed explicitly. Retain earlier upstream names as
  // historical vocabulary, but do not invent aliases for captured names.
  static const char *const ALLOWED[] = {
      "SYSOP", "INDOOR", "ZONE", "ALARMS", "SPOVERRIDE", "PRESET", "SYSTEM",
      "SCHEDULE", "VERSION", "ZONECARD", "ZONING", "WEATHERDATA", "UNITID",
      "THERMOSETTINGS", "TECHAPPSETTINGS", "NOTIFICATIONDATA", "INDOORSTATE",
      "ZONESTATE", "ODSTATE", "ODSETTINGS"};
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

  // Passive target captures now prove that Trane JSON is transported as a
  // CANopen SDO download to object 0x300A:00. The legacy writer previously
  // emitted guessed C2/sequence frames without an object index and without
  // waiting for the mandatory SDO server responses (A0/A2/A1 or 60/20/30).
  // Sending that sequence would be an invalid SDO transaction. Fail closed
  // until a non-blocking SDO client state machine is implemented and command
  // direction is qualified against a captured UX360 command transaction.
  (void) expect_ack;
  tx_blocked_++;
  ESP_LOGE(TAG, "TX blocked: CANopen SDO writer for Trane object 0x300A:00 is not yet qualified (%s)", kind);
  return false;
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
