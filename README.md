<p align="center"><img src="assets/ditto.png" width="360" alt="Ditto"></p>

<h1 align="center">Ditto</h1>

<p align="center"><b>Your AI agents act like they just met you. Ditto fixes that.</b></p>

<p align="center">
<img src="https://img.shields.io/github/stars/ohad6k/ditto?style=for-the-badge&color=3a3a3a&labelColor=141414&logo=github&logoColor=white&cacheSeconds=1800" alt="stars">
<a href="https://discord.gg/VNnMq2U5r"><img src="https://img.shields.io/badge/discord-join-3a3a3a?style=for-the-badge&labelColor=141414&logo=discord&logoColor=white" alt="discord"></a>
<img src="https://img.shields.io/badge/license-MIT-3a3a3a?style=for-the-badge&labelColor=141414" alt="MIT">
<img src="https://img.shields.io/badge/python-zero_deps-3a3a3a?style=for-the-badge&labelColor=141414&logo=python&logoColor=white" alt="Python, zero dependencies">
</p>

Your real coding-agent sessions already contain the rules you never wrote down: what “done” means, what you reject on sight, how you debug, how you design UI, and how you write when you are actually working.

Ditto mines selected evidence from those sessions into a private working profile. The native plugin can route work, design, and writing tasks through separate personal layers without making every task load everything.

## Quickstart

Install the cross-agent bootstrap:

```bash
npx skills add ohad6k/ditto@ditto
```

Then tell your agent:

```text
run ditto
```

That installs the bounded bootstrap and core working profile across supported skills.sh agents. It does not install native namespaced routing.

### Native Codex plugin

The native plugin adds `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`:

```bash
codex plugin marketplace add ohad6k/ditto --ref v0.2.0 --json
codex plugin add ditto@ditto --json
```

The plugin-install command itself scans no logs, writes no private profile state, and schedules zero mining model calls. Asking an agent to install, run, or update Ditto still consumes that host interaction plus its normal system and tool overhead.

Native Claude plugin packaging is not claimed in this release because it was not testable in the release environment. Claude Code remains supported through the selected skills.sh bootstrap and direct profile adapter.

## What happens when you run it

Ditto first prints a read-only plan:

```json
{
  "valid_sessions": 1656,
  "post_dedupe_source_tokens": 1950000,
  "selected_source_tokens": 100000,
  "cached_segments": 0,
  "planned_worker_calls": 4,
  "planned_reducer_calls": 1,
  "deep_mode": {"available": true, "automatic": false, "selected": false}
}
```

The bounded starter ladder is:

| Candidate | New source text | Maximum planned passes |
|---|---:|---:|
| 4 × 25K | 100K tokens | 4 workers + 1 reducer |
| 6 × 20K | 120K tokens | 6 workers + 1 reducer |
| 8 × 20K | 160K tokens | 8 workers + 1 reducer |

Ditto uses the smallest calibrated candidate that recovers the required profile. It never silently falls back to full history. Deep mode is explicit, separately planned, and requires approval.

On update, unchanged segment and evidence hashes are reused. An identical update plans zero additional Ditto mining passes. New or changed history plans only the affected bounded work plus one reducer.

These are `planned_worker_calls` and `planned_reducer_calls`, not provider billing events. Ditto cannot measure provider system prompts, tool traffic, orchestration overhead, or a percentage of a proprietary subscription allowance.

## What makes the result trustworthy

- Only real user-authored `.jsonl` messages are mined. `AGENTS.md`, `CLAUDE.md`, memory files, and typed self-descriptions are rejected as source evidence.
- Every worker covers work, design, and writing in one bounded JSON report.
- Quotes must be short, dated, verbatim receipts from known session IDs.
- Inferred rules require at least two distinct sessions and, when available, two source/time strata.
- One uncontradicted explicit instruction may survive as low-frequency evidence.
- Generic filler, invented quotes, unresolved contradictions, partial profile packs, and corrupt caches fail closed.

The native loaders are deliberately separate:

| Skill | Loads |
|---|---|
| `ditto:work` | Core working profile |
| `ditto:design` | Core + design taste |
| `ditto:write` | Core + writing voice |
| `ditto:mine` | Only explicit setup, update, or deepen requests |

## Privacy

Ditto's extractor, redaction, caches, and generated profiles stay local. Selected redacted text is processed by the model provider you choose. With a local model, the entire mining flow can remain local.

`ditto.py` itself is one stdlib-only file and makes no network calls. The skills.sh command downloads the selected bootstrap. Outside a repository checkout, that bootstrap downloads only `ditto.py` and `MINING_PROMPT.md` from the exact release tag after SHA-256 verification. Those downloads happen before log discovery and read no session data.

Redaction is best-effort and runs before selected text is written to Ditto caches. Inspect private output before sharing it. Share the card or one short trait, never your full profile or receipt appendix.

See [SECURITY.md](SECURITY.md) for the exact boundary.

## Raw one-file CLI

The legacy extractor remains available and backward compatible:

```bash
curl -O https://raw.githubusercontent.com/ohad6k/ditto/v0.2.0/ditto.py
python ditto.py --dry-run
python ditto.py --chunks 4 --out ditto-out
```

Manual adapters remain available:

```bash
python ditto.py --install you.md --target codex
python ditto.py --install you.md --target claude
python ditto.py --install you.md --target cursor --repo .
python ditto.py --install you.md --target agents --repo .
python ditto.py --install you.md --target gemini --repo .
```

## The card

```bash
python ditto.py --card
```

The card contains the archetype, top laws ranked by distinct supporting session receipts, coverage stats, and one sharp truth. Historical screenshots in this repository are pre-plugin examples and may display the old worker/report-count format.

<p align="center"><img src="assets/card.png" width="460" alt="Historical pre-plugin Ditto profile card example"></p>

## Support matrix

| Surface | Status in this release |
|---|---|
| Codex native plugin | Proven locally with four namespaced skills |
| Codex skills.sh bootstrap | Supported |
| Claude Code skills.sh/direct adapter | Supported |
| Claude native plugin | Not claimed; host unavailable during validation |
| Cursor / Gemini adapters | Supported through explicit install commands |

## Updating and notifications

Run `update ditto` to reuse stable caches and plan only changed work.

A GitHub star bookmarks the repository but does not subscribe you to releases. To receive release notifications, choose **Watch → Custom → Releases** on GitHub.

## Limits

- Ditto models how you work, design, and write. It does not make the underlying model smarter.
- Sparse or repetitive histories can leave design or writing inactive. Ditto reports the exact targeted-deepen instruction instead of inventing a persona.
- Provider token accounting remains outside Ditto's exact measurement.
- Benchmarks, leaderboard results, and proof videos are a separate later release.

See [ROADMAP.md](ROADMAP.md) for what is intentionally deferred.

## Community

- [Share what Ditto found](https://github.com/ohad6k/ditto/issues/1)
- [Discord](https://discord.gg/VNnMq2U5r)

## License

MIT. Made by [@ohad6k](https://github.com/ohad6k).
