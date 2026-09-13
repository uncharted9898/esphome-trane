# Trane HVAC CAN bus ESPHome external component

# The climate component has an optional guarded trane_bus control path. Auto-load
# the sibling component so legacy configurations that name only trane_hvac still
# compile/link without having to instantiate trane_bus.
AUTO_LOAD = ["trane_bus"]
