import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def build_db(root):
    db_path = Path(root) / "opencode.db"
    con = sqlite3.connect(db_path)
    con.execute("create table message (id text, session_id text, time_created integer, time_updated integer, data text)")
    con.execute("create table part (id text, message_id text, session_id text, time_created integer, time_updated integer, data text)")

    def add(msg_id, session_id, role, parts, ts=1783963834101):
        con.execute("insert into message values (?,?,?,?,?)",
                    (msg_id, session_id, ts, ts, json.dumps({"role": role, "time": {"created": ts}})))
        for i, part in enumerate(parts):
            con.execute("insert into part values (?,?,?,?,?,?)",
                        (f"{msg_id}_p{i}", msg_id, session_id, ts + i, ts + i, json.dumps(part)))

    add("m1", "ses_a", "user", [{"type": "text", "text": "done means live proof"}])
    add("m2", "ses_a", "assistant", [
        {"type": "reasoning", "text": "model thinking"},
        {"type": "text", "text": "assistant reply text"},
    ])
    add("m3", "ses_b", "user", [
        {"type": "text", "text": "injected", "synthetic": True},
        {"type": "text", "text": "ship the fix tonight"},
    ])
    con.commit()
    con.close()
    return str(db_path)


class OpencodeDbTest(unittest.TestCase):
    def test_discovers_one_entry_per_session_and_mines_only_typed_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = build_db(tmp)
            entries = ditto.discover_files([tmp])
            self.assertEqual(2, len(entries))
            self.assertTrue(all(ditto.OPENCODE_DB_SESSION_SEP in e for e in entries))

            texts = []
            for entry in entries:
                texts += [t for _, t in ditto.user_messages(entry)]
            self.assertEqual(["done means live proof", "ship the fix tonight"], sorted(texts))

            self.assertEqual("opencode", ditto.source_kind(db_path))

    def test_missing_or_empty_root_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], ditto.discover_files([tmp]))
            self.assertEqual([], ditto.discover_files([str(Path(tmp) / "nope")]))


class OpencodeLegacyStorageTest(unittest.TestCase):
    def test_legacy_json_layout_mines_user_text_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "opencode"
            storage = root / "storage"
            session_file = storage / "session" / "proj1" / "ses_x.json"
            session_file.parent.mkdir(parents=True)
            session_file.write_text(json.dumps({"id": "ses_x", "title": "t"}), encoding="utf-8")

            msg_dir = storage / "message" / "ses_x"
            msg_dir.mkdir(parents=True)
            (msg_dir / "msg_u.json").write_text(json.dumps(
                {"id": "msg_u", "role": "user", "time": {"created": 1783963834101}}), encoding="utf-8")
            (msg_dir / "msg_a.json").write_text(json.dumps(
                {"id": "msg_a", "role": "assistant", "time": {"created": 1783963834200}}), encoding="utf-8")

            for mid, part in (
                ("msg_u", {"type": "text", "text": "never fake data"}),
                ("msg_u", {"type": "file", "text": "attachment"}),
                ("msg_a", {"type": "text", "text": "assistant text"}),
            ):
                pdir = storage / "part" / mid
                pdir.mkdir(parents=True, exist_ok=True)
                n = len(list(pdir.glob("*.json")))
                (pdir / f"prt_{n}.json").write_text(json.dumps(part), encoding="utf-8")

            entries = ditto.discover_files([str(root)])
            self.assertEqual([str(session_file)], entries)
            mined = ditto.user_messages(entries[0])
            self.assertEqual([("2026-07-13", "never fake data")], mined)

    def test_legacy_layout_mines_under_any_path_root_name(self):
        # an exported legacy store passed via --path, root not named opencode
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "backup-export"
            storage = root / "storage"
            session_file = storage / "session" / "proj1" / "ses_y.json"
            session_file.parent.mkdir(parents=True)
            session_file.write_text(json.dumps({"id": "ses_y"}), encoding="utf-8")
            msg_dir = storage / "message" / "ses_y"
            msg_dir.mkdir(parents=True)
            (msg_dir / "msg_u.json").write_text(json.dumps(
                {"id": "msg_u", "role": "user", "time": {"created": 1783963834101}}), encoding="utf-8")
            pdir = storage / "part" / "msg_u"
            pdir.mkdir(parents=True)
            (pdir / "prt_0.json").write_text(
                json.dumps({"type": "text", "text": "one step, short"}), encoding="utf-8")

            entries = ditto.discover_files([str(root)])
            self.assertEqual([str(session_file)], entries)
            self.assertEqual([("2026-07-13", "one step, short")],
                             ditto.user_messages(entries[0]))


if __name__ == "__main__":
    unittest.main()
