#include "components/trane_bus/wifi_list_fragment_assembler.h"
#include <cassert>
#include <string>

int main() {
  using esphome::trane_bus::WifiListFragmentAssembler;
  using esphome::trane_bus::TraneProfileFragmentAssembler;
  TraneProfileFragmentAssembler x;
  std::string result;
  const std::string root = "{\"WifiList\":{\"Update\":{\"network\":{\"Ssid\":\"";
  const std::string msg = root + std::string(2353 - root.size() - 5, 'A') + "\"}}}}";
  assert(msg.size() == 2353);
  assert(!x.consume(0x649, msg.substr(0, 2048), 100, result));
  assert(x.pending() && result.empty());
  assert(x.consume(0x649, msg.substr(2048), 125, result));
  assert(result == msg && !x.pending());
  assert(x.consume(0x641, "{\"Ack\":\"200\"}", 130, result));
  assert(result == "{\"Ack\":\"200\"}");
  assert(!x.consume(0x649, msg.substr(0, 2048), 200, result));
  assert(x.expire(5201) && !x.pending());
  assert(x.consume(0x649, "normal", 5202, result) && result == "normal");
  assert(!x.consume(0x649, msg.substr(0, 2048), 5400, result));
  assert(x.consume(0x649, "{\"OdStatus\":{\"Update\":{}}}", 5401, result));
  assert(result == "{\"OdStatus\":{\"Update\":{}}}");
  assert(!x.pending());

  // Captured October 22 shape: Schedule 2048+1625 JSON bytes. The second
  // SDO download advertises 1626 including its terminating NUL.
  const std::string schedule_root = "{\"Schedule\":{\"Update\":{\"1\":{\"Period\":\"";
  const std::string schedule = schedule_root +
      std::string(3673 - schedule_root.size() - 5, 'S') + "\"}}}}";
  assert(schedule.size() == 3673);
  assert(!x.consume(0x649, schedule.substr(0, 2048), 1000, result));
  assert(result.empty() && x.pending());
  assert(x.consume(0x649, schedule.substr(2048), 2250, result));
  assert(result == schedule && !x.pending());

  assert(!x.consume(0x649, schedule.substr(0, 2048), 3000, result));
  assert(x.consume(0x641, "{\"Ack\":\"200\"}", 3001, result));
  assert(x.pending());
  assert(x.consume(0x649, "{\"ZoneStatus\":{\"Update\":{}}}", 3002, result));
  assert(!x.pending() && result == "{\"ZoneStatus\":{\"Update\":{}}}");

  assert(!x.consume(0x649, schedule.substr(0, 2048), 4000, result));
  assert(!x.consume(0x649, std::string(2049, 'B'), 4001, result));
  assert(!x.pending());
  assert(!x.consume(0x649, schedule.substr(0, 2048), 5000, result));
  assert(x.expire(10001) && !x.pending());
  WifiListFragmentAssembler legacy;
  assert(!legacy.pending());
  return 0;
}
