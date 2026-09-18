#pragma once

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/components/canbus/canbus.h"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace esphome {
namespace trane_bus {

class TraneBus : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;

  void set_canbus(canbus::Canbus *canbus) { canbus_ = canbus; }
  void set_tx_enabled(bool enabled) { tx_enabled_ = enabled; }
  void set_raw_json_enabled(bool enabled) { raw_json_enabled_ = enabled; }
  void set_require_sc360_before_tx(bool enabled) { require_sc360_before_tx_ = enabled; }
  void set_bus_activity_timeout_ms(uint32_t timeout_ms) { bus_activity_timeout_ms_ = timeout_ms; }
  void set_ack_timeout_ms(uint32_t timeout_ms) { ack_timeout_ms_ = timeout_ms; }
  void set_command_can_id(uint32_t can_id) { command_can_id_ = can_id; }
  void set_setpoint_min_f(float value) { setpoint_min_f_ = value; }
  void set_setpoint_max_f(float value) { setpoint_max_f_ = value; }
  void set_min_deadband_f(float value) { min_deadband_f_ = value; }
  void set_capture_capacity(size_t capacity) { capture_capacity_ = capacity; }
  void set_capture_enabled(bool enabled) { capture_enabled_ = enabled; }

  bool is_tx_enabled() const { return tx_enabled_; }
  bool is_raw_json_enabled() const { return raw_json_enabled_; }
  bool has_seen_sc360() const { return seen_sc360_; }
  bool has_pending_ack() const { return pending_ack_; }
  bool has_recent_trane_activity() const;
  bool is_capture_enabled() const { return capture_enabled_; }

  // Public observation-only classifier used by the HA discovery surface.
  // Keep the target-observed CANopen management/configuration vocabulary out
  // of the "novel ID" counter even when an individual proprietary payload has
  // not yet been semantically decoded. Deliberately classify only IDs actually
  // observed on this target rather than broad CANopen ranges.
  bool is_known_trane_id(uint32_t can_id) const {
    if (can_id == 0x000 || can_id == 0x081 || can_id == 0x083 ||
        (can_id >= 0x200 && can_id <= 0x210) || can_id == 0x496 ||
        can_id == 0x540 || can_id == 0x560 || can_id == 0x5A1 ||
        can_id == 0x621 || can_id == 0x7E4 || can_id == 0x7E5)
      return true;
    return is_known_trane_id_(can_id);
  }

  Trigger<std::string, uint32_t> *get_json_trigger() { return &json_trigger_; }

  bool send_json(const std::string &payload);
  bool set_system_mode(const std::string &mode);
  bool set_setpoints(float heat_f, float cool_f, int zone = 1, int hold_type = 2, int source = 1);
  bool request_profile(const std::string &profile);

  void start_capture(bool clear_first = false);
  void stop_capture() { capture_enabled_ = false; }
  void clear_capture();
  void dump_capture() const;

  // Discovery/census helpers. These are observation-only and never transmit.
  // They keep the latest standard-frame payload for every 11-bit CAN ID so
  // candidate telemetry can be exposed in YAML without teaching the transport
  // layer unproven semantics.
  void clear_id_census();
  void dump_id_census() const;
  void dump_json_snapshots() const;
  uint16_t get_unique_standard_ids_seen() const { return unique_standard_ids_seen_; }
  uint32_t get_can_id_count(uint16_t can_id) const;
  uint8_t get_last_can_dlc(uint16_t can_id) const;
  float get_last_float_le_or_nan(uint16_t can_id, uint8_t offset) const;
  float get_last_u16_le_or_nan(uint16_t can_id, uint8_t offset) const;
  float get_last_byte_or_nan(uint16_t can_id, uint8_t offset) const;
  uint32_t get_last_u32_le_or_zero(uint16_t can_id, uint8_t offset) const;
  std::string get_last_frame_hex(uint16_t can_id) const;
  std::string get_last_json_value(const std::string &root, const std::string &scope, const std::string &key) const;
  uint8_t get_json_snapshot_count() const { return json_snapshot_count_; }

