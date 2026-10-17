#include "components/trane_bus/wifi_list_fragment_assembler.h"
#include <cassert>
#include <string>

int main() {
  using esphome::trane_bus::WifiListFragmentAssembler;
  WifiListFragmentAssembler x;
  std::string result;
  const std::string root = "{\"WifiList\":{\"Update\":{\"network\":{\"Ssid\":\"";
  const std::string msg = root + std::string(2010, 'A') + "\"}}}";
  assert(msg.size() > 2048);
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
  return 0;
}
