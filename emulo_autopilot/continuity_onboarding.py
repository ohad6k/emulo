import base64
import json
import os
import stat
import tempfile
import re

from cryptography.exceptions import InvalidTag

from .contracts import canonical_json
from .continuity_crypto import (
    device_public_key,
    generate_device_key_pair,
    generate_master_key,
    generate_recovery_secret,
    read_private_material,
    unwrap_master_key_from_recovery,
    wrap_master_key_for_recovery,
    wrap_master_key_for_device,
    write_private_material,
)
from .store import AutopilotStore
from .continuity import (
    HttpsContinuityTransport,
    complete_pairing,
    validate_https_origin,
)


SETUP_SCHEMA = "emulo.continuity-setup/v1"
RECOVERY_SCHEMA = "emulo.continuity-recovery/v1"
RECOVERY_KIT_SCHEMA = "emulo.continuity-recovery-kit/v1"
PRIVATE_MATERIAL_FILENAME = "private-material.json"
RECOVERY_KIT_FILENAME = "recovery-kit.json"
DEVICE_CREDENTIAL_FILENAME = "device.json"
CREDENTIAL_SCHEMA = "emulo.continuity-device-credential/v1"
CONNECT_SCHEMA = "emulo.continuity-connect/v1"

_DEVICE = re.compile(r"^dev_[a-f0-9]{32}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_CLIENT_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,31}$")


def _encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _paths(home):
    store = AutopilotStore(home)
    store.initialize()
    continuity = store._child("continuity")
    return (
        os.path.join(continuity, PRIVATE_MATERIAL_FILENAME),
        os.path.join(continuity, RECOVERY_KIT_FILENAME),
    )


def _credential_path(home):
    store = AutopilotStore(home)
    store.initialize()
    return os.path.join(store._child("continuity"), DEVICE_CREDENTIAL_FILENAME)


def _reserve_new(path, existing_message):
    if os.path.lexists(path):
        raise ValueError(existing_message)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(existing_message) from exc
    os.close(descriptor)
    os.chmod(path, 0o600)


