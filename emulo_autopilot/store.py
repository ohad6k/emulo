import contextlib
import json
import os
import re
import socket
import stat
import tempfile
import time
import uuid

from .contracts import (
    canonical_json,
    validate_candidate,
    validate_checkpoint,
    validate_decision,
    validate_inbox,
)


LOCK_SCHEMA = "emulo.autopilot-lock/v1"
LOCK_KEYS = {
    "schema_version",
    "operation_id",
    "operation",
    "pid",
    "hostname",
    "created_at",
}


class AutopilotStore:
    def __init__(self, emulo_home):
        self.emulo_home = os.path.realpath(os.path.abspath(emulo_home))
        self.root = os.path.join(self.emulo_home, "autopilot")

    @staticmethod
    def _assert_not_link(path):
        if not os.path.lexists(path):
            return
        info = os.lstat(path)
        is_reparse = bool(
            hasattr(info, "st_file_attributes")
            and info.st_file_attributes
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
        if stat.S_ISLNK(info.st_mode) or is_reparse:
            raise ValueError("Autopilot path cannot be a link or reparse point")

    def _assert_contained(self, path):
        try:
            if os.path.commonpath([self.root, path]) != self.root:
                raise ValueError("path escapes Autopilot root")
        except ValueError as exc:
            raise ValueError("path escapes Autopilot root") from exc

    def _assert_path_chain(self, path):
        self._assert_not_link(self.root)
        relative = os.path.relpath(path, self.root)
        probe = self.root
        if relative == ".":
            return
        for part in relative.split(os.sep):
            probe = os.path.join(probe, part)
            self._assert_not_link(probe)

    def _child(self, *parts):
        for part in parts:
            if (
                not isinstance(part, str)
                or not part
                or part in {".", ".."}
                or os.path.isabs(part)
                or os.sep in part
                or (os.altsep and os.altsep in part)
                or "/" in part
                or "\\" in part
            ):
                raise ValueError("unsafe Autopilot path component")
        candidate = os.path.abspath(os.path.join(self.root, *parts))
        self._assert_contained(candidate)
        self._assert_path_chain(candidate)
        return candidate

    def initialize(self):
        os.makedirs(self.emulo_home, mode=0o700, exist_ok=True)
        self._assert_not_link(self.root)
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        self._assert_not_link(self.root)
        for name in (
            "candidates",
            "checkpoints",
            "decisions",
            "inbox",
            "generations",
            "operations",
        ):
            path = self._child(name)
            os.makedirs(path, mode=0o700, exist_ok=True)
            self._assert_not_link(path)
        return self.root

    def atomic_write_json(self, path, value):
        self.initialize()
        path = os.path.abspath(path)
        self._assert_contained(path)
        self._assert_path_chain(path)
        parent = os.path.dirname(path)
        os.makedirs(parent, mode=0o700, exist_ok=True)
        self._assert_path_chain(parent)
        payload = (canonical_json(value) + "\n").encode("utf-8")
        descriptor, staged = tempfile.mkstemp(prefix=".staged-", dir=parent)
        try:
            os.chmod(staged, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, path)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if os.path.exists(staged):
                os.unlink(staged)
        return path

    @contextlib.contextmanager
    def lock(self, operation):
        self.initialize()
        if not isinstance(operation, str) or not re.fullmatch(
            r"[a-z][a-z0-9-]{0,63}", operation
        ):
            raise ValueError("operation is invalid")
        operation_id = uuid.uuid4().hex
        path = self._child("lock.json")
        record = {
            "schema_version": LOCK_SCHEMA,
            "operation_id": operation_id,
            "operation": operation,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise RuntimeError(
                "Autopilot is locked; inspect status before recover-lock"
            ) from exc
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write((canonical_json(record) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            yield record
        finally:
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as handle:
                    current = json.load(handle)
                if current.get("operation_id") == operation_id:
                    os.unlink(path)
            except (FileNotFoundError, UnicodeError, ValueError, json.JSONDecodeError):
                pass

    @staticmethod
    def _validate_lock(value):
        if not isinstance(value, dict) or set(value) != LOCK_KEYS:
            raise ValueError("lock record is invalid")
        if value["schema_version"] != LOCK_SCHEMA:
            raise ValueError("lock record is invalid")
        if not re.fullmatch(r"[a-f0-9]{32}", value["operation_id"] or ""):
            raise ValueError("lock record is invalid")
        if not isinstance(value["operation"], str) or not re.fullmatch(
            r"[a-z][a-z0-9-]{0,63}", value["operation"]
        ):
            raise ValueError("lock record is invalid")
        if isinstance(value["pid"], bool) or not isinstance(value["pid"], int):
            raise ValueError("lock record is invalid")
        if not isinstance(value["hostname"], str) or not value["hostname"]:
            raise ValueError("lock record is invalid")
        if not isinstance(value["created_at"], str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value["created_at"]
        ):
            raise ValueError("lock record is invalid")
        return value

    def recover_lock(self, expected_operation_id):
        if not isinstance(expected_operation_id, str) or not re.fullmatch(
            r"[a-f0-9]{32}", expected_operation_id
        ):
            raise ValueError("operation_id is invalid")
        path = self._child("lock.json")
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                value = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("lock record is invalid") from exc
        value = self._validate_lock(value)
        if value["operation_id"] != expected_operation_id:
            raise ValueError("operation_id does not match active lock")
        os.unlink(path)
        return value

    def put_candidate(self, candidate):
        candidate = validate_candidate(candidate)
        path = self._child("candidates", candidate["candidate_id"] + ".json")
        expected = (canonical_json(candidate) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing candidate bytes do not match identity")
            return path
        return self.atomic_write_json(path, candidate)

    def get_candidate(self, candidate_id):
        if not isinstance(candidate_id, str) or not re.fullmatch(
            r"cand_[a-f0-9]{20}", candidate_id
        ):
            raise ValueError("candidate_id is invalid")
        path = self._child("candidates", candidate_id + ".json")
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                value = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("candidate is missing or corrupt") from exc
        return validate_candidate(value)

    def append_decision(self, decision):
        decision = validate_decision(decision)
        self.get_candidate(decision["candidate_id"])
        path = self._child("decisions", decision["decision_id"] + ".json")
        expected = (canonical_json(decision) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing decision bytes do not match identity")
            return path
        return self.atomic_write_json(path, decision)

    def latest_decision(self, candidate_id):
        self.get_candidate(candidate_id)
        decisions = []
        root = self._child("decisions")
        if not os.path.isdir(root):
            return None
        for name in os.listdir(root):
            if not re.fullmatch(r"dec_[a-f0-9]{20}\.json", name):
                raise ValueError("unexpected decision file")
            path = self._child("decisions", name)
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as handle:
                    decision = validate_decision(json.load(handle))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError("decision is corrupt") from exc
            if decision["candidate_id"] == candidate_id:
                decisions.append(decision)
        if not decisions:
            return None
        return max(
            decisions,
            key=lambda item: (item["decided_at"], item["decision_id"]),
        )

    def checkpoint_path(self, path_hash):
        if not isinstance(path_hash, str) or not re.fullmatch(
            r"[a-f0-9]{64}", path_hash
        ):
            raise ValueError("path_hash is invalid")
        return self._child("checkpoints", path_hash + ".json")

    def get_checkpoint(self, path_hash):
        path = self.checkpoint_path(path_hash)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                return validate_checkpoint(json.load(handle))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("checkpoint is corrupt") from exc

    def put_checkpoint(self, checkpoint):
        checkpoint = validate_checkpoint(checkpoint)
        path = self.checkpoint_path(checkpoint["path_hash"])
        return self.atomic_write_json(path, checkpoint)

    def put_inbox(self, inbox):
        inbox = validate_inbox(inbox)
        path = self._child("inbox", inbox["inbox_id"] + ".json")
        expected = (canonical_json(inbox) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing inbox bytes do not match identity")
            return path
        return self.atomic_write_json(path, inbox)

    def list_inbox(self):
        self.initialize()
        values = []
        for name in os.listdir(self._child("inbox")):
            if not re.fullmatch(r"inbox_[a-f0-9]{20}\.json", name):
                raise ValueError("unexpected inbox file")
            path = self._child("inbox", name)
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as handle:
                    values.append(validate_inbox(json.load(handle)))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError("inbox is corrupt") from exc
        return sorted(values, key=lambda item: item["inbox_id"])
