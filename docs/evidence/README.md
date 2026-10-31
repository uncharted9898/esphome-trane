# Target evidence archive

These files are **chronological reverse-engineering evidence**, not the current semantic source of truth.

Current mappings live in [../TELEMETRY.md](../TELEMETRY.md). CANopen transport behavior lives in [../CANOPEN-LINK-TRANSPORT.md](../CANOPEN-LINK-TRANSPORT.md).

## 2026-09-17

| File | What it captured |
|---|---|
| [can-census-initial.md](2026-09-17/can-census-initial.md) | Initial target CAN census and first 5TAMX/5TWV0X correlations |
| [can-census-followup.md](2026-09-17/can-census-followup.md) | Follow-up census, additional IDs, airflow/min-speed/transport observations |
| [technician-correlation.md](2026-09-17/technician-correlation.md) | Correlation against Technician monitor values |
| [blower-electrical.md](2026-09-17/blower-electrical.md) | Blower electrical/airflow correlations and later superseded assumptions |
| [high-load-requalification.md](2026-09-17/high-load-requalification.md) | High-load capture that disproved several old outdoor labels |
| [cool-ambient-requalification.md](2026-09-17/cool-ambient-requalification.md) | Cooler-ambient cross-check and CANopen SDO identification |
| [satisfied-profile-sweep.md](2026-09-17/satisfied-profile-sweep.md) | Satisfied/idle baseline, profile sweep, freshness findings |
| [canopen-lss-fastscan.md](2026-09-17/canopen-lss-fastscan.md) | Initial LSS Fastscan decode and analyzer support |

## 2026-09-18

| File | What it captured |
|---|---|
| [active-cooling.md](2026-09-18/active-cooling.md) | Active cooling, modulation, shutdown, LSS identity, environmental source corrections, logs 9-14 |

## How to use these notes

A useful pattern is:

1. Read the current mapping in [../TELEMETRY.md](../TELEMETRY.md).
2. Follow the evidence links/dated notes when you need to understand *why* a field has its current confidence level.
3. When new captures disprove a mapping, update the maintained map and append a new evidence note rather than rewriting old observations.


## 2026-09-20

| File | What it captured |
|---|---|
| [active-cooling-ha-validation.md](2026-09-20/active-cooling-ha-validation.md) | Curated HA validation, 0x281 compressor-demand proof, compressor speed request/ceiling requalification, and 0x2D0/0x430 follow-up |

## 2026-09-22

| File | What it captured |
|---|---|
| [outdoor-sensor-chain-long-pass.md](2026-09-22/outdoor-sensor-chain-long-pass.md) | Logs 16-21 outdoor sensor-chain decode, suction-pressure scaling boundary, drive/fan thermal candidates, 0x450 stale-value fix, and 0x2D0 airflow-limit clue |


## 2026-09-23

| File | What it captured |
|---|---|
| [full-day-idle-stator-heat.md](2026-09-23/full-day-idle-stator-heat.md) | Long idle/equalization baseline, 0x383 pressure-pair requalification, repeatable stator-heat cycles, 0x282 flag, and compressor phase-current family |


## 2026-09-24

| File | What it captured |
|---|---|
| [full-day-stator-heat-cadence.md](2026-09-24/full-day-stator-heat-cadence.md) | Complete 24-hour idle archive, 19 stator-heat cycles, cadence/timing, 0x390 power-level requalification, and strengthened phase-current evidence |


## 2026-09-25

| File | What it captured |
|---|---|
| [full-day-idle-stator-room-mirror.md](2026-09-25/full-day-idle-stator-room-mirror.md) | Complete 24-hour idle capture, 16 more stator-heat cycles, stator-enable promotion, 0x390 timing, direct ZoneStatus.H/0x490 room-temperature mirror, and quantitative pressure equalization |


## 2026-09-26

| File | What it captured |
|---|---|
| [full-day-cooling-cycle-qualification.md](2026-09-26/full-day-cooling-cycle-qualification.md) | Five real AC Stage 1 cycles, startup/modulation/shutdown state codes, pressure split/re-equalization, TA_INV_HI false-fault correction, and 13 additional stator-heat cycles |


## 2026-09-27

