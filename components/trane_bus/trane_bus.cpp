#include "trane_bus.h"

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <vector>

namespace esphome {
namespace trane_bus {

static const char *const TAG = "trane_bus";
static constexpr size_t MAX_JSON_PAYLOAD = 512;
static constexpr uint32_t INTER_FRAME_DELAY_MS = 2;

void TraneBus::dump_config() {
  ESP_LOGCONFIG(TAG, "Trane Link transport:");
  ESP_LOGCONFIG(TAG, "  Command CAN ID: 0x%03" PRIX32, command_can_id_);
  ESP_LOGCONFIG(TAG, "  TX enabled: %s", YESNO(tx_enabled_));
  ESP_LOGCONFIG(TAG, "  Max JSON payload: %u bytes", static_cast<unsigned>(MAX_JSON_PAYLOAD));
}

bool TraneBus::send_frame_(const std::vector<uint8_t> &frame) {
  if (canbus_ == nullptr) {
    ESP_LOGE(TAG, "Cannot transmit: CAN bus is not configured");
    tx_errors_++;
    return false;
  }

  const canbus::Error result = canbus_->send_data(command_can_id_, false, frame);
  if (result != canbus::ERROR_OK) {
    ESP_LOGE(TAG, "CAN transmit failed on 0x%03" PRIX32 " with error %u",
             command_can_id_, static_cast<unsigned>(result));
    tx_errors_++;
    return false;
  }

  tx_frames_++;
  return true;
}

bool TraneBus::send_json(const std::string &payload) {
  tx_attempts_++;

  if (!tx_enabled_) {
    tx_blocked_++;
    ESP_LOGW(TAG, "TX blocked (monitor-only mode): %s", payload.c_str());
    return false;
  }

  if (payload.empty()) {
    ESP_LOGW(TAG, "Refusing to transmit an empty JSON payload");
    tx_errors_++;
    return false;
  }

  if (payload.size() > MAX_JSON_PAYLOAD) {
    ESP_LOGE(TAG, "Refusing %u-byte JSON payload; maximum is %u bytes",
             static_cast<unsigned>(payload.size()), static_cast<unsigned>(MAX_JSON_PAYLOAD));
    tx_errors_++;
    return false;
  }

  const uint32_t total = static_cast<uint32_t>(payload.size());
  std::vector<uint8_t> header = {
      0xC2,
      static_cast<uint8_t>(total & 0xFF),
      static_cast<uint8_t>((total >> 8) & 0xFF),
      0x00, 0x00, 0x00, 0x00, 0x00,
  };

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
  ESP_LOGI(TAG, "Transmitted JSON on 0x%03" PRIX32 ": %s", command_can_id_, payload.c_str());
  return true;
}

}  // namespace trane_bus
}  // namespace esphome
