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