| File | What it captured |
|---|---|
| [full-day-long-run-blower-requalification.md](2026-09-27/full-day-long-run-blower-requalification.md) | Nine cooling intervals including an ~83-minute run, one AC Stage 2 transition, blower command/feedback requalification, long-run pressure confirmation, and eight more stator-heat cycles |


## 2026-09-28

| File | What it captured |
|---|---|
| [full-day-stage2-low-suction-protection.md](2026-09-28/full-day-stage2-low-suction-protection.md) | Twelve cooling intervals, a ~93-minute run with ~66 minutes of AC Stage 2, blower-percent confirmation, OEM 185.10/185.11 low-suction protection correlation, six more stator-heat cycles, and 0x460 thermal-family correlation |


## 2026-09-29

| File | What it captured |
|---|---|
| [full-day-control-request-path.md](2026-09-29/full-day-control-request-path.md) | Sixteen cooling runs, clean control day after 185.10/185.11, blower request-percent confirmation, 0x385 startup-sentinel filtering, structured setpoint override path, and two more stator-heat cycles |


## 2026-09-30

| File | What it captured |
|---|---|
| [full-day-stage2-exact-length-json.md](2026-09-30/full-day-stage2-exact-length-json.md) | Fourteen cooling intervals, two long Stage-2-heavy runs, blower-request confirmation, four more 0x385 sentinels, three stator-heat cycles, and the exact-length/no-NUL 0x300A JSON transport bug/fix |


## 2026-10-01

| File | What it captured |
|---|---|
| [full-day-repeated-exact-length-json.md](2026-10-01/full-day-repeated-exact-length-json.md) | Six cooling intervals including two ~167-minute runs, sustained Stage 2, blower-request confirmation, two more 0x385 sentinels, four stator-heat cycles, and a second independent exact-length/no-NUL 0x300A JSON transfer |


## 2026-10-02

| File | What it captured |
|---|---|
| [full-day-sustained-stage2.md](2026-10-02/full-day-sustained-stage2.md) | Nine cooling intervals including a ~5.75-hour run with ~5.3 hours of Stage 2, blower-request confirmation, six more 0x385 sentinels, two stator-heat cycles, pressure/thermal long-run confirmation, and clean structured JSON transport |


## 2026-10-03

| File | What it captured |
|---|---|
| [full-day-stock-setpoint-transport.md](2026-10-03/full-day-stock-setpoint-transport.md) | Full-day archive, exact stock SpOverride.Put CANopen block-SDO handshake, application Ack path, SystemOpStatus.E humidity requalification, and third exact-length/no-NUL JSON observation |


## 2026-10-04

| File | What it captured |
|---|---|
| [full-day-idle-stator-cadence.md](2026-10-04/full-day-idle-stator-cadence.md) | Complete 24-hour mechanical-idle capture, 18 isolated stator-heat cycles, strongest full-day pressure-equalization baseline, direct humidity/room mirrors, and a fourth exact-length/no-NUL 0x300A JSON transfer |


## 2026-10-05

| File | What it captured |
|---|---|
| [full-day-idle-setpoint-stator.md](2026-10-05/full-day-idle-setpoint-stator.md) | Complete 24-hour mechanical-idle capture, three additional stock SpOverride.Put writes (77/79/78 F), five-write qualified setpoint evidence total, 15 stator-heat cycles taking the total to 109, pressure equalization, structured humidity/room mirrors, and clean NUL-sized JSON transport |


## 2026-10-06

| File | What it captured |
|---|---|
| [technician-profile-fan-long-json.md](2026-10-06/technician-profile-fan-long-json.md) | Full-day compressor-idle archive, Technician-qualified fan enable/50/100% control sequence, 0x281.byte7 blower-active disproof, HcStatus=4 fan/coast evidence, full EquipSummary inventory including CNT09525 and 10 kW 2-stage heater accessory, long-JSON logger truncation/fix, fifth exact-length/no-NUL transfer, and 14 complete + one carry-out stator-heat cycles |


## 2026-10-07

