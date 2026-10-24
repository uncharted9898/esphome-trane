#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace esphome {
namespace trane_bus {

// Bounded, receive-only application JSON assembly across independent
// CANopen 0x300A:00 block downloads. Capture-qualified roots only:
//   2026-10-15 WifiList: 2048 + 305 JSON bytes (+ final NUL)
//   2026-10-22 Schedule: 2048 + 1625 JSON bytes (+ final NUL)
// Neither SDO transport nor any transmit capability is changed.
class TraneProfileFragmentAssembler {
 public:
  static constexpr size_t MAX_DOCUMENT_BYTES = 4096;
  static constexpr size_t FIRST_FRAGMENT_BYTES = 2048;
  static constexpr uint32_t MAX_FRAGMENT_AGE_MS = 5000;

  // Returns true only when a complete message should enter normal JSON
  // handling. Unrelated 0x641 commands/ACKs are passed through unchanged.
  bool consume(uint32_t source_id, const std::string &payload, uint32_t now_ms,
               std::string &complete) {
    complete.clear();
    if (source_id != 0x649) {
      complete = payload;
      return true;
    }

    expire(now_ms);
    if (!fragment_.empty()) {
      // A new JSON root cannot be the continuation of a quoted string in the
      // captured split transfer; do not mix unrelated profile updates.
      if (!payload.empty() && payload.front() == '{') {
        reset();
      } else {
        if (payload.empty() || payload.size() > MAX_DOCUMENT_BYTES - fragment_.size()) {
          reset();
          return false;
        }
        fragment_ += payload;
        if (complete_object_(fragment_)) {
          complete.swap(fragment_);
          reset();
          return true;
        }
        return false;
      }
    }

    // Do not infer generic fragmentation from arbitrary malformed JSON.
    // Only captured, exact-size first chunks from the two known profile roots.
    static constexpr char WIFI_PREFIX[] = "{\"WifiList\":";
    static constexpr char SCHEDULE_PREFIX[] = "{\"Schedule\":";
    const bool qualified_root =
        payload.compare(0, sizeof(WIFI_PREFIX) - 1, WIFI_PREFIX) == 0 ||
        payload.compare(0, sizeof(SCHEDULE_PREFIX) - 1, SCHEDULE_PREFIX) == 0;
    if (payload.size() == FIRST_FRAGMENT_BYTES && qualified_root &&
        !complete_object_(payload)) {
      fragment_ = payload;
      started_ms_ = now_ms;
      return false;
    }

    complete = payload;
    return true;
  }

  bool expire(uint32_t now_ms) {
    if (fragment_.empty() ||
        static_cast<uint32_t>(now_ms - started_ms_) <= MAX_FRAGMENT_AGE_MS)
      return false;
    reset();
    return true;
  }

  bool pending() const { return !fragment_.empty(); }

  void reset() {
    fragment_.clear();
    started_ms_ = 0;
  }

 private:
  // Small quote/escape-aware structural guard: never forward an unterminated
  // or bracket-mismatched concatenation. Normal JSON handling remains
  // authoritative for downstream field interpretation.
  static bool complete_object_(const std::string &value) {
    if (value.size() < 2 || value.front() != '{' || value.back() != '}')
      return false;
    std::vector<char> nesting;
    nesting.reserve(16);
    bool quoted = false;
    bool escaped = false;
    for (size_t i = 0; i < value.size(); i++) {
      const char ch = value[i];
      if (quoted) {
        if (escaped) {
          escaped = false;
        } else if (ch == '\\') {
          escaped = true;
        } else if (ch == '"') {
          quoted = false;
        }
        continue;
      }
      if (ch == '"') {
        quoted = true;
      } else if (ch == '{' || ch == '[') {
        nesting.push_back(ch);
      } else if (ch == '}' || ch == ']') {
        if (nesting.empty())
          return false;
        const char opener = nesting.back();
        if ((ch == '}' && opener != '{') || (ch == ']' && opener != '['))
          return false;
        nesting.pop_back();
        if (nesting.empty() && i + 1 < value.size())
          return false;
      }
    }
    return !quoted && !escaped && nesting.empty();
  }

  std::string fragment_{};
  uint32_t started_ms_{0};
};

// Compatibility for the October 15 helper; callers can migrate without
// breaking any existing test or integration referencing the historical name.
using WifiListFragmentAssembler = TraneProfileFragmentAssembler;

}  // namespace trane_bus
}  // namespace esphome
