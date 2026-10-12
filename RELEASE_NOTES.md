# v0.1.0-beta.4

12 October 2026: adds matched 737-800WSFP2 landing VREF15/30/40 for 40–85t
to the existing bounded passenger -800 profile. Both FMCs display and select
the landing references; Calc publishes matching F30/F40 and the original
F40-based maneuver aliases/bugs. The plugin-facing F15 maneuver reference
stays F40+20. The optional VREF module's standard -800 values do not take
precedence while this profile is active. Previously selected/manual approach
speeds retain their original ownership and require deliberate reselection.

At 62.6t the profile uses landing F15/F30/F40 149/138/135kt with bounded
linear interpolation and the original nearest-integer landing convention.
Exact Boeing/FMC interpolation/rounding remains unverified. Out-of-domain or
unavailable approach weight supplies no substituted landing candidates.
Other models/SFP off, takeoff tables, N1 and the beta.3 pneumatic fix are retained.
Native -800 stall/minimum-speed modeling, aerodynamics and tailskid geometry
are unchanged; certified landing/dispatch distances and braking are not added.

The same standalone/MTK package supports exact beta.1/.2/.3 hook migrations.
Published MTK catalog 1.20.0 registers the three new landing marker pairs and
preserves the complete ownership policy. Use MTK 0.28.2 or newer, refresh its
online catalog, update through MTK and keep other installed patches selected.
No new MTK application release is required. A standalone update requires
uninstall with the retained matching old installer first, then installation
from the beta.4 ZIP. Follow the README when switching installation owners.

Independent beta.4 source review is GO. Current dry tests passed 104 Python
methods (21 Lua/landing, 62 installer, 6 earlier-beta handovers, 15 export) and
54 released-Core MTK cases, including VREF/Tablet/required LevelUp W&B,
beta.1/.2/.3 upgrades and restore. The review found and closed an approach-mass
provenance defect: a unit-only change retains the originating weight and
cannot invalidate 85.0t kg input or admit an out-of-domain 187.4klb input via
its rounded alternate-unit value.
MTK tests used a disposable expanded-policy catalog; the published 1.20.0
catalog was verified to contain the same complete policy. Earlier catalogs
without the new markers reject beta.4 and roll the aircraft back exactly.
Simulator validation remains open. The public package contains only patch
material/runtime tables; no original/modified complete aircraft scripts,
plugin, ACF, manual or private C++ source.

# v0.1.0-beta.3

10 October 2026: packs, engine bleed switches and isolation-valve changes no
longer retire confirmed automatic takeoff speeds merely because their state
changes. They remain part of the calculation identity, so the matching N1 pack
correction is recalculated. Changed speed candidates retain VERIFY TAKEOFF
SPEEDS; genuinely unavailable results and actual FMC performance edits retain
their validation. No N1 reset or A/T workaround is introduced.

The tester reports that beta.2 resolved the A/T disconnections. This is user
flight evidence, not full simulator validation. The remaining APPROACH REF
report concerns existing landing VREF owners, which this takeoff patch does
not replace. No VREF or performance-table change is included in this release.

The common MTK metadata recognizes exact beta.1 and beta.2 hooks/payloads.
Standalone updates require uninstall with the matching old installer and
retention of verified backups outside the aircraft. Ownership protection is
unchanged. Standalone package integrity now also covers the ownership guard
and its contract. Independent source review is green. Current disposable dry
checks passed 97 Python methods (62 standalone, 5 earlier-beta upgrades,
15 export and 15 Lua) and 45 released-Core MTK cases using MTK 0.28.2 and
catalog 1.19.0. The 56-row pneumatic regression executes the original .35
ground/N1 producers and confirms the published beta.2 negative control.
No beta.3 simulator, real-thrust calibration or landing-VREF validation is claimed.

# v0.1.0-beta.2

9 October 2026: fixes a ground lifecycle defect in the 27K patch. Ordinary
pressure-altitude, automatic ambient-temperature and gross-weight changes no
longer erase confirmed V-speeds or publish temporary zero N1 targets. A fresh
changed speed candidate requests the original VERIFY TAKEOFF SPEEDS display.
Explicit configuration changes and genuinely unavailable calculations remain
guarded. N1, fixed ceilings, speeds and trim share a captured producer input
and its matching key. The performance tables and interpolation are unchanged.

The tester's A/T report is consistent with an unavailable-N1 transition, but
the exact simulator event is not yet traced. The original heated TAT-probe
indication is unchanged; its ground temperature rise is a separate owner.
No original/modified aircraft script, ACF, plugin, manual or private C++ is
distributed. This remains a Beta and does not claim simulator validation.

MTK users update through their existing owner. Standalone beta.1 users must
uninstall with their retained beta.1 installer, retain its verified state and
backups outside the aircraft, then install beta.2. See README.md.

Current review/dry-test status: pending separate test approval and execution;
no earlier beta.1 PASS is transferred to this runtime correction.

# v0.1.0-beta.1

MTK catalog integration refresh — 8 October 2026: the FMS reset hook now uses
an insertion point that also works with LevelUp's required Weight & Balance
patch. The installer recognizes the previous beta manifest while still
checking its complete receipt, payloads and original backups. Version, release
tag, runtime Lua and performance tables are unchanged. Catalog 1.18.0 offers
27K as an optional, unselected Beta module for both Zibo and LevelUp.
Simulator validation remains open.

Earlier installer refresh — 8 October 2026: the standalone installer now checks MTK
ownership of shared Lua files, the entire reserved SFP27 namespace and unknown
companion files. It rechecks ownership before writes and during recovery.
Existing beta receipts and original backups remain supported. Patch version,
performance tables, Lua payloads and the MTK patch manifest are unchanged.

First installable public beta for upstream Zibo 4.05.35 and the corresponding
LevelUp passenger 737-800 with original .35 Lua and SFP enabled.

- Identified profile: 737-800WSFP2 / CFM56-7B27B1 / FMC 737-800W.2 / FAA C/N brakes.
- Full 27K, fixed 26K/24K derates, manually selected assumed temperature,
  matched N1, dry/wet takeoff speeds, trim and FMC integration.
- Changes existing Zibo SFP calculations that displayed 27K/26K/24K but used
  26K/24K/22K calculation families. Different N1 and V-speeds are expected.
- Same payloads for standalone and MTK; optional, default OFF, order 68.
  Standalone install/uninstall, integrity, receipt/backups and recovery included.
- Other LevelUp variants, SFP OFF and unsupported aircraft keep existing behavior.
- Unsupported Tablet takeoff-distance and automatic optimum ATM/MTOW results
  are withheld. Certified dispatch limits and contaminated-runway data are absent.

Independent source review and dry fixtures cover standalone lifecycle, numerical
table integrity, actual .35 Lua behavior and new-Core/current-catalog MTK
ownership/restore. Real simulator callback timing and calibrated thrust remain
unverified. Please report aircraft version/configuration, conditions, selected
rating/temperature, N1, V-speeds and any log error when testing.

Use MTK 0.28.0 or newer with catalog 1.18.0 or later, or the standalone
installer. Use one installation owner and follow the [installation instructions](README.md)
and [recovery procedure](docs/RECOVERY.md).