def _write_reserved_json(path, value):
    parent = os.path.dirname(path)
    descriptor, staged = tempfile.mkstemp(prefix=".recovery-kit-", dir=parent)
    try:
        os.chmod(staged, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write((canonical_json(value) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
        os.chmod(path, 0o600)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if os.path.exists(staged):
            os.unlink(staged)


def _write_new_private_material(path, private_key, master_key):
    _reserve_new(path, "continuity is already initialized")
    try:
        write_private_material(path, private_key, master_key)
    except Exception:
        if os.path.isfile(path) and not os.path.islink(path):
            os.unlink(path)
        raise


def _read_recovery_kit(path):
    path = os.path.abspath(os.fspath(path))
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError("recovery kit path is invalid")
    if os.name != "nt" and stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        raise ValueError("recovery kit permissions are too broad")
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("recovery kit is invalid") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "wrapped_master_key"}
        or value.get("schema_version") != RECOVERY_KIT_SCHEMA
        or not isinstance(value.get("wrapped_master_key"), dict)
    ):
        raise ValueError("recovery kit is invalid")
    return value


def _read_private_json(path, label):
    path = os.path.abspath(os.fspath(path))
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError(label + " path is invalid")
    if os.name != "nt" and stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        raise ValueError(label + " permissions are too broad")
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(label + " is invalid") from exc


def initialize_continuity(home):
    private_path, kit_path = _paths(home)
    if os.path.lexists(private_path) or os.path.lexists(kit_path):
        raise ValueError("continuity is already initialized")
    private_key, public_key = generate_device_key_pair()
    master_key = generate_master_key()
    recovery_secret = generate_recovery_secret()
    kit = {
        "schema_version": RECOVERY_KIT_SCHEMA,
        "wrapped_master_key": wrap_master_key_for_recovery(
            master_key,
            recovery_secret,
        ),
    }
    _reserve_new(kit_path, "continuity is already initialized")
    try:
        _write_reserved_json(kit_path, kit)
        _write_new_private_material(private_path, private_key, master_key)
    except Exception:
        if os.path.isfile(kit_path) and not os.path.islink(kit_path):
            os.unlink(kit_path)
        raise
    return {
        "schema_version": SETUP_SCHEMA,
        "recovery_secret": recovery_secret,
        "private_material_path": private_path,
        "recovery_kit_path": kit_path,
        "device_public_key": _encode(public_key),
    }


def recover_continuity(home, recovery_kit_path, recovery_secret):
    private_path, _kit_path = _paths(home)
    if os.path.lexists(private_path):
        raise ValueError("continuity is already initialized")
    kit = _read_recovery_kit(recovery_kit_path)
    try:
        master_key = unwrap_master_key_from_recovery(
            kit["wrapped_master_key"],
            recovery_secret,
        )
    except (InvalidTag, ValueError) as exc:
        raise ValueError("recovery secret or kit is invalid") from exc
    private_key, public_key = generate_device_key_pair()
    _write_new_private_material(private_path, private_key, master_key)
    return {
        "schema_version": RECOVERY_SCHEMA,
        "private_material_path": private_path,
        "device_public_key": _encode(public_key),
    }


def load_private_material(home):
    private_path, _kit_path = _paths(home)
    return read_private_material(private_path)


def connect_continuity(
    home,
    server,
    pairing_code,
    label,
    client_version,
    pairer=None,
):
    credential_path = _credential_path(home)
    if os.path.lexists(credential_path):
        raise ValueError("continuity device is already connected")
    if not isinstance(pairing_code, str) or not _TOKEN.fullmatch(pairing_code):
        raise ValueError("pairing code is invalid")
    if (
        not isinstance(label, str)
        or not 1 <= len(label) <= 64
        or re.search(r"[\x00-\x1f\x7f]", label)
    ):
        raise ValueError("device label is invalid")
    if (
        not isinstance(client_version, str)
        or not _CLIENT_VERSION.fullmatch(client_version)
    ):
        raise ValueError("client version is invalid")
    server = validate_https_origin(server)
    if pairer is None:
        pairer = complete_pairing
    private_key, master_key = load_private_material(home)
    public_key = device_public_key(private_key)
    wrapped = wrap_master_key_for_device(master_key, public_key)
    paired = pairer(
        server,
        {
            "pairingCode": pairing_code,
            "label": label,
            "keyAgreementPublicKey": _encode(public_key),
            "wrappedMasterKey": wrapped,
            "clientVersion": client_version,
        },
    )
    if (
        not isinstance(paired, dict)
        or set(paired) != {"deviceId", "deviceToken"}
        or not isinstance(paired.get("deviceId"), str)
        or not _DEVICE.fullmatch(paired["deviceId"])
        or not isinstance(paired.get("deviceToken"), str)
        or not _TOKEN.fullmatch(paired["deviceToken"])
    ):
        raise ValueError("pairing response is invalid")
    credential = {
        "schema_version": CREDENTIAL_SCHEMA,
        "server": server,
        "device_id": paired["deviceId"],
        "device_token": paired["deviceToken"],
    }
    _reserve_new(credential_path, "continuity device is already connected")
    try:
        _write_reserved_json(credential_path, credential)
    except Exception:
        if os.path.isfile(credential_path) and not os.path.islink(credential_path):
            os.unlink(credential_path)
        raise
    return {
        "schema_version": CONNECT_SCHEMA,
        "server": credential["server"],
        "device_id": credential["device_id"],
    }


def read_device_credential(home):
    value = _read_private_json(_credential_path(home), "device credential")
    if (
        not isinstance(value, dict)
        or set(value)
        != {"schema_version", "server", "device_id", "device_token"}
        or value.get("schema_version") != CREDENTIAL_SCHEMA
        or not isinstance(value.get("server"), str)
        or not isinstance(value.get("device_id"), str)
        or not _DEVICE.fullmatch(value["device_id"])
        or not isinstance(value.get("device_token"), str)
        or not _TOKEN.fullmatch(value["device_token"])
    ):
        raise ValueError("device credential is invalid")
    validate_https_origin(value["server"])
    return value


def continuity_status(home):
    store = AutopilotStore(home)
    store.initialize()
    private_path = store._child("continuity", PRIVATE_MATERIAL_FILENAME)
    credential_path = store._child("continuity", DEVICE_CREDENTIAL_FILENAME)
    initialized = os.path.isfile(private_path) and not os.path.islink(private_path)
    connected = os.path.isfile(credential_path) and not os.path.islink(credential_path)
    credential = read_device_credential(home) if connected else None
    head = store.get_head()
    return {
        "schema_version": "emulo.continuity-status/v1",
        "initialized": initialized,
        "connected": connected,
        "server": None if credential is None else credential["server"],
        "device_id": None if credential is None else credential["device_id"],
        "active_generation_id": None if head is None else head["generation_id"],
        "pending_count": len(store.list_continuity_pending()),
    }


def load_connected_continuity(home):
    _private_key, master_key = load_private_material(home)
    credential = read_device_credential(home)
    return (
        master_key,
        credential["device_id"],
        HttpsContinuityTransport(
            credential["server"],
            credential["device_token"],
        ),
    )
