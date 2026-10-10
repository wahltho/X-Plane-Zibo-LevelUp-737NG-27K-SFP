# Zibo / LevelUp 737-800WSFP2 27K patch

**0.1.0-beta.3 — pneumatic V-speed fix. Beta; simulator validation remains open.**

Independent source review and disposable-fixture dry checks cover this release:
97 Python test methods and 45 released-Core MTK cases passed. The pneumatic
regression also exercises the original .35 N1 producers in 56 combinations.

This patch implements **737-800WSFP2 / CFM56-7B27B1 / FMC 737-800W.2**, with
FAA Category C/N brakes, for upstream Zibo 4.05.35 Lua and the corresponding
LevelUp passenger 737-800. It includes the runtime performance tables for full
27K and fixed 26K/24K derates. The original `zibomod.xpl` and aircraft ACF stay
unchanged. No private C++ plugin is required.

Public repository: [X-Plane-Zibo-LevelUp-737NG-27K-SFP](https://github.com/wahltho/X-Plane-Zibo-LevelUp-737NG-27K-SFP).
Release package: [v0.1.0-beta.3](https://github.com/wahltho/X-Plane-Zibo-LevelUp-737NG-27K-SFP/releases/tag/v0.1.0-beta.3).
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
- Background pressure-altitude, automatic ambient-temperature and fuel-weight
  and pneumatic-load updates preserve confirmed speeds and valid N1 targets. Changed speed
  candidates use the existing VERIFY TAKEOFF SPEEDS display; explicit
  configuration edits and genuinely unavailable results retain validation.

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
The ownership policy is registered in catalog schema 2. The current catalog
1.19.0 includes the selectable Beta module in both Zibo and LevelUp patch groups.
Use MTK 0.28.2 or newer with that catalog or a later compatible version. The patch remains
optional and is not selected automatically.

### Install through MTK

1. Close X-Plane. Start MTK with an internet connection and select the aircraft.
2. Let MTK refresh its catalog, then review the product's patch package.
3. Under Advanced, select **737-800WSFP2 27K / SFP (Beta)** and apply the
   reviewed selection through MTK. Keep any already installed patches selected.
4. Restart X-Plane completely. Enable SFP on the supported passenger -800.

MTK can add this module when it already manages the shared Lua files, including
the required LevelUp maintenance patches. A standalone installation must first
be removed through its own installer; matching file hashes alone do not prove
ownership or a complete restore chain.

### Updating an earlier beta

For an MTK-owned installation, update the existing patch selection through MTK
and keep its other modules selected. The catalog reads this patch's latest
release; no manual copy of aircraft scripts is needed.

For a standalone beta.1 or beta.2 installation, close X-Plane and uninstall using the
retained installer for that **installed version** first. Confirm successful removal, then retain
the complete verified `.sfp27-standalone` state/backups outside the aircraft.
Install beta.3 from its extracted ZIP. Its installer deliberately refuses
another version's receipt; it does not adopt another version's original-backup chain.
Do not delete backups, manually remove hooks, or combine installation owners.

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

The installer also reads MTK's saved ownership records. If MTK manages any
shared FMS, calculation or Tablet file, make the change through MTK. This check
applies even if 27K has not been installed yet. Broken MTK state, unknown
`B738.sfp27_*` files and malformed or case-changed SFP27 markers block writes.
Ownership, receipts and originals are checked again during the transaction
and before recovery. The receipt/backup format remains unchanged; ownership
and uninstall are deliberately restricted to the matching package version.

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
it. For beta.3, the registered policy and released MTK 0.28.2 Core passed
45 cases with catalog 1.19.0, including exact beta.1/beta.2 upgrades,
ownership refusal in both directions, unknown markers, receiptless state and
locks, complete restore and required LevelUp W&B/VREF/Tablet combinations.
Use MTK 0.28.2 or newer with the current compatible catalog. MTK obtains
the catalog online and keeps a verified cache. The catalog must contain the full `.sfp27-standalone` directory and
lock evidence rules. Package metadata alone does not register those rules.

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

Beta.3 passed independent source review and current disposable-fixture dry
tests: 62 standalone, 5 earlier-beta upgrade, 15 export and 15 Lua methods,
plus 45 cases through the actual released MTK Core. The pneumatic matrix
covers both aircraft variants, both callback orders and per-engine N1 loading;
the published beta.2 payload reproduces the speed-clearing regression.
These checks do not constitute simulator or actual-thrust validation.
Current status and activation limits are recorded in
[PREPARATION_STATUS.json](PREPARATION_STATUS.json).

The public package includes runtime tables and patch files. Raw audit data,
manuals, source provenance, internal reviews and authoring tools remain local.
Support follows the other community patches through the
[wahltho Discord server](https://discord.gg/ySS88PMuyC).
