---
name: docproof
description: Verifies that Markdown documentation still tells the truth -- parses every fenced code block with a deterministic per-language checker (python ast, json, node --check, bash -n, console sessions line-by-line). Use when docs may have drifted - before a release, after an API rename, in CI on every PR. Exit 1 means a snippet is broken; no model ever reads your docs.
license: MIT
compatibility: Requires Python 3.8+; node/bash only for their languages (absent checker = warning, never a guess). Works in Claude Code, Codex, Cursor, and any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# docproof

Documentation rots silently: the API got renamed, the snippet did not.
The next copy-paster finds out the hard way, and by then nobody knows
when the docs stopped being true. `docproof` turns "the README still
works" into a build status - deterministic parsing, milliseconds, no
model, no network.

## The one rule

You may not ship docs you have not verified:

```bash
python scripts/docproof README.md docs/ --strict
```

- **exit 1** - a snippet is broken: the docs lie, fix before merge.
- **exit 0** - every checkable snippet verified (warnings ok unless
  `--strict`).
- **exit 2** - usage error.

## Protocol

1. **Pick the surface** - README.md plus `docs/` (or any files/dirs; the
   walk picks up `*.md`).
2. **Verify, never trust**: parse-only by default; `--run` executes
   python/bash snippets with `--timeout` (default 10s) to catch code that
   parses but explodes.
3. **Act on the verdict**:

| Level | Meaning | Blocks? |
| --- | --- | --- |
| `fail` | snippet broken (syntax / bad json / runtime) | always |
| `warn` | checker binary missing or unusable -- unverified | `--strict` |
| `unchecked` | language has no checker (go, yaml, ...) | never |
| `skipped` | opted out (`skip`, `<!-- docproof-ignore -->`, non-code) | never |

4. **Report back** - counts, file:line of every broken snippet, the exit
   code:

```console
$ python scripts/docproof README.md --no-color
README.md:12  FAIL  python     python syntax error (line 1): ...

docproof: 1 snippet(s) broken -- the docs lie; fix before merge (5 checked, 2 unchecked, 1 skipped)
[exit 1]
```

## Hard bans

- Never execute a snippet without `--run` - docs may contain install or
  delete commands; console sessions are never executed at all.
- Never paste docs into a model to "check" them - parsing is a solved
  problem, and this skill exists to keep your docs on the machine.
- Never mark a broken snippet as skipped to go green - use the ignore
  comment only for genuinely non-runnable blocks, and say why in the doc.

## Reporting back

1. Counts: checked / fail / warn / unchecked / skipped.
2. Command and exit code.
3. Action: fixed the snippet, or declared it `skip`/ignore with a reason.
