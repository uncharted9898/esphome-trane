#pragma once

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/components/canbus/canbus.h"

#include <cstdint>
#include <string>

namespace esphome {
namespace trane_bus {

class TraneBus : public Component {
 public:
  void set_canbus(canbus::Canbus *canbus) { canbus_ = canbus; }
  void set_tx_enabled(bool enabled) { tx_enabled_ = enabled; }
  void set_command_can_id(uint32_t can_id) { command_can_id_ = can_id; }

  bool is_tx_enabled() const { return tx_enabled_; }
  bool send_json(const std::string &payload);

  uint32_t get_tx_attempts() const { return tx_attempts_; }
  uint32_t get_tx_blocked() const { return tx_blocked_; }
  uint32_t get_tx_messages() const { return tx_messages_; }
  uint32_t get_tx_frames() const { return tx_frames_; }
  uint32_t get_tx_errors() const { return tx_errors_; }

  void dump_config() override;

 protected:
  bool send_frame_(const std::vector<uint8_t> &frame);

  canbus::Canbus *canbus_{nullptr};
  bool tx_enabled_{false};
  uint32_t command_can_id_{0x641};

  uint32_t tx_attempts_{0};
  uint32_t tx_blocked_{0};
  uint32_t tx_messages_{0};
  uint32_t tx_frames_{0};
  uint32_t tx_errors_{0};
};

template<typename... Ts> class TraneBusSendJsonAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(std::string, payload)

  void play(Ts... x) override {
    this->parent_->send_json(this->payload_.value(x...));
  }
};

template<typename... Ts> class TraneBusSetTxEnabledAction : public Action<Ts...>, public Parented<TraneBus> {
 public:
  TEMPLATABLE_VALUE(bool, enabled)

  void play(Ts... x) override {
    this->parent_->set_tx_enabled(this->enabled_.value(x...));
  }
};

}  // namespace trane_bus
}  // namespace esphome