  const std::string &get_last_json_root() const { return last_json_root_; }
  const std::string &get_last_profile_request() const { return last_profile_request_; }
  const std::string &get_debug_idble() const { return debug_idble_; }
  const std::string &get_debug_odble() const { return debug_odble_; }
  uint32_t get_last_json_can_id() const { return last_json_can_id_; }

  uint32_t get_rx_frames() const { return rx_frames_; }
  uint32_t get_trane_frames() const {
    uint32_t total = 0;
    for (uint16_t can_id = 0; can_id < STANDARD_CAN_ID_COUNT; can_id++) {
      if (is_known_trane_id(can_id))
        total += id_counts_[can_id];
    }
    return total;
  }
  uint32_t get_sc360_frames() const { return sc360_frames_; }
  uint32_t get_rx_json_messages() const { return rx_json_messages_; }
  uint32_t get_tx_attempts() const { return tx_attempts_; }
  uint32_t get_tx_blocked() const { return tx_blocked_; }
  uint32_t get_tx_busy_blocked() const { return tx_busy_blocked_; }
  uint32_t get_tx_messages() const { return tx_messages_; }
  uint32_t get_tx_frames() const { return tx_frames_; }
  uint32_t get_tx_errors() const { return tx_errors_; }
  uint32_t get_ack_ok() const { return ack_ok_; }
  uint32_t get_ack_error() const { return ack_error_; }
  uint32_t get_ack_timeouts() const { return ack_timeouts_; }
  uint32_t get_rx_transport_errors() const { return rx_transport_errors_; }
  uint32_t get_last_trane_frame_ms() const { return last_trane_frame_ms_; }
  uint32_t get_last_sc360_frame_ms() const { return last_sc360_frame_ms_; }
  size_t get_capture_size() const { return capture_frames_.size(); }
  uint32_t get_capture_overwrites() const { return capture_overwrites_; }

 protected:
  static constexpr size_t STANDARD_CAN_ID_COUNT = 0x800;
  static constexpr size_t JSON_SNAPSHOT_SLOTS = 16;
  static constexpr size_t MAX_JSON_SNAPSHOT_BYTES = 2048;

  struct SegmentedRxState {
    enum class Mode : uint8_t { IDLE = 0, BLOCK_DOWNLOAD = 1, SEGMENTED_DOWNLOAD = 2 };

    std::string buffer{};
    size_t expected_len{0};
    Mode mode{Mode::IDLE};
    uint8_t expected_seq{1};
    uint8_t expected_toggle{0};
    uint8_t block_size{0};
    uint8_t block_last_seq{0};
    bool awaiting_block_ack{false};

    void reset() {
      buffer.clear();
      expected_len = 0;
      mode = Mode::IDLE;
      expected_seq = 1;
      expected_toggle = 0;
      block_size = 0;
      block_last_seq = 0;
      awaiting_block_ack = false;
    }
  };

  struct CapturedFrame {
    uint32_t timestamp_ms{0};
    uint32_t can_id{0};
    uint8_t dlc{0};
    uint8_t data[8]{0};
  };

  struct JsonSnapshot {
    std::string root{};
    std::string json{};
    uint32_t sequence{0};
  };

  bool send_frame_(const std::vector<uint8_t> &frame);
  bool send_json_internal_(const std::string &payload, bool expect_ack, const char *kind);
  bool validate_payload_shape_(const std::string &payload) const;
  bool validate_profile_name_(const std::string &profile) const;
  bool is_known_trane_id_(uint32_t can_id) const;
  void on_can_frame_(uint32_t can_id, bool extended_id, bool rtr, const std::vector<uint8_t> &data);
  void observe_standard_frame_(uint32_t can_id, const std::vector<uint8_t> &data);
  void capture_frame_(uint32_t can_id, const std::vector<uint8_t> &data);
  bool feed_segmented_json_(SegmentedRxState &state, const std::vector<uint8_t> &data, std::string &complete);
  void feed_sdo_json_response_(SegmentedRxState &state, const std::vector<uint8_t> &data);
  void handle_json_message_(uint32_t can_id, const std::string &json);
  void remember_json_snapshot_(const std::string &root, const std::string &json);
  void handle_641_message_(const std::string &json);
  void clear_pending_ack_();

