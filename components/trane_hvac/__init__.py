# Trane HVAC CAN bus ESPHome external component

# Keep trane_bus optional. The legacy monolithic decoder uses the climate
# platform without a trane_bus instance, while the maintained guarded profiles
# explicitly configure trane_bus_id and materialize that sibling component.
