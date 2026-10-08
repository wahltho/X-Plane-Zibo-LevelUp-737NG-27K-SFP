# Zibo / LevelUp 737-800WSFP2 27K patch

**0.1.0-beta.1 — installable public beta; simulator validation remains open.**

This patch implements **737-800WSFP2 / CFM56-7B27B1 / FMC 737-800W.2**, with
FAA Category C/N brakes, for upstream Zibo 4.05.35 Lua and the corresponding
LevelUp passenger 737-800. It includes the runtime performance tables for full
27K and fixed 26K/24K derates. The original `zibomod.xpl` and aircraft ACF stay
unchanged. No private C++ plugin is required.

Public repository: [X-Plane-Zibo-LevelUp-737NG-27K-SFP](https://github.com/wahltho/X-Plane-Zibo-LevelUp-737NG-27K-SFP).
Download the [v0.1.0-beta.1 package](https://github.com/wahltho/X-Plane-Zibo-LevelUp-737NG-27K-SFP/releases/tag/v0.1.0-beta.1).
See [release notes](RELEASE_NOTES.md) for scope and validation.

## Changes existing Zibo SFP calculations

**Installing this patch intentionally changes results for existing Zibo SFP
users.** Original 4.05.35 already displays 27K/26K/24K when SFP is enabled, but
its selectable takeoff calculations still use the 26K/24K/22K families. This
patch replaces that calculation with the matched 27K/26K/24K N1,
assumed-temperature and takeoff-speed families. Expect different N1, V-speeds
and trim results on an installation that already displayed a 27K option.

The existing SFP setting activates the profile on the supported aircraft;
there is no additional engine-option switch. Installing the patch opts that
configuration into the identified SFP2 profile. A single upstream SFP switch
cannot identify every aircraft's hardware configuration or effectivity, so the
patch does not claim universal SFP1/SFP2/SFP3 applicability.

## Included behavior

- Full 27K, fixed 26K/24K derates and manually entered assumed temperature,
  with a separate matching N1 and ATM table family for each rating.
- Dry/wet takeoff V1/VR/V2, pressure-altitude/temperature/wind/slope
  adjustments, V1(MCG) and stabilizer trim for flaps 1, 5, 10, 15 and 25.
- Consistent FMC labels and automatic-speed acceptance, the original SFP
  persistence, and a ground-latched fixed-rating ceiling. Removing assumed
  temperature retains a selected 26K/24K derate.
- Explicit missing cells and bounded interpolation. Unavailable combinations
  do not borrow another aircraft's tables or extrapolate beyond the data.
- Suppression of unsupported Tablet takeoff-distance and optimized ATM/MTOW
  results, including stale results from an earlier calculation.

## Aircraft scope

| Aircraft | Activation |
|---|---|
| LevelUp passenger -800, native variant ID 0 | SFP enabled; initialization on the ground |
| Zibo passenger -800, native ID -1 and legacy 73x 0 | SFP enabled; initialization on the ground |
| LevelUp -600 / -700 / -900 / -900ER | No new profile; existing calculations retained |
| BBJ / other IDs / SFP off | No new profile |

First activation after an airborne reload is unsupported. The -900ER has its
own performance family and does not establish compatibility with the -800.

## Standalone and MTK

Both installation paths use the same seven payload copies and 27 structural
operations on three existing Lua scripts. Complete original aircraft scripts
are not distributed. `package-manifest.json` uses supported MTK schema 3
operations, module `27k-sfp`, optional and disabled by default, order 68.
It uses `migrate-marked-block-v1`, `exact-text-replacements-v1` and `copy-file-v1`.
The ownership contract is registered in catalog schema 2 / version 1.16.0.
MTK integration was tested with Core 0.28.0 and that current catalog. Availability
in the Toolkit's selectable download catalog is a separate catalog update;
installing this package does not add or select a catalog entry automatically.

### Standalone install and uninstall

1. Download and extract the release ZIP to a folder outside the aircraft.
2. Close X-Plane and all other installers before changing aircraft files.
3. Run the installer from the extracted package, passing the aircraft folder
   that contains `b738.acf` or the LevelUp ACF files.

On macOS / Linux:

```bash
python3 z_Install.py "/path/to/aircraft" --plan
python3 z_Install.py "/path/to/aircraft"
python3 z_Install.py "/path/to/aircraft" --uninstall
```

On Windows, use `py -3` instead of `python3`. `--plan` inspects without writing.
The normal command installs or repeats an unchanged installation; `--uninstall`
removes this installer's verified hooks and payloads while preserving unrelated
edits. Restart X-Plane completely after installation or removal. Keep the
extracted package and the installer's state/backups for later uninstall.

This installer does not remove an MTK-owned installation. Use MTK's uninstall
or restore for that owner. Unknown or modified ownership is refused rather
than silently overwritten.

The standalone installer requires Python 3.10+. Before mutation it verifies
package integrity, the complete target inventory, installed hook bodies,
payload identity, original backups and its own installation receipt. Unknown,
partial, duplicate or modified owned blocks and missing/corrupt ownership
records block. Foreign edits outside owned hooks are preserved. Writes use
whole-package preflight, backups, a journal, rollback, process checks and a
lock. See [recovery](docs/RECOVERY.md).

Use one installation owner. To switch from standalone to MTK, uninstall with
the standalone installer first. Close all installers and X-Plane, verify the
removed receipt and absence of SFP27 hooks/payloads, then retain the complete
verified `.sfp27-standalone` directory outside the aircraft. The current catalog
contract deliberately rejects that state while it remains in the aircraft.
An installer must not
adopt an already patched file as the original merely because its bytes match.

`mtk-ownership-policy.json` is the supported
catalog-schema-2 policy fragment for standalone evidence, seven payload paths
and the complete reserved SFP27 marker namespace on all three scripts. It must
be registered in the MTK catalog; the package manifest does not auto-register
it. The registered policy and actual new Core passed 28 installer cases,
including genuine ownership refusal in both directions, unknown markers,
receiptless state and locks, complete restore and VREF/Tablet combinations.
Use MTK 0.28.0 or newer with the corrected current catalog. Its offline bundle
must also include the complete `.sfp27-standalone` and lock evidence rules;
an older application cannot gain this protection from package metadata alone.

## Performance and validation boundaries

Matching AFM/Performance Dispatch data remains necessary for certified runway
field limits, accelerate-stop/go, climb-limited MTOW, obstacle clearance,
brake/tire limits and automatic optimum assumed temperature. This patch does
not supply those functions. Contaminated/slippery runway performance and SFP
hardware changes are outside v0.1. Existing climb, cruise, continuous and
go-around producers are retained.

Interpolation and integer-speed rounding remain model conventions rather than
a verified exact FMC convention. Static analysis supports the original .35
Linux plugin's N1-to-force interface, but does not prove calibrated installed
27K thrust, complete callback timing or equivalent Mac/Windows behavior.
Unavailable N1 retains original MAN/unavailable handling; a plugin fallback
is not a calculated value from this profile.

The package passed independent review and disposable-fixture dry tests.
Those checks do not constitute simulator or actual-thrust validation.
Current status and activation limits are recorded in
[PREPARATION_STATUS.json](PREPARATION_STATUS.json).

The public package includes runtime tables and patch files. Raw audit data,
manuals, source provenance, internal reviews and authoring tools remain local.
Support follows the other community patches through the
[wahltho Discord server](https://discord.gg/ySS88PMuyC).
