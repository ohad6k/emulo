"""Command-line interface for local Ditto Proof v1 artifact operations."""

import argparse
import json
import sys
from pathlib import Path

from proof.canonical import canonical_bytes, sha256_bytes
from proof.manifest import build_system_freeze
from proof.runner import execute_cell, prepare_cell
from proof.schema import validate_manifest


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _find_cell(manifest, cell_id):
    matches = [
        cell
        for pair in manifest["pairs"]
        for cell in pair["cells"]
        if cell["cell_id"] == cell_id
    ]
    if len(matches) != 1:
        raise ValueError("cell ID is not frozen exactly once")
    return matches[0]


def _parser():
    parser = argparse.ArgumentParser(prog="python -m proof.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--manifest", required=True)

    freeze_system = commands.add_parser("freeze-system")
    freeze_system.add_argument("--host", choices=("codex", "claude"), required=True)
    freeze_system.add_argument("--menu-label", required=True)
    freeze_system.add_argument("--model-id")
    freeze_system.add_argument("--host-version", required=True)
    freeze_system.add_argument("--run-argv", action="append", required=True)
    freeze_system.add_argument("--ditto-install-argv", action="append", required=True)
    freeze_system.add_argument("--screenshot-sha256", required=True)
    freeze_system.add_argument("--tool-policy-sha256", required=True)
    freeze_system.add_argument("--permission-policy-sha256", required=True)
    freeze_system.add_argument("--quota-snapshot", required=True)
    freeze_system.add_argument("--expected-cost", required=True)

    for name in ("prepare-cell", "execute-cell"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", required=True)
        command.add_argument("--cell-id", required=True)
        command.add_argument("--run-root", required=True)
        if name == "execute-cell":
            command.add_argument("--execute", action="store_true")
            command.add_argument("--approval", required=True)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--record", required=True)
    evaluate.add_argument("--policy", required=True)

    package = commands.add_parser("package")
    package.add_argument("--manifest", required=True)
    package.add_argument("--records", required=True)
    package.add_argument("--destination", required=True)
    package.add_argument("--ship-approval", required=True)
    package.add_argument("--evidence-root", required=True)
    package.add_argument("--privacy-inputs", required=True)
    package.add_argument("--manual-review-approved", action="store_true")
    return parser


def _dispatch(args):
    if args.command == "validate":
        manifest = validate_manifest(_read_json(args.manifest))
        return {
            "valid": True,
            "manifest_sha256": sha256_bytes(canonical_bytes(manifest)),
            "pairs": len(manifest["pairs"]),
            "cells": sum(len(pair["cells"]) for pair in manifest["pairs"]),
        }
    if args.command == "freeze-system":
        return build_system_freeze(
            args.host,
            args.menu_label,
            args.model_id,
            args.host_version,
            args.run_argv,
            args.ditto_install_argv,
            args.screenshot_sha256,
            args.tool_policy_sha256,
            args.permission_policy_sha256,
            args.quota_snapshot,
            args.expected_cost,
        )

    if args.command in ("prepare-cell", "execute-cell"):
        manifest = validate_manifest(_read_json(args.manifest))
        cell = _find_cell(manifest, args.cell_id)
        if args.command == "prepare-cell":
            prepared = prepare_cell(manifest, cell, args.run_root)
            return {
                "cell_id": args.cell_id,
                "fixture_sha256": prepared.fixture_sha256,
                "home_audit_sha256": prepared.home_audit_sha256,
                "prepared": True,
            }
        if not args.execute:
            raise PermissionError("execute-cell requires --execute and exact approval")
        prepared, completed, installed_hash = execute_cell(
            manifest,
            cell,
            args.run_root,
            execute=True,
            approval=args.approval,
        )
        return {
            "cell_id": args.cell_id,
            "fixture_sha256": prepared.fixture_sha256,
            "home_audit_sha256": prepared.home_audit_sha256,
            "installed_context_sha256": installed_hash,
            "exit_code": completed.returncode,
            "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
            "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
        }

    if args.command == "evaluate":
        from proof.evaluate import evaluate_objective

        return evaluate_objective(_read_json(args.record), _read_json(args.policy))
    if args.command == "package":
        from proof.privacy import scan_public_tree
        from proof.publish import build_publication, render_index
        from proof.store import EvidenceStore

        if not args.manual_review_approved:
            raise PermissionError("package requires explicit manual privacy review")
        privacy = _read_json(args.privacy_inputs)
        if set(privacy) != {"canaries", "private_roots"}:
            raise ValueError("privacy inputs require canaries and private_roots")
        if not isinstance(privacy["canaries"], dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in privacy["canaries"].items()
        ):
            raise ValueError("privacy canaries must be a string map")
        if (
            not isinstance(privacy["private_roots"], list)
            or not privacy["private_roots"]
            or not all(
            isinstance(value, str) and value for value in privacy["private_roots"]
            )
        ):
            raise ValueError("privacy private_roots must be a nonempty string list")
        evidence_root = Path(args.evidence_root).resolve()
        resolved_private_roots = [
            Path(value).resolve() for value in privacy["private_roots"]
        ]
        if not any(
            evidence_root == root or root in evidence_root.parents
            for root in resolved_private_roots
        ):
            raise ValueError("privacy private_roots must include the evidence root")
        manifest = validate_manifest(_read_json(args.manifest))
        store = EvidenceStore(
            args.evidence_root,
            {
                cell["cell_id"]: cell
                for pair in manifest["pairs"]
                for cell in pair["cells"]
            },
        )
        publication = build_publication(
            manifest,
            _read_json(args.records),
            args.ship_approval,
            evidence_store=store,
        )
        render_index(
            publication,
            args.destination,
            canaries=privacy["canaries"],
            private_roots=privacy["private_roots"],
        )
        scan_public_tree(
            args.destination,
            canaries=privacy["canaries"],
            private_roots=privacy["private_roots"],
            manual_review_approved=True,
        )
        return {
            "packaged": True,
            "evidence_digest": publication["evidence_digest"],
        }
    raise AssertionError("unhandled command")


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        result = _dispatch(args)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "message": str(exc)},
                sort_keys=True,
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
