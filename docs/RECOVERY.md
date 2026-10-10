# Standalone interruption recovery

This is the public beta installer contract. Beta.3 installation, uninstall,
interruption recovery and earlier-version handover were validated on disposable
fixtures; see RELEASE_NOTES.md. Simulator validation remains open.

Keep the matching extracted package: ownership, uninstall and interruption
recovery require that same package version. To update a standalone beta.1 or beta.2,
uninstall with its matching old installer first, verify removal, and retain its complete state and
backups outside the aircraft before installing beta.3. Its installer
deliberately refuses another version's receipt or journal. For an MTK-owned installation,
update or restore through MTK instead.

The installer creates `.sfp27-standalone.lock` before changing aircraft files.
`owner.json` records the host, PID and unique token. A normal release removes
only that token's metadata and the otherwise empty directory. Recovery refuses
a live owner, another host, unknown contents or symlinks.

A pending transaction is rolled back by `--recover`: every current target must
match the complete durable plan's before/after hash, and every changed target
must have exactly one matching journal entry. Every backup must match its before
hash. Foreign changes block recovery before mutation. Keep the journal and
backups until that conflict is resolved; do not restore whole scripts over
someone else's later edits.

On successful rollback of a first installation, the installer retains verified
original backups and records a complete `removed` receipt. A subsequent clean
plan/install is then possible. A rollback of an update or uninstall restores
the exact prior receipt, after validating its complete original backup chain.
A minimal, malformed or legacy receipt cannot establish installation ownership.

Process death during first backup preparation, before journal publication,
can leave a backup-only state directory. Aircraft target writes have not begun
at that stage. Without a complete receipt or journal, `--recover` refuses to
report success or infer ownership. Retain that directory and its backups for
manual investigation. After all accessing installers and X-Plane are closed,
verify all three scripts and seven payload paths against their pre-install
state, and confirm no SFP27 hooks/payloads, receipt or pending journal exists.
Only after establishing that this is solely the interrupted first attempt may
the verified backup-only state directory be moved intact outside the aircraft
for retention. Do not delete it or adopt an unknown original baseline.

Process death between lock-directory creation and owner.json publication can
leave an empty lock. Without metadata the tool cannot safely establish that an
installer has exited. It deliberately refuses automatic removal. To resolve:

1. Close X-Plane and all standalone/Toolkit installer processes on the host.
   For a shared aircraft, establish the same on every accessing host.
2. Inspect the exact `.sfp27-standalone.lock` directory. It must be a real,
   empty directory, with no symlink, owner metadata or other contents.
3. Remove only that empty directory (`rmdir`), never a recursive removal.
4. Run the existing `--recover` operation to handle any pending journal, then
   inspect the aircraft and receipt before another install attempt.

Unknown nonempty lock state requires manual ownership investigation. The
installer does not delete it. Clearing a lock never authorizes deleting its
state/backup/journal directory or accepting unknown modified payloads.

Recovery also checks MTK's ownership records and the reserved SFP27 files.
If another installer has acquired a shared file, or unknown files or hooks
have appeared, recovery stops and retains the journal and backups. Resolve
the reported ownership conflict before retrying; deleting MTK state is not a
supported way to authorize recovery.

For a deliberate switch to MTK after a successful standalone uninstall, the
catalog ownership contract rejects any remaining `.sfp27-standalone` state or
lock directory, including a valid removed receipt. Close all accessing
installers and X-Plane; verify the removed receipt and that every SFP27 hook and
payload has been removed while foreign edits remain. Retain the complete
verified state directory intact outside the aircraft. Do not delete backups or
perform that handover on an installed, incomplete or unknown ownership state.
