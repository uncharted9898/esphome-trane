#pragma once

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/components/canbus/canbus.h"

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

  bool is_tx_enabled() const { return tx_enabled_; }
  bool is_raw_json_enabled() const { return raw_json_enabled_; }
  bool has_seen_sc360() const { return seen_sc360_; }
  bool has_pending_ack() const { return pending_ack_; }
  bool has_recent_trane_activity() const;

  Trigger<std::string, uint32_t> *get_json_trigger() { return &json_trigger_; }

  // Raw JSON is intentionally disabled by default. Normal callers should use
  // the typed methods below so the component can validate command semantics.
  bool send_json(const std::string &payload);
  bool set_system_mode(const std::string &mode);
  bool set_setpoints(float heat_f, float cool_f, int zone = 1, int hold_type = 2, int source = 1);
  bool request_profile(const std::string &profile);

  uint32_t get_rx_frames() const { return rx_frames_; }
  uint32_t get_trane_frames() const { return trane_frames_; }
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

 protected:
  struct SegmentedRxState {
    std::string buffer{};
    size_t expected_len{0};
    uint8_t expected_seq{1};

    void reset() {
      buffer.clear();
      expected_len = 0;
      expected_seq = 1;
    }
  };

  bool send_frame_(const std::vector<uint8_t> &frame);
  bool send_json_internal_(const std::string &payload, bool expect_ack, const char *kind);
  bool validate_payload_shape_(const std::string &payload) const;
  bool validate_profile_name_(const std::string &profile) const;
  bool is_known_trane_id_(uint32_t can_id) const;
  void on_can_frame_(uint32_t can_id, bool extended_id, bool rtr, const std::vector<uint8_t> &data);
  bool feed_segmented_json_(SegmentedRxState &state, const std::vector<uint8_t> &data, std::string &complete);
  void handle_json_message_(uint32_t can_id, const std::string &json);
  void handle_641_message_(const std::string &json);
  void clear_pending_ack_();

  canbus::Canbus *canbus_{nullptr};
  bool tx_enabled_{false};
  bool raw_json_enabled_{false};
  bool require_sc360_before_tx_{true};
  bool seen_sc360_{false};
  bool pending_ack_{false};

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
  SegmentedRxState rx_641_{};
  SegmentedRxState rx_649_{};

  Trigger<std::string, uint32_t> json_trigger_;

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