| File | What it captured |
|---|---|
| [full-day-idle-bridge-reboot-stator.md](2026-10-07/full-day-idle-bridge-reboot-stator.md) | Complete mechanical-idle day, closure of the 10/06 stator carry-out plus 15 new complete cycles taking the corpus to 139, wide-ambient pressure equalization, a bridge-only reboot/reconnect without OEM heartbeat reset, 0x2D0 non-airflow disproof, and 0x53D/0x53E network-status refinement |


## 2026-10-08

| File | What it captured |
|---|---|
| [full-day-cooling-stator-sixth-nonul.md](2026-10-08/full-day-cooling-stator-sixth-nonul.md) | Full day with eight cooling runs, ~73.5 minutes Stage 2, 13 new stator cycles (152 cumulative), pressure/room/humidity validation, compressor-request-adjacent 0x281.byte7 behavior, and sixth exact-length/no-NUL JSON transfer verified on-device |


## 2026-10-09

| File | What it captured |
|---|---|
| [full-day-stage1-stator-thermal-correlations.md](2026-10-09/full-day-stage1-stator-thermal-correlations.md) | Complete full-day Stage 1 capture with 12 compressor runs (~104 min), 4 isolated stator cycles (156 cumulative), all 1,304 structured JSON messages reassembled from CAN without mismatch, compressor-request/0x281.byte7 correlation, pressure equalization, indoor mirrors and stronger 0x460 electronics thermal-family evidence |


## 2026-10-10

| File | What it captured |
|---|---|
| [full-day-stator-cooling-setpoint-seventh-nonul.md](2026-10-10/full-day-stator-cooling-setpoint-seventh-nonul.md) | Complete 24-hour CAN capture with three cooling runs, brief Stage 2 transitions, ten complete stator cycles (166 cumulative), sixth stock setpoint Put, seventh exact-length/no-NUL DebugUI transaction, direct room/humidity mirrors and unchanged guardrails |


## 2026-10-11

| File | What it captured |
|---|---|
| [full-day-stage2-stator-setpoint-eighth-nonul.md](2026-10-11/full-day-stage2-stator-setpoint-eighth-nonul.md) | Full-day CAN capture with four cooling runs and 118.29 minutes uninterrupted Stage 2, 13 complete stator cycles (179 cumulative), 75 F inhibit disproof, exact match of all 976 structured JSON bodies, seventh stock setpoint write, and eighth exact-length/no-NUL DebugUI transfer |


## 2026-10-12

| File | What it captured |
|---|---|
| [full-day-stage2-stator-transport.md](2026-10-12/full-day-stage2-stator-transport.md) | 24-hour CAN capture with nine compressor runs, 176.26 minutes uninterrupted Stage 2, eight complete stator cycles (187 cumulative), full 1,582/1,582 structured JSON replay, pressure/room/humidity correlation and unchanged write-safety policy |


## 2026-10-13

| File | What it captured |
|---|---|
| [full-day-stage2-stator-ninth-nonul.md](2026-10-13/full-day-stage2-stator-ninth-nonul.md) | Full-day 2,637,881-frame CAN replay with 1,605/1,605 structured JSON matches, twelve compressor starts (one carry-out), 124.61 minutes sustained Stage 2, seven stator cycles (194 cumulative), ninth exact-length/no-NUL DebugUI transfer, and preserved write safety |


## 2026-10-14

| File | What it captured |
|---|---|
| [full-day-stage2-stator-power-sentinel.md](2026-10-14/full-day-stage2-stator-power-sentinel.md) | Full 24-hour CAN replay (1,480/1,480 JSON messages), compressor carry-in/out, 247.2 minutes sustained Stage 2, six stator cycles (200 cumulative), and first confirmed 65535 W compressor-power startup sentinel requiring filtered HA telemetry |


## 2026-10-15 through 2026-10-16

| File | What it captured |
|---|---|
| [two-day-technician-restart-split-wifi.md](2026-10-16/two-day-technician-restart-split-wifi.md) | 48 hours / 5.34 million raw CAN frames; full raw-vs-collector JSON agreement; long-logger verification; new split WifiList SDO shape; node-3 NMT restart; 5 additional stator cycles (205 cumulative); new power sentinels and two exact-length/no-NUL DebugUI samples |


## 2026-10-17

