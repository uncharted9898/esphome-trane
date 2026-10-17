# Trane Link firmware observations

This file records firmware versions observed on real equipment in the target Trane Link installation. Keep **download availability**, **installed version**, and **version-string interpretation** separate so field evidence is not accidentally promoted into a broader vendor-wide claim.

## SC360

### 2026-09-15 field observation

- Device: SC360 system controller in the target communicating Trane Link system.
- Source: Trane Technician app during an actual field update check.
- Latest firmware offered by the Technician app for this SC360: `9.4.0.20260518`.
- The Technician app downloaded that package.
- This observation establishes `9.4.0.20260518` as the latest version **offered to this SC360 by the Technician app at that time**. It should not be generalized to every SC360 hardware revision, region, account, or staged rollout without additional evidence.
- Downloaded does not by itself prove installation completed. Confirm the post-update running build from the UX360 equipment summary, Technician app device details, or a captured Link `UnitID` / build/version object before marking it installed.

### Version-string notes

`9.4.0.20260518` appears to contain:

- product/software version: `9.4.0`;
- suffix: `20260518`.

The suffix strongly resembles a `YYYYMMDD` build date (`2026-05-18`), but keep that interpretation as a working hypothesis unless Trane documentation or package metadata explicitly confirms the field format.

### Relationship to older observations

The upstream/older field capture `09.01.01.250508` remains useful historical protocol evidence, but it is no longer a reasonable candidate for "latest SC360 firmware" on the target installation. For this system, the Technician app directly offered `9.4.0.20260518` on 2026-09-15.

Do not silently rewrite historical CAN captures to the newer number; retain the version actually observed in each capture.

## OTA capture checklist

When updating communicating equipment, keep the Waveshare bridge online and record the complete session. Prefer the normal-CAN observer profile with application command TX disabled.

Before update:

- record SC360 running build;
- record UX360 build;
- record 5TAMX build;
- record 5TWV0X build;
- record mitigation/A2L controller and sensor versions if exposed;
- capture model and serial for each communicating node;
- start the host-side `TRANE_CAN_LIVE` logger before initiating the update.

During update:

- preserve `0x641` / `0x649` traffic;
- preserve `0x5C1` / `0x5C9` private transport;
- preserve all currently unknown standard CAN IDs;
- note which physical unit reboots and in what order;
- note any temporary communication-loss or mitigation-related events without inducing additional faults.

After update:

- capture the first complete cold/recovery boot through stable idle;
- record the running version of every communicating device again;
- compare node census and CAN-ID census before/after;
- compare full-profile objects and configuration revisions before/after;
- keep the original downloaded firmware package and its hash if available through the legitimate Technician-app workflow.

## Evidence levels

Use these labels in future notes:

- **Offered** — Technician app/server says the version is available for the specific device.
- **Downloaded** — package transfer/download completed to the Technician-app workflow.
- **Installed** — update process reports completion on the device.
- **Running-confirmed** — device itself reports the version after reboot via UI, Technician diagnostics, or Link telemetry.

For `9.4.0.20260518` on 2026-09-15, current evidence is **Offered + Downloaded**. Promote it to **Installed** / **Running-confirmed** only after the post-update device state confirms it.
