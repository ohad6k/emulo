import contextlib
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import time
import uuid

from .contracts import (
    DOMAINS,
    GENERATION_SCHEMA,
    HEAD_SCHEMA,
    canonical_json,
    generation_identity,
    validate_candidate,
    validate_checkpoint,
    validate_decision,
    validate_generation,
    validate_head,
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


def render_domain(domain, candidates):
    if domain not in DOMAINS:
        raise ValueError("generation domain is invalid")
    lines = [
        "# Emulo Autopilot overlay: " + domain,
        "",
        "Evidence-backed personal rules supplementing the active Emulo profile:",
        "",
    ]
    for candidate in sorted(candidates, key=lambda item: item["candidate_id"]):
        lines.append("- " + candidate["statement"])
    return "\n".join(lines).rstrip() + "\n"


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

    def get_lock(self):
        path = self._child("lock.json")
        if not os.path.lexists(path):
            return None
        try:
            self._assert_not_link(path)
            if not os.path.isfile(path):
                raise ValueError("lock record is invalid")
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                return self._validate_lock(json.load(handle))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("lock record is invalid") from exc

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

    def list_candidates(self):
        self.initialize()
        values = []
        root = self._child("candidates")
        for name in os.listdir(root):
            if not re.fullmatch(r"cand_[a-f0-9]{20}\.json", name):
                raise ValueError("unexpected candidate file")
            values.append(self.get_candidate(name[:-5]))
        return sorted(values, key=lambda item: item["candidate_id"])

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

    def get_head(self):
        path = self._child("head.json")
        if not os.path.exists(path):
            return None
        self._assert_not_link(path)
        if not os.path.isfile(path):
            raise ValueError("Autopilot head is corrupt")
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                return validate_head(json.load(handle))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Autopilot head is corrupt") from exc

    def get_generation(self, generation_id):
        if not isinstance(generation_id, str) or not re.fullmatch(
            r"gen_[a-f0-9]{20}", generation_id
        ):
            raise ValueError("generation_id is invalid")
        root = self._child("generations", generation_id)
        try:
            self._assert_path_chain(root)
            self._assert_not_link(root)
            if not os.path.isdir(root):
                raise ValueError("generation directory is missing")
            manifest_path = self._child(
                "generations", generation_id, "generation.json"
            )
            self._assert_not_link(manifest_path)
            if not os.path.isfile(manifest_path):
                raise ValueError("generation manifest is missing")
            with open(
                manifest_path, "r", encoding="utf-8", errors="strict"
            ) as handle:
                generation = validate_generation(json.load(handle))
            if generation["generation_id"] != generation_id:
                raise ValueError("generation identity mismatch")
            expected_files = {"generation.json"}
            for domain, metadata in generation["domains"].items():
                artifact_name = metadata["artifact"]
                expected_files.add(artifact_name)
                path = self._child("generations", generation_id, artifact_name)
                self._assert_not_link(path)
                if not os.path.isfile(path):
                    raise ValueError("generation artifact is missing")
                with open(path, "rb") as handle:
                    payload = handle.read()
                if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
                    raise ValueError("generation artifact hash mismatch")
                payload.decode("utf-8", errors="strict")
            if set(os.listdir(root)) != expected_files:
                raise ValueError("generation contains unexpected files")
            return generation
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Autopilot generation is corrupt") from exc

    def list_generations(self):
        self.initialize()
        values = []
        root = self._child("generations")
        for name in os.listdir(root):
            if not re.fullmatch(r"gen_[a-f0-9]{20}", name):
                raise ValueError("unexpected generation entry")
            values.append(self.get_generation(name))
        return sorted(values, key=lambda item: item["generation_id"])

    def read_domain(self, generation_id, domain):
        if domain not in DOMAINS:
            raise ValueError("generation domain is invalid")
        generation = self.get_generation(generation_id)
        metadata = generation["domains"].get(domain)
        if metadata is None:
            return None
        path = self._child("generations", generation_id, metadata["artifact"])
        try:
            self._assert_not_link(path)
            if not os.path.isfile(path):
                raise ValueError("generation artifact is missing")
            with open(path, "rb") as handle:
                payload = handle.read()
            if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
                raise ValueError("generation artifact hash mismatch")
            return payload.decode("utf-8", errors="strict")
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError("Autopilot generation is corrupt") from exc

    def read_active_domain(self, domain):
        head = self.get_head()
        if head is None:
            return None
        return self.read_domain(head["generation_id"], domain)

    @staticmethod
    def _write_file_bytes(path, payload):
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _write_generation(
        self,
        candidate_ids,
        parent_generation_id,
        operation,
        created_at,
    ):
        candidates = []
        for candidate_id in sorted(set(candidate_ids)):
            candidate = self.get_candidate(candidate_id)
            decision = self.latest_decision(candidate_id)
            if decision is None or decision["decision"] != "approve":
                raise ValueError(
                    "candidate requires a newest explicit approval decision"
                )
            if decision["policy_class"] not in {"safe", "review"}:
                raise ValueError("candidate policy class blocks activation")
            candidates.append(candidate)

        by_domain = {}
        for candidate in candidates:
            by_domain.setdefault(candidate["domain"], []).append(candidate)

        artifacts = {}
        domains = {}
        for domain in sorted(by_domain):
            payload = render_domain(domain, by_domain[domain]).encode("utf-8")
            artifact_name = domain + ".md"
            artifacts[artifact_name] = payload
            domains[domain] = {
                "artifact": artifact_name,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }

        generation = {
            "schema_version": GENERATION_SCHEMA,
            "generation_id": "",
            "parent_generation_id": parent_generation_id,
            "operation": operation,
            "candidate_ids": sorted(set(candidate_ids)),
            "domains": domains,
            "created_at": created_at,
        }
        generation["generation_id"] = generation_identity(generation)
        generation = validate_generation(generation)

        self.initialize()
        staged_name = ".staged-" + uuid.uuid4().hex
        staged = self._child("generations", staged_name)
        target = self._child("generations", generation["generation_id"])
        os.mkdir(staged, mode=0o700)
        try:
            for artifact_name, payload in artifacts.items():
                self._write_file_bytes(os.path.join(staged, artifact_name), payload)
            manifest = (canonical_json(generation) + "\n").encode("utf-8")
            self._write_file_bytes(os.path.join(staged, "generation.json"), manifest)

            if os.path.exists(target):
                existing = self.get_generation(generation["generation_id"])
                if existing != generation:
                    raise ValueError("existing generation does not match identity")
            else:
                os.replace(staged, target)

            verified = self.get_generation(generation["generation_id"])
            head = validate_head(
                {
                    "schema_version": HEAD_SCHEMA,
                    "generation_id": generation["generation_id"],
                }
            )
            self.atomic_write_json(self._child("head.json"), head)
            return verified
        finally:
            if os.path.isdir(staged):
                shutil.rmtree(staged)

    def activate(self, candidate_ids, created_at):
        if not isinstance(candidate_ids, list) or not candidate_ids:
            raise ValueError("candidate_ids must be a non-empty list")
        if any(
            not isinstance(candidate_id, str)
            or not re.fullmatch(r"cand_[a-f0-9]{20}", candidate_id)
            for candidate_id in candidate_ids
        ):
            raise ValueError("candidate_id is invalid")
        with self.lock("activate"):
            head = self.get_head()
            current = None
            active_ids = set()
            if head is not None:
                current = self.get_generation(head["generation_id"])
                active_ids.update(current["candidate_ids"])
            combined = sorted(active_ids.union(candidate_ids))
            if current is not None and combined == current["candidate_ids"]:
                return current
            return self._write_generation(
                combined,
                None if current is None else current["generation_id"],
                "activate",
                created_at,
            )

    def rollback(self, target_generation_id, created_at):
        if not isinstance(target_generation_id, str) or not re.fullmatch(
            r"gen_[a-f0-9]{20}", target_generation_id
        ):
            raise ValueError("target generation is not an ancestor")
        with self.lock("rollback"):
            head = self.get_head()
            if head is None:
                raise ValueError("target generation is not an ancestor")
            current = self.get_generation(head["generation_id"])
            parent_id = current["parent_generation_id"]
            visited = {current["generation_id"]}
            target = None
            while parent_id is not None:
                if parent_id in visited:
                    raise ValueError("Autopilot generation is corrupt")
                visited.add(parent_id)
                generation = self.get_generation(parent_id)
                if generation["generation_id"] == target_generation_id:
                    target = generation
                    break
                parent_id = generation["parent_generation_id"]
            if target is None:
                raise ValueError("target generation is not an ancestor")
            return self._write_generation(
                target["candidate_ids"],
                current["generation_id"],
                "rollback",
                created_at,
            )
