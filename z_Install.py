#!/usr/bin/env python3
"""Standalone installer for the same payloads/operations as the MTK draft.

Development preparation: installation remains blocked until separately approved
validation closes PREPARATION_STATUS.json. No plugin or ACF is ever modified.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import uuid

import patchlib
import standalone_guard

PACKAGE = Path(__file__).resolve().parent
STATE_NAME = ".sfp27-standalone"
ALLOWED_DIRECTORIES = {"B738.a_fms", "B738.calc", "B738.tablet"}
ALLOWED_FILES = {
    "B738.a_fms": {"B738.a_fms.lua", "B738.sfp27_data.lua", "B738.sfp27_core.lua", "B738.sfp27_fms.lua"},
    "B738.calc": {"B738.calc.lua", "B738.sfp27_data.lua", "B738.sfp27_core.lua", "B738.sfp27_calc.lua"},
    "B738.tablet": {"B738.tablet.lua", "B738.sfp27_tablet.lua"},
}
PACKAGE_ID = "wahltho.zibo-levelup-737ng.27k-sfp"


class OwnershipBoundary:
    """Catalog checks around the existing native receipt/journal transaction."""

    def __init__(self, root, manifest):
        absolute = Path(root).absolute()
        standalone_guard.safe(Path(absolute.anchor), absolute.relative_to(absolute.anchor).as_posix())
        self.root = root
        contract = json.loads((PACKAGE / "standalone-ownership.json").read_bytes(), object_pairs_hook=unique_object)
        if contract.get("schemaVersion") != 1 or contract.get("policy", {}).get("packageId") != PACKAGE_ID:
            raise ValueError("Unsupported standalone ownership contract")
        self.policy = contract["policy"]
        self.targets = {op["relativePath"] for op in manifest["modules"][0]["targets"]}
        if any(not any(standalone_guard.covered(p, r) for p in self.policy["targetPaths"])
               for r in self.targets):
            raise ValueError("Package target is outside its catalog ownership contract")
        self.contents, self.modes = self.capture()
        self.mtk = standalone_guard.check_mtk(root, self.policy["targetPaths"], PACKAGE_ID)
        self.receipt = standalone_guard.read(root, STATE_NAME + "/receipt.json")
        self.backups = {}
        if self.receipt is not None:
            receipt = validate_receipt(root, manifest, json.loads(self.receipt, object_pairs_hook=unique_object))
            for relative, item in receipt["targets"].items():
                if item["originalSha256"] is not None:
                    path = STATE_NAME + "/backups/" + item["originalSha256"] + "/" + relative
                    self.backups[path] = item["originalSha256"]

    def capture(self):
        paths = set(self.targets)
        for pattern in self.policy["targetPaths"]:
            for relative in standalone_guard.expand(self.root, pattern):
                if relative not in self.targets and standalone_guard.read(self.root, relative) is not None:
                    raise ValueError("Unknown file in reserved SFP27 scope: " + relative)
                paths.add(relative)
        contents, modes = {}, {}
        for relative in sorted(paths):
            content = standalone_guard.read(self.root, relative)
            if relative not in self.targets:
                continue
            standalone_guard.marker_fingerprints(content, self.policy, relative)
            contents[relative] = content
            path = standalone_guard.safe(self.root, relative)
            modes[relative] = path.stat().st_mode & 0o777 if content is not None else 0o644
        return contents, modes

    def recheck(self, contents=None, receipt=None):
        expected = self.contents if contents is None else contents
        observed, modes = self.capture()
        if observed != expected or any(modes[r] != self.modes[r] for r in expected if expected[r] is not None):
            raise ValueError("Aircraft target or reserved scope changed after preparation")
        if standalone_guard.check_mtk(self.root, self.policy["targetPaths"], PACKAGE_ID) != self.mtk:
            raise ValueError("MTK ownership state changed after preparation")
        expected_receipt = self.receipt if receipt is None else receipt
        if standalone_guard.read(self.root, STATE_NAME + "/receipt.json") != expected_receipt:
            raise ValueError("Standalone receipt changed after preparation")
        for relative, expected_hash in self.backups.items():
            if digest(standalone_guard.read(self.root, relative) or b"") != expected_hash:
                raise ValueError("Original backup changed after preparation: " + relative)


class PreparedChanges(list):
    def __init__(self, changes, ownership):
        super().__init__(changes)
        self.ownership = ownership


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=0o644):
    descriptor, temporary = tempfile.mkstemp(prefix=".sfp27-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def safe_target(root, relative):
    parts = Path(relative).parts
    if len(parts) != 5 or parts[:3] != ("plugins", "xlua", "scripts") or parts[3] not in ALLOWED_DIRECTORIES:
        raise ValueError("Out-of-scope aircraft target: " + relative)
    if parts[4] not in ALLOWED_FILES[parts[3]]:
        raise ValueError("Out-of-scope aircraft filename: " + relative)
    path = standalone_guard.safe(root, relative)
    for parent in [path] + list(path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlink aircraft target: " + relative)
    if not path.parent.is_dir() or not path.resolve().is_relative_to(root):
        raise ValueError("Missing/unsafe script directory: " + relative)
    return path


def verify_package():
    integrity = json.loads((PACKAGE / "installer-manifest.json").read_text())
    for name, expected in integrity["files"].items():
        path = PACKAGE / name
        if path.is_symlink() or not path.resolve().is_relative_to(PACKAGE):
            raise ValueError("Unsafe package payload: " + name)
        content = path.read_bytes()
        if len(content) != expected["size"] or digest(content) != expected["sha256"]:
            raise ValueError("Package integrity mismatch: " + name)
    return json.loads((PACKAGE / "package-manifest.json").read_text())


def state_file(root, relative):
    state = root / STATE_NAME
    path = standalone_guard.safe(root, STATE_NAME + "/" + relative)
    for parent in [path] + list(path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlink package state path: " + str(parent))
    if not path.resolve().is_relative_to(state):
        raise ValueError("Unsafe package state path")
    return path


def marker_inventory(manifest):
    known = {}
    for operation in manifest["modules"][0]["targets"]:
        if operation["operation"] == "copy-file-v1":
            continue
        payload = json.loads((PACKAGE / operation["payload"]).read_bytes())
        lines = ([payload["beginMarker"], payload["endMarker"]]
                 if "beginMarker" in payload else
                 [line for item in payload["replacements"] for line in item["newLines"]])
        known.setdefault(operation["relativePath"], set()).update(
            line for line in lines if line.startswith(("-- BEGIN SFP27 ", "-- END SFP27 ")))
    return known


def check_markers(content, relative, known):
    markers = [line.strip() for line in patchlib.decode(content)[0]
               if re.match(r"^\s*--\s*(?:BEGIN|END)\s+SFP27", line)]
    if any(line not in known.get(relative, set()) for line in markers) or len(markers) != len(set(markers)):
        raise ValueError("Unknown/duplicate SFP27 hooks: " + relative)
    return bool(markers)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate standalone receipt field: " + key)
        result[key] = value
    return result


def load_receipt(root, manifest):
    path = state_file(root, "receipt.json")
    if not path.is_file():
        if (root / STATE_NAME).exists():
            raise ValueError("Incomplete standalone state; retain its backups and recover first")
        return None
    receipt = json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    return validate_receipt(root, manifest, receipt)


def validate_receipt(root, manifest, receipt):
    if not isinstance(receipt, dict) or receipt.get("packageId") != PACKAGE_ID:
        raise ValueError("Foreign standalone state")
    if (type(receipt.get("schemaVersion")) is not int or receipt["schemaVersion"] != 1
            or receipt.get("packageVersion") != manifest["packageVersion"]
            or receipt.get("manifestSha256") not in {
                digest((PACKAGE / "package-manifest.json").read_bytes()),
                # Same beta before the W&B-compatible reset anchor. Targets,
                # hook bodies and runtime payloads are identical; the complete
                # receipt, originals and installed hooks are still verified.
                "62670408deaacb9fd86b77b2536b0aa13fda07a503d917ec26e658b68d4862c5",
            }
            or receipt.get("state") not in ("installed", "removed")
            or receipt.get("uninstall") is not (receipt.get("state") == "removed")):
        raise ValueError("Unsupported/incomplete standalone receipt; retain original backups")
    operations = manifest["modules"][0]["targets"]
    targets = receipt.get("targets")
    expected = {op["relativePath"] for op in operations}
    if not isinstance(targets, dict) or set(targets) != expected:
        raise ValueError("Incomplete standalone ownership inventory")
    changes = receipt.get("changes")
    if not isinstance(changes, list):
        raise ValueError("Invalid standalone transaction history")
    seen = set()
    for item in changes:
        if (not isinstance(item, dict) or set(item) != {"path", "before", "after", "mode"}
                or item["path"] not in expected or item["path"] in seen
                or type(item["mode"]) is not int or not 0 <= item["mode"] <= 0o777):
            raise ValueError("Invalid standalone transaction history entry")
        seen.add(item["path"])
        for key in ("before", "after"):
            value = item[key]
            if value is not None and (not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None):
                raise ValueError("Invalid standalone transaction history hash")
    copies = {op["relativePath"]: op["resultSha256"] for op in operations
              if op["operation"] == "copy-file-v1"}
    for relative, item in targets.items():
        if not isinstance(item, dict) or set(item) != {"originalSha256", "installedSha256", "mode"}:
            raise ValueError("Invalid standalone ownership entry: " + relative)
        if type(item["mode"]) is not int or not 0 <= item["mode"] <= 0o777:
            raise ValueError("Invalid standalone file mode: " + relative)
        for key in ("originalSha256", "installedSha256"):
            value = item[key]
            if value is not None and (not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None):
                raise ValueError("Invalid standalone ownership hash: " + relative)
        original = item["originalSha256"]
        if relative in copies:
            expected_copy = copies[relative] if receipt["state"] == "installed" else None
            if original is not None or item["installedSha256"] != expected_copy:
                raise ValueError("Invalid standalone payload ownership: " + relative)
        elif original is None or item["installedSha256"] is None:
            raise ValueError("Missing standalone original script identity: " + relative)
        if original is not None:
            saved = state_file(root, "backups/" + original + "/" + relative)
            if not saved.is_file() or digest(saved.read_bytes()) != original:
                raise ValueError("Missing/modified standalone original backup: " + relative)
    return receipt


def check_content_ownership(contents, manifest, owned, uninstall):
    known = marker_inventory(manifest)
    operations = manifest["modules"][0]["targets"]
    for operation in operations:
        relative = operation["relativePath"]
        content = contents[relative]
        if content is not None:
            present = (operation["operation"] == "copy-file-v1" or
                       check_markers(content, relative, known))
            if present and not owned:
                raise ValueError("SFP27 already has a different owner (MTK/manual): " + relative)
    if owned:
        for relative, markers in known.items():
            content = contents[relative]
            if content is None:
                raise ValueError("Missing installed standalone script: " + relative)
            observed = {line.strip() for line in patchlib.decode(content)[0]
                        if re.match(r"^\s*--\s*(?:BEGIN|END)\s+SFP27", line)}
            if observed != markers:
                raise ValueError("Incomplete installed standalone hooks: " + relative)
            # Validate all installed bodies by their exact inverse. Unrelated
            # bytes outside owned blocks need not match the historical backup.
            for op in reversed(operations):
                if op["relativePath"] == relative:
                    payload = json.loads((PACKAGE / op["payload"]).read_bytes())
                    content = patchlib.apply(content, payload, True)
        for op in operations:
            if op["operation"] == "copy-file-v1":
                content = contents[op["relativePath"]]
                if content is None or digest(content) != op["resultSha256"]:
                    raise ValueError("Missing/modified installed standalone payload: " + op["relativePath"])
    if uninstall and not owned:
        raise ValueError("No installed standalone receipt; refusing to remove another owner's patch")


def read_targets(root, manifest):
    contents, modes = {}, {}
    for relative in {op["relativePath"] for op in manifest["modules"][0]["targets"]}:
        path = safe_target(root, relative)
        contents[relative] = path.read_bytes() if path.is_file() else None
        modes[relative] = path.stat().st_mode & 0o777 if contents[relative] is not None else 0o644
    return contents, modes


def check_ownership(root, manifest, uninstall):
    receipt = load_receipt(root, manifest)
    contents, _ = read_targets(root, manifest)
    check_content_ownership(contents, manifest, receipt is not None and receipt["state"] == "installed", uninstall)
    return receipt


def transform(contents, manifest, uninstall):
    operations = manifest["modules"][0]["targets"]
    if uninstall:
        operations = list(reversed(operations))
    desired = dict(contents)
    for operation in operations:
        relative = operation["relativePath"]
        content = desired[relative]
        payload = (PACKAGE / operation["payload"]).read_bytes()
        if operation["operation"] == "copy-file-v1":
            known = operation.get("sourceSha256", []) + [digest(payload)]
            if content is not None and digest(content) not in known:
                raise ValueError("Foreign/modified SFP27 payload: " + relative)
            desired[relative] = None if uninstall else payload
        else:
            if content is None:
                raise ValueError("Missing upstream script: " + relative)
            desired[relative] = patchlib.apply(content, json.loads(payload), uninstall)
    known = marker_inventory(manifest)
    for relative, content in desired.items():
        if content is None or not relative.endswith(("/B738.a_fms.lua", "/B738.calc.lua", "/B738.tablet.lua")):
            continue
        marked = check_markers(content, relative, known)
        if uninstall and marked:
            raise ValueError("Unknown SFP27 hooks remain: " + relative)
    return desired


def prepare(root, manifest, uninstall):
    ownership = OwnershipBoundary(root, manifest)
    receipt = load_receipt(root, manifest)
    originals, modes = read_targets(root, manifest)
    check_content_ownership(originals, manifest, receipt is not None and receipt["state"] == "installed", uninstall)
    desired = transform(originals, manifest, uninstall)
    ownership.recheck()
    return PreparedChanges([(relative, originals[relative], new, modes[relative])
                            for relative, new in desired.items() if new != originals[relative]], ownership)


def backup(root, state, changes, ownership):
    for relative, old, _, mode in changes:
        ownership.recheck()
        if old is None:
            continue
        path = state / "backups" / digest(old) / relative
        standalone_guard.safe(root, path.relative_to(root).as_posix())
        # Walk before mkdir; a foreign backup tree is never followed.
        for parent in [path] + list(path.parents):
            if parent == state:
                break
            if parent.is_symlink():
                raise ValueError("Symlink backup path: " + str(parent))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != old:
                raise ValueError("Backup collision: " + relative)
        else:
            atomic_write(path, old, mode)


def transaction(root, changes, uninstall):
    manifest = verify_package()
    reviewed = getattr(changes, "ownership", None)
    if reviewed is not None:
        reviewed.recheck()
    ownership = OwnershipBoundary(root, manifest)
    prior = check_ownership(root, manifest, uninstall)
    expected = {op["relativePath"] for op in manifest["modules"][0]["targets"]}
    delta = {r: (old, new, mode) for r, old, new, mode in changes}
    if len(delta) != len(changes) or not set(delta).issubset(expected):
        raise ValueError("Invalid transaction target inventory")
    if any(old == new for old, new, _ in delta.values()):
        raise ValueError("No-op target in transaction change inventory")
    plan, before_contents = {}, {}
    for relative in sorted(expected):
        path = safe_target(root, relative)
        current = path.read_bytes() if path.is_file() else None
        mode = path.stat().st_mode & 0o777 if current is not None else 0o644
        old, new, mode = delta.get(relative, (current, current, mode))
        if current != old:
            raise ValueError("Aircraft changed after preparation: " + relative)
        before_contents[relative] = old
        plan[relative] = {"beforeSha256": digest(old) if old is not None else None,
                          "afterSha256": digest(new) if new is not None else None, "mode": mode}
    check_content_ownership(before_contents, manifest, prior is not None and prior["state"] == "installed", uninstall)
    after_contents = transform(before_contents, manifest, uninstall)
    if any(plan[r]["afterSha256"] != (digest(data) if data is not None else None)
           for r, data in after_contents.items()):
        raise ValueError("Transaction plan differs from package operations")
    originals = {r: (digest(old) if old is not None else None, mode)
                 for r, old, _, mode in changes}
    target_records = {}
    for op in manifest["modules"][0]["targets"]:
        relative = op["relativePath"]
        if prior is not None and prior["state"] == "installed":
            original, mode = prior["targets"][relative]["originalSha256"], prior["targets"][relative]["mode"]
        else:
            if relative not in originals:
                raise ValueError("First installation must establish every target's original state")
            original, mode = originals[relative]
        target_records[relative] = {"originalSha256": original, "mode": mode}
    # A stale plan must fail before even creating state or backup artifacts.
    for relative, old in before_contents.items():
        path = safe_target(root, relative)
        if (path.read_bytes() if path.exists() else None) != old:
            raise ValueError("Aircraft changed after preparation: " + relative)
    ownership.recheck()
    state = standalone_guard.safe(root, STATE_NAME)
    if state.is_symlink():
        raise ValueError("Symlink package state directory")
    state.mkdir(exist_ok=True)
    journal_path = state_file(root, "pending.json")
    if journal_path.exists():
        raise ValueError("Interrupted standalone transaction: run --recover before another operation")
    receipt_path = state_file(root, "receipt.json")
    receipt_before = receipt_path.read_bytes() if receipt_path.is_file() else None
    backup(root, state, changes, ownership)
    # Payloads before hooks on install; hooks before payload removal on uninstall.
    ordered = sorted(changes, key=lambda item: ("/B738.sfp27_" not in item[0]) != uninstall)
    journal = {"schemaVersion": 1, "packageId": PACKAGE_ID,
               "packageVersion": manifest["packageVersion"],
               "manifestSha256": digest((PACKAGE / "package-manifest.json").read_bytes()),
               "targets": target_records, "plan": plan, "uninstall": uninstall,
               "previousReceipt": base64.b64encode(receipt_before).decode() if receipt_before is not None else None,
               "changes": [{"path": r, "before": digest(a) if a is not None else None,
                            "after": digest(b) if b is not None else None, "mode": m}
                           for r, a, b, m in ordered]}
    ownership.recheck()
    atomic_write(journal_path, (json.dumps(journal, indent=2) + "\n").encode())
    try:
        expected_contents = dict(before_contents)
        for relative, old, new, mode in ordered:
            ownership.recheck(expected_contents)
            path = safe_target(root, relative)
            if (path.read_bytes() if path.exists() else None) != old:
                raise ValueError("Concurrent target modification: " + relative)
            if new is None:
                path.unlink()
            else:
                atomic_write(path, new, mode)
            expected_contents[relative] = new
        for relative, _, new, _ in ordered:
            path = safe_target(root, relative)
            if (path.read_bytes() if path.exists() else None) != new:
                raise ValueError("Readback mismatch: " + relative)
        for relative, item in target_records.items():
            path = safe_target(root, relative)
            current_hash = digest(path.read_bytes()) if path.is_file() else None
            if current_hash != plan[relative]["afterSha256"]:
                raise ValueError("Target changed before installation receipt: " + relative)
            item["installedSha256"] = current_hash
        receipt = {**journal, "schemaVersion": 1, "packageVersion": manifest["packageVersion"],
                   "manifestSha256": digest((PACKAGE / "package-manifest.json").read_bytes()),
                   "targets": target_records, "state": "removed" if uninstall else "installed"}
        ownership.recheck(after_contents)
        receipt_bytes = (json.dumps(receipt, indent=2) + "\n").encode()
        atomic_write(receipt_path, receipt_bytes)
        ownership.recheck(after_contents, receipt_bytes)
        journal_path.unlink()
    except BaseException:
        # Recovery checks the whole transaction before touching any target and
        # refuses to overwrite a concurrently changed file. The journal remains
        # if rollback itself is interrupted or encounters a conflict.
        recover_transaction(root)
        raise


def recover_transaction(root):
    ownership = OwnershipBoundary(root, verify_package())
    journal_path = state_file(root, "pending.json")
    if not journal_path.is_file():
        if (root / STATE_NAME).exists():
            load_receipt(root, verify_package())
        return
    journal = json.loads(journal_path.read_bytes(), object_pairs_hook=unique_object)
    manifest = verify_package()
    expected = {op["relativePath"] for op in manifest["modules"][0]["targets"]}
    if (not isinstance(journal, dict) or journal.get("packageId") != PACKAGE_ID
            or type(journal.get("schemaVersion")) is not int or journal["schemaVersion"] != 1
            or journal.get("packageVersion") != manifest["packageVersion"]
            or journal.get("manifestSha256") != digest((PACKAGE / "package-manifest.json").read_bytes())
            or not isinstance(journal.get("targets"), dict) or set(journal["targets"]) != expected
            or type(journal.get("uninstall")) is not bool):
        raise ValueError("Foreign transaction journal")
    plan = journal.get("plan")
    if not isinstance(plan, dict) or set(plan) != expected:
        raise ValueError("Incomplete durable recovery plan")
    before_contents = {}
    for relative, item in plan.items():
        if (not isinstance(item, dict) or set(item) != {"beforeSha256", "afterSha256", "mode"}
                or type(item["mode"]) is not int or not 0 <= item["mode"] <= 0o777):
            raise ValueError("Invalid recovery plan entry")
        for key in ("beforeSha256", "afterSha256"):
            value = item[key]
            if value is not None and (not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None):
                raise ValueError("Invalid recovery plan hash")
        path = safe_target(root, relative)
        current = path.read_bytes() if path.is_file() else None
        current_hash = digest(current) if current is not None else None
        if current_hash not in (item["beforeSha256"], item["afterSha256"]):
            raise ValueError("Recovery conflict; aircraft file changed: " + relative)
        before = item["beforeSha256"]
        old = current if current_hash == before else None
        if before is not None and item["beforeSha256"] != item["afterSha256"]:
            backup_path = state_file(root, "backups/" + before + "/" + relative)
            old = backup_path.read_bytes()
            if digest(old) != before:
                raise ValueError("Recovery backup mismatch: " + relative)
        before_contents[relative] = old
    changes = journal.get("changes")
    if not isinstance(changes, list):
        raise ValueError("Invalid recovery change inventory")
    recovery, seen = [], set()
    for item in reversed(changes):
        if not isinstance(item, dict) or set(item) != {"path", "before", "after", "mode"}:
            raise ValueError("Invalid transaction entry")
        relative, before, after, mode = item["path"], item["before"], item["after"], item["mode"]
        if relative not in expected or relative in seen or type(mode) is not int or not 0 <= mode <= 0o777:
            raise ValueError("Invalid transaction entry")
        seen.add(relative)
        if (before, after, mode) != (plan[relative]["beforeSha256"], plan[relative]["afterSha256"], plan[relative]["mode"]):
            raise ValueError("Transaction entry differs from durable recovery plan")
        path = safe_target(root, relative)
        current = path.read_bytes() if path.is_file() else None
        current_hash = digest(current) if current is not None else None
        if current_hash not in (before, after):
            raise ValueError("Recovery conflict; aircraft file changed: " + relative)
        old = None
        if before is not None:
            backup_path = state_file(root, "backups/" + before + "/" + relative)
            old = backup_path.read_bytes()
            if digest(old) != before:
                raise ValueError("Recovery backup mismatch: " + relative)
        recovery.append((path, current, old, mode))
    changed_targets = {relative for relative, item in plan.items() if item["beforeSha256"] != item["afterSha256"]}
    if seen != changed_targets:
        raise ValueError("Incomplete transaction change inventory")
    receipt_path = state_file(root, "receipt.json")
    encoded = journal.get("previousReceipt")
    previous = base64.b64decode(encoded, validate=True) if encoded is not None else None
    prior = None
    if previous is not None:
        prior = validate_receipt(root, manifest, json.loads(previous, object_pairs_hook=unique_object))
        originals = {relative: {"originalSha256": item["originalSha256"], "mode": item["mode"]}
                     for relative, item in prior["targets"].items()}
        # A reinstall after a removed receipt establishes current originals.
        if prior["state"] == "removed":
            originals = {relative: {"originalSha256": item["beforeSha256"], "mode": item["mode"]}
                         for relative, item in plan.items()}
        if journal["targets"] != originals:
            raise ValueError("Recovery original inventory differs from validated owner")
    check_content_ownership(before_contents, manifest, prior is not None and prior["state"] == "installed", journal["uninstall"])
    after_contents = transform(before_contents, manifest, journal["uninstall"])
    if any(plan[r]["afterSha256"] != (digest(data) if data is not None else None)
           for r, data in after_contents.items()):
        raise ValueError("Recovery plan differs from package operations")
    if previous is None:
        # Initial rollback retains its verified backups and publishes a removed
        # receipt. It must not strand an ownerless state directory that blocks
        # the next clean plan/install after successful recovery.
        if seen != expected:
            raise ValueError("Incomplete initial recovery inventory")
        originals = {relative: {"originalSha256": item["beforeSha256"], "mode": item["mode"]}
                     for relative, item in plan.items()}
        if journal["targets"] != originals:
            raise ValueError("Recovery original inventory differs from initial plan")
        targets = {relative: {**item, "installedSha256": item["originalSha256"]}
                   for relative, item in originals.items()}
        previous = (json.dumps({**journal, "uninstall": True, "state": "removed", "targets": targets}, indent=2) + "\n").encode()
        validate_receipt(root, manifest, json.loads(previous))
    expected_contents = dict(ownership.contents)
    for path, current, old, mode in recovery:
        ownership.recheck(expected_contents)
        if (path.read_bytes() if path.is_file() else None) != current:
            raise ValueError("Concurrent modification during recovery")
        if old is None:
            if path.exists():
                path.unlink()
        else:
            atomic_write(path, old, mode)
        expected_contents[path.relative_to(root).as_posix()] = old
        if (path.read_bytes() if path.is_file() else None) != old:
            raise ValueError("Recovery readback mismatch")
    for relative, item in plan.items():
        path = safe_target(root, relative)
        if (digest(path.read_bytes()) if path.is_file() else None) != item["beforeSha256"]:
            raise ValueError("Concurrent target change before recovery receipt: " + relative)
    ownership.recheck(before_contents)
    atomic_write(receipt_path, previous)
    ownership.recheck(before_contents, previous)
    journal_path.unlink()


def ensure_offline():
    command = ["tasklist", "/FO", "CSV", "/NH"] if os.name == "nt" else ["ps", "-A", "-o", "comm="]
    output = subprocess.check_output(command, text=True, errors="replace")
    for line in output.splitlines():
        name = Path(line.strip().strip('"').split('\",\"')[0]).name.lower()
        if name in ("x-plane", "x-plane.exe", "x-plane-x86_64", "x-plane-arm64"):
            raise ValueError("Close X-Plane before changing the aircraft")


def acquire_lock(root, recover):
    lock = standalone_guard.safe(root, STATE_NAME + ".lock")
    if lock.is_symlink():
        raise ValueError("Symlink installer lock")
    if lock.exists():
        if not recover:
            raise ValueError("Installer lock present; use --recover after its owner exits")
        metadata = lock / "owner.json"
        if metadata.is_symlink() or {p.name for p in lock.iterdir()} != {"owner.json"}:
            raise ValueError("Unknown installer lock contents")
        owner = json.loads(metadata.read_bytes())
        if owner.get("host") != platform.node():
            raise ValueError("Installer lock belongs to another host")
        pid = int(owner["pid"])
        if pid <= 0:
            raise ValueError("Invalid lock owner PID")
        if os.name == "nt":
            import csv
            import io
            output = subprocess.check_output(["tasklist", "/FI", "PID eq " + str(pid), "/FO", "CSV", "/NH"], text=True)
            if any(len(row) > 1 and row[1] == str(pid) for row in csv.reader(io.StringIO(output))):
                raise ValueError("Installer lock owner still exists")
        else:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            except PermissionError:
                raise ValueError("Cannot establish that lock owner exited")
            else:
                raise ValueError("Installer lock owner still exists")
        metadata.unlink()
        lock.rmdir()
    lock.mkdir()
    token = uuid.uuid4().hex
    atomic_write(lock / "owner.json", (json.dumps({"host": platform.node(), "pid": os.getpid(), "token": token}) + "\n").encode())
    return lock, token


def release_lock(lock, token):
    metadata = lock / "owner.json"
    if metadata.is_symlink() or {p.name for p in lock.iterdir()} != {"owner.json"}:
        raise ValueError("Installer lock changed; refusing removal")
    if json.loads(metadata.read_bytes()).get("token") != token:
        raise ValueError("Installer lock owner changed")
    metadata.unlink()
    lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aircraft", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--uninstall", action="store_true")
    action.add_argument("--recover", action="store_true", help="Roll back an interrupted standalone transaction")
    action.add_argument("--plan", action="store_true", help="Read-only installation plan (no aircraft writes)")
    args = parser.parse_args()
    manifest = verify_package()
    status = json.loads((PACKAGE / "PREPARATION_STATUS.json").read_text())
    if not args.uninstall and not args.recover and not args.plan and not status["installReady"]:
        raise ValueError("Development source preparation only: validation and installation are not released")
    absolute = args.aircraft.expanduser().absolute()
    standalone_guard.safe(Path(absolute.anchor), absolute.relative_to(absolute.anchor).as_posix())
    root = absolute.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Expected aircraft root directory")
    if args.plan:
        if state_file(root, "pending.json").exists():
            raise ValueError("Interrupted standalone transaction; recover first")
        changes = prepare(root, manifest, False)
        print(json.dumps({"installReady": status["installReady"], "changes": [r for r, _, _, _ in changes]}, indent=2))
        return 0
    ensure_offline()
    lock, token = acquire_lock(root, args.recover)
    try:
        if args.recover:
            recover_transaction(root)
            print("Recovery complete. Inspect the aircraft before installing again.")
            return 0
        if state_file(root, "pending.json").exists():
            raise ValueError("Interrupted standalone transaction; recover first")
        changes = prepare(root, manifest, args.uninstall)
        if changes or args.uninstall:
            transaction(root, changes, args.uninstall)
    finally:
        release_lock(lock, token)
    print("Removed." if args.uninstall else "Installed. Restart X-Plane completely.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("SFP27 stopped: " + str(error), file=sys.stderr)
        sys.exit(1)