  canbus::Canbus *canbus_{nullptr};
  bool tx_enabled_{false};
  bool raw_json_enabled_{false};
  bool require_sc360_before_tx_{true};
  bool seen_sc360_{false};
  bool pending_ack_{false};
  bool capture_enabled_{false};

  uint32_t command_can_id_{0x641};
  uint32_t bus_activity_timeout_ms_{300000};
  uint32_t ack_timeout_ms_{3000};
  uint32_t pending_ack_since_ms_{0};
  uint32_t last_trane_frame_ms_{0};
  uint32_t last_sc360_frame_ms_{0};

  float setpoint_min_f_{50.0f};
  float setpoint_max_f_{90.0f};
  float min_deadband_f_{2.0f};

  std::string pending_kind_{};
  std::string last_json_root_{};
  std::string last_profile_request_{};
  std::string debug_idble_{};
  std::string debug_odble_{};
  uint32_t last_json_can_id_{0};
  SegmentedRxState rx_601_{};
  SegmentedRxState rx_621_{};
  SegmentedRxState rx_641_{};
  SegmentedRxState rx_649_{};
  Trigger<std::string, uint32_t> json_trigger_;

  size_t capture_capacity_{0};
  size_t capture_write_index_{0};
  std::vector<CapturedFrame> capture_frames_{};
  uint32_t capture_overwrites_{0};

  // Compact 11-bit CAN census: ~27 KiB total for counts, DLCs and last data.
  // This is intentionally fixed-size so observation cannot fragment heap or
  // grow without bound during long commissioning runs.
  std::array<uint32_t, STANDARD_CAN_ID_COUNT> id_counts_{};
  std::array<uint8_t, STANDARD_CAN_ID_COUNT> id_last_dlc_{};
  std::array<std::array<uint8_t, 8>, STANDARD_CAN_ID_COUNT> id_last_data_{};
  uint16_t unique_standard_ids_seen_{0};

  std::array<JsonSnapshot, JSON_SNAPSHOT_SLOTS> json_snapshots_{};
  uint32_t json_snapshot_sequence_{0};
  uint8_t json_snapshot_count_{0};

  // Retained for low-cost runtime/diagnostic compatibility. Public reporting
  // uses the census-derived get_trane_frames() so it cannot drift from the
  // authoritative target classifier above.
  uint32_t rx_frames_{0};
  uint32_t trane_frames_{0};
  uint32_t sc360_frames_{0};
  uint32_t rx_json_messages_{0};
  uint32_t tx_attempts_{0};
  uint32_t tx_blocked_{0};
  uint32_t tx_busy_blocked_{0};
  uint32_t tx_messages_{0};
  uint32_t tx_frames_{0};
  uint32_t tx_errors_{0};
  uint32_t ack_ok_{0};
  uint32_t ack_error_{0};
  uint32_t ack_timeouts_{0};
  uint32_t rx_transport_errors_{0};
};

template<typename... Ts> class TraneBusSendJsonAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(std::string, payload)
  void play(Ts... x) override { this->parent_->send_json(this->payload_.value(x...)); }
};

template<typename... Ts> class TraneBusSetTxEnabledAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(bool, enabled)
  void play(Ts... x) override { this->parent_->set_tx_enabled(this->enabled_.value(x...)); }
};

template<typename... Ts> class TraneBusSetModeAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(std::string, mode)
  void play(Ts... x) override { this->parent_->set_system_mode(this->mode_.value(x...)); }
};

template<typename... Ts> class TraneBusSetSetpointsAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(float, heat_f)
  TEMPLATABLE_VALUE(float, cool_f)
  TEMPLATABLE_VALUE(int, zone)
  TEMPLATABLE_VALUE(int, hold_type)
  TEMPLATABLE_VALUE(int, source)
  void play(Ts... x) override {
    this->parent_->set_setpoints(this->heat_f_.value(x...), this->cool_f_.value(x...), this->zone_.value(x...),
                                 this->hold_type_.value(x...), this->source_.value(x...));
  }
};

template<typename... Ts> class TraneBusGetProfileAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(std::string, profile)
  void play(Ts... x) override { this->parent_->request_profile(this->profile_.value(x...)); }
};

}  // namespace trane_bus
}  // namespace esphome
