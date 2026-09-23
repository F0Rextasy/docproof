# Block inventory and decision order

`scripts/docproof` walks Markdown files, extracts fenced code blocks, and
assigns every block exactly one level. First matching rule wins:

| # | Rule | Level | Exit effect |
| --- | --- | --- | --- |
| 1 | `<!-- docproof-ignore -->` in the two lines above the fence | skipped | never |
| 2 | `skip` (or `off`) token in the info string (```python skip) | skipped | never |
| 3 | no language tag at all | skipped | never |
| 4 | language in text / txt / plain / diff / output / mermaid / irc / csv / ansi | skipped | never |
| 5 | console / shell-session / terminal: extract `$ `-prompted command lines (+ continuations), `bash -n` them; block with no commands | skipped | never |
| 6 | python (py, python3): `ast.parse`; with `--run`: execute via subprocess, timeout | ok / fail | fail blocks |
| 7 | json: `json.loads` | ok / fail | fail blocks |
| 8 | javascript (js, node, mjs, cjs): `node --check` (.mjs when top-level import/export present) | ok / fail / warn | fail blocks; warn under --strict |
| 9 | bash (sh, shell, zsh): `bash -n`; with `--run`: execute | ok / fail / warn | as above |
| 10 | anything else (go, rust, yaml, html, ...) | unchecked | never |

## Checker resolution and probe

`--bash PATH` / `--node PATH` override; otherwise `PATH` lookup. A found
binary is sanity-probed with `--version` (rc 0). A binary that exists but
fails the probe - e.g. `C:\Windows\system32\bash.exe` on a Windows box
without a WSL distribution - yields **warn "exists but is not usable --
not verified"**: a broken checker must never fabricate a verdict. Not
found at all: **warn "not found -- not verified"**. Warn blocks only
with `--strict`; it never becomes fail.

## Console sessions

Only `$ `-prompted lines are commands; output lines are ignored, so a
session may print anything (including pseudo-code and stray parens)
without failing. A `$ `-line is checked with `bash -n` - syntax only.
Console blocks are **never** executed, even under `--run`: real sessions
carry `pip install`, `rm`, and credentials-shaped strings.

## `--run` semantics

Off by default (parse-only). On: python blocks run with `sys.executable`,
bash blocks with the resolved bash, both in `cwd` of the invocation, each
under `--timeout` (default 10s). Nonzero exit or timeout -> fail with the
last stderr tail. javascript and json are parse-only always; console
never runs.

## Output

Text: one row per finding - `file:line  LEVEL  lang  message` - then the
summary line `docproof: ok -- N checked, ...` or `N snippet(s) broken --
the docs lie ...`. `--format json` for machines:

```json
{"ok": false, "counts": {"checked": 5, "fail": 1, "warn": 0,
 "unchecked": 1, "skipped": 2},
 "findings": [{"file": "README.md", "line": 12, "lang": "python",
               "level": "fail", "message": "python syntax error ..."}]}
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | no fail; no warn when `--strict` |
| 1 | at least one fail, or warn under `--strict` |
| 2 | usage: unreadable path, no markdown found, bad flags |

## Design invariants

- Verdicts are a pure function of (file bytes, checker availability) -
  same input, same answer, no sampling.
- Parse-check never touches the network; execution happens only under
  explicit `--run`.
- unchecked/skipped never block: docproof reports what it could not
  verify instead of pretending it did.
