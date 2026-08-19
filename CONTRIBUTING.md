# Contributing to Emulo

Emulo reads people's private AI coding-session logs. Every rule below comes from that.

## Setup

The core is one stdlib-only file, `emulo.py`. Nothing to build, no runtime dependency to install.

```bash
git clone https://github.com/ohad6k/emulo
cd emulo
python -m unittest discover -s tests
```

`pyproject.toml` declares `requires-python = ">=3.8"`. CI runs 3.12 (`.github/workflows/tests.yml`). This guide was written against a local run on Python 3.11.4: 396 tests, OK, 3 skipped (Windows symlink tests that need a privilege Windows does not grant by default). Those three run on Linux and macOS.

CI installs the one optional pin before the suite, so do the same if you touch encrypted continuity:

```bash
python -m pip install -r requirements.lock
```

That pin is `cryptography`, used only by the optional `pro` extra. The mining core never imports it.

Run the CLI straight from a checkout:

```bash
python emulo.py --help
python emulo.py --dry-run --path <folder of .jsonl logs>
python emulo.py plugin --help
python emulo.py mcp
```

`--dry-run` prints counts and output paths and writes nothing. While developing, point `--path` at a scratch folder of fixture logs instead of your real history. With no logs found, the run exits non-zero and writes nothing, which is the intended behavior, not a bug.

## Layout

| Path | What's in it |
|---|---|
| `emulo.py` | The whole tool: discovery, extraction, redaction, the read-only plan, `plugin` subcommands, the `mcp` server, the card, and the install adapters. Stdlib only, no network calls. |
| `emulo_autopilot/` | Autopilot package: policy, sessions, store, encrypted continuity. |
| `proof/` | Emulo Proof v1 methodology code: schema, runner, evaluate, publish. |
| `skills/` | The five native plugin skills: `mine`, `work`, `design`, `write`, `video`. |
| `.agents/` | The skills.sh bootstrap and its marketplace entry. |
| `.claude-plugin/`, `.codex-plugin/`, `.github/plugin/` | Host plugin manifests. `tests/test_plugin_manifests.py` keeps them honest. |
| `compat/` | Compatibility shims for the old `ditto` name. Keep them working. |
| `cloud/worker/` | The Cloudflare Worker behind Emulo Pro. |
| `site/` | The public site. |
| `docs/`, `MINING_PROMPT.md` | Docs and the mining prompt handed to agents. |
| `tests/` | Plain `unittest`. No test-runner dependency. |

## Hard rules

**Verify before you claim it works.** A code edit is not evidence. Run the thing, read the output, then say what happened. If you could not run it, say that instead of implying you did.

**Never publish a command you have not run.** Every command in a README, a doc, an issue reply, or a PR description has to have been executed as written on a real machine. If it only works on one OS, say which.

**Fix the one thing.** Minimal diffs. No drive-by refactors, no reformatting a file you opened to change one line, no renaming things that were not in your way. A PR that rewrites code that was not the problem gets rejected.

**Do not widen the privacy surface quietly.** New discovery paths, new fields written to `EMULO_HOME`, new text sent to a model provider, new files written outside the output directory, or anything loosening redaction: call it out explicitly in the PR and add a test. `SECURITY.md` is the boundary. If your change moves it, update `SECURITY.md` in the same PR.

**Fail closed.** Empty or malformed input writes nothing. Corrupt caches are quarantined, not trusted. Hash checks happen before reuse. Keep it that way.

**Never commit private data.** Session logs, mined output, `you.md` and its lens files, the receipt appendix, and Emulo caches are gitignored on purpose. Do not add exceptions and do not paste them into an issue, a PR, or a test fixture. Test fixtures must be synthetic.

## What a good PR looks like

- One change, described in a sentence. If you need "and" twice, split it.
- Tests: a test that fails before your change and passes after. Same `unittest` style as the rest of `tests/`.
- The full suite green: `python -m unittest discover -s tests`. Paste the tail of the output in the PR.
- Docs updated in the same PR when behavior, flags, or the privacy boundary changed.
- The PR checklist filled in honestly, including the "could not verify" cases.

Open an issue before a large change so nobody builds the wrong thing twice.

## Reporting bugs

Use the issue templates. They exist because a bug report about a log miner is the easiest place in this project to leak your own data by accident. Give the Emulo version, the OS, the command, and the error text with paths and log contents redacted. Never attach a profile, a session transcript, or a chunk of your corpus.

For a security issue, do not open a public issue with reproduction details. Report it privately to the maintainer first, through GitHub's private vulnerability reporting on the repository if it is enabled.

## License

MIT. By contributing you agree your contribution ships under the same license.
