<!-- Keep it short. See CONTRIBUTING.md for the hard rules. -->

**What changed**

<!-- One sentence. If you need "and" twice, split the PR. -->

**How I verified it**

```text
<the exact commands you ran and the tail of their output>
```

<!-- Anything you could not verify, say so here rather than leaving it implied. -->

**Privacy surface**

<!-- New discovery paths, new state under EMULO_HOME, more text sent to a model
provider, files written outside the output directory, or changed redaction?
Write "none" if nothing moved. -->

**Checklist**

- [ ] Full suite green: `python -m unittest discover -s tests`
- [ ] A test covers this change, and it fails without the change
- [ ] Minimal diff, no unrelated refactors or reformatting
- [ ] Every command in this PR and in any docs it touches was actually run as written
- [ ] Privacy surface unchanged, or the change is described above and `SECURITY.md` updated
- [ ] No profile contents, session text, real paths, or secrets in the diff or this description
- [ ] Docs updated if behavior, flags, or the boundary changed
