# Trane Link bridge commissioning

Reference board: Waveshare ESP32-S3-RS485-CAN

Target architecture: parallel CAN tap. UX360 remains installed and usable. SC360 remains authoritative. The bridge must be removable without changing normal HVAC operation.

## 0. Before connecting anything

1. Confirm the Waveshare CAN 120 ohm jumper is open/disabled.
2. With the bridge disconnected and HVAC power off, measure DH to DL at the system. Record the resistance; do not add another termination resistor.
3. Power the Waveshare from USB-C for first commissioning.
4. Connect only CAN H -> DH and CAN L -> DL.
5. Do not connect Trane R/B to the Waveshare CAN terminal side.

## 1. Passive capture firmware

Flash `waveshare-trane-listenonly.yaml`.

Expected behavior:

- GPIO15 = CAN TX into the Waveshare onboard CAN interface.
- GPIO16 = CAN RX from the onboard CAN interface.
- 50 kbit/s.
- ESP32 TWAI mode = LISTENONLY.
- TX queue length = 0.
- `trane_bus.tx_enabled = false`.
- raw JSON TX disabled.

Acceptance checks:

- UX360 continues to operate normally.
- No new HVAC fault appears after attaching CAN H/L.
- SC360 traffic is detected.
- 0x649 traffic is visible.
- 0x5C1/0x5C9 activity appears during UX360 interactions/reboot.
- outdoor 0x380-0x38F family appears.
- indoor/air-handler traffic appears.

Remain in passive capture until this stage is clean.

## 2. Capture matrix for the all-electric target system

Record raw CAN while changing only one operating condition at a time.

1. idle/standby;
2. cooling startup;
3. cooling modulation;
4. cooling shutdown/coastdown;
5. heat-pump heating startup;
6. heating modulation;
7. heating shutdown;
8. auxiliary electric heat stage 1;
9. auxiliary electric heat stage 2, if configured;
10. emergency heat;
11. fan-only, if UX360 exposes it;
12. dehumidification;
13. schedule transition;
14. manual/timed hold;
15. UX360 reboot;
16. SC360 reboot;
17. full system power restoration;
18. defrost;
19. defrost plus supplemental electric heat;
20. safe service/fault conditions where appropriate.

For every capture note:

- UTC/local timestamp;
- HVAC mode;
- room temperature;
- heat/cool setpoints;
- outdoor temperature;
- UX360 screen state;
- observed compressor %;
- blower %;
- aux/emergency heat indication;
- any active alarms.

## 3. Active-monitor firmware

Flash `waveshare-trane-full.yaml` or `waveshare-trane-control.yaml` with repository defaults unchanged.

At this stage:

- TWAI is NORMAL so the bridge participates as a CAN node/ACK peer;
- Trane application TX remains disabled;
- raw JSON remains disabled;
- decoded telemetry should continue working.

Verify for an extended run before enabling commands.

## 4. Local-control arming

On `waveshare-trane-full.yaml`, the `Local Trane Control` switch restores OFF after every reboot.

It may only enable if recent SC360 traffic has been observed. Even after enabled, command transport:

- validates supported modes;
- validates setpoint ranges/deadband;
- blocks a second write while waiting for ACK;
- times out a missing ACK;
- keeps SC360-reported state authoritative;
- does not continuously reassert Home Assistant state.

## 5. First command sequence

Use a low-risk sequence while physically present at the equipment.

1. Request `SYSOP` profile.
2. Confirm SC360 traffic is fresh.
3. Enable `Local Trane Control`.
4. Change one setpoint by 1 F.
5. Confirm CAN ACK 200.
6. Confirm the UX360 updates to the same setpoint.
7. Confirm the SC360 broadcast updates and Home Assistant reflects it.
8. Change the value back from the UX360 and confirm Home Assistant follows without the bridge fighting the thermostat.
9. Test heat/cool/off commands one at a time only after setpoint coexistence is proven.

## 6. Failure tests

All must pass before treating the bridge as production-ready.

- unplug bridge USB power while HVAC is running;
- reboot bridge;
- disable Wi-Fi;
- disable Home Assistant;
- reboot Home Assistant;
- disconnect LAN;
- use UX360 while bridge is online;
- issue a command then immediately change it at UX360;
- simulate an ACK timeout without repeated writes;
- leave bridge powered with local control switch OFF.

Expected result: HVAC and UX360/SC360 continue normally in every case.

## 7. Permanent power

Do not apply Trane 24 VAC directly to the Waveshare DC input.

Use an appropriately rated 24 VAC -> DC converter and feed the board within its documented DC input range. Keep the bridge electrically parallel to, never inline with, the Trane Link bus.