| File | What it captured |
|---|---|
| [full-day-cooling-setpoints-stator.md](2026-10-17/full-day-cooling-setpoints-stator.md) | 24-hour 2,631,192 CAN frames, 2,010/2,010 CANopen JSON replay, eight cooling runs, nine stator cycles (214 cumulative), six additional stock setpoint writes (13 cumulative), and stable five-node network |


## 2026-10-18

| File | What it captured |
|---|---|
| [full-day-cold-idle-stator-bridge-reset.md](2026-10-18/full-day-cold-idle-stator-bridge-reset.md) | Complete 24-hour mechanical idle: 2,594,593 raw CAN frames, 98/98 clean CANopen JSON messages, 23 complete isolated stator cycles (237 cumulative), cold-ambient pressure equalization, and a bridge-only reset with five Link nodes remaining operational |


## 2026-10-19

| File | What it captured |
|---|---|
| [first-heat-pump-stage1-profile-stator.md](2026-10-19/first-heat-pump-stage1-profile-stator.md) | First explicit HP Stage 1 operation (three compressor runs), diagnostic 0x281.byte7 heating/cooling request-mode discrimination, one new stock 68°F heat setpoint write, 18 new stator cycles (255 cumulative), 362/362 reconstructed JSON messages, runtime-history profile sweep and twelfth no-NUL DebugUI sample |


## 2026-10-20 through 2026-10-23

| File | What it captured |
|---|---|
| [four-day-heating-stator-split-schedule.md](2026-10-23/four-day-heating-stator-split-schedule.md) | 73 new completed stator cycles (328 cumulative), four stock setpoint writes (18 cumulative), two no-NUL samples (14 cumulative), Oct 20 HP Stage 1 runs, two mechanically idle days, and a new 3673-byte Schedule split across two valid block SDOs |


## 2026-10-24

| File | What it captured |
|---|---|
| [full-day-idle-stator-transport.md](2026-10-24/full-day-idle-stator-transport.md) | Complete mechanical-idle day with 2,591,720 raw CAN frames, exact 88/88 JSON reconstruction, 20 new stator cycles (348 cumulative), cold idle-pressure equalization and stable five-node CANopen network; also validates the captured October 22 Schedule split seam |


## 2026-10-25

| File | What it captured |
|---|---|
| [full-day-idle-stator-no-nul.md](2026-10-25/full-day-idle-stator-no-nul.md) | Complete mechanical-idle day with 2,592,765 CAN frames, 139/139 validated CANopen JSON messages, 19 isolated stator cycles (367 cumulative), stable five-node network and fifteenth exact-length/no-NUL DebugUI sample |


## 2026-10-26

| File | What it captured |
|---|---|
| [full-day-cold-idle-stator-collector-restart.md](2026-10-26/full-day-cold-idle-stator-collector-restart.md) | Full-day cold idle with 2,590,463 CAN frames, exact 60/60 JSON replay, 19 isolated stator cycles (386 cumulative), 11.19-minute longest cycle, tight pressure equalization and a collector-only restart without ESP/OEM NMT reset |


## 2026-10-27 through 2026-10-28

| File | What it captured |
|---|---|
| [two-day-cold-idle-stator-no-nul.md](2026-10-28/two-day-cold-idle-stator-no-nul.md) | Two full mechanically idle days with 5,186,202 raw CAN frames, 133/133 exact JSON replay, 39 completed isolated stator cycles (425 cumulative), sixteenth no-NUL DebugUI and October 28 collector-only reconnect |


## 2026-10-29

| File | What it captured |
|---|---|
| [full-day-idle-stator-carryout-seventeenth-nonul.md](2026-10-29/full-day-idle-stator-carryout-seventeenth-nonul.md) | Complete idle day, 2,593,335 raw CAN frames, exact 107/107 JSON replay, 17 completed isolated stator cycles (442 cumulative) plus one 23:59 carry-out, seventeenth exact-length/no-NUL DebugUI, stable five-node CANopen network |


## 2026-10-30

| File | What it captured |
|---|---|
| [full-day-idle-stator-carryin-closure.md](2026-10-30/full-day-idle-stator-carryin-closure.md) | Full-day mechanical idle with 2,593,248 raw CAN frames and 24/24 complete JSON messages; closure of October 29 stator carry-out plus 16 new complete cycles (459 cumulative); stable five-node network and no new TX family |
