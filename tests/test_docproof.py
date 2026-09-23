"""Contract tests for docproof. Run: python -m unittest discover -s tests -v

Every test drives the real CLI against fixture markdown (or temp files)
and asserts observable exit codes, counts, and messages -- never
internals. bash-dependent tests skip honestly when no usable bash exists.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "docproof")
EXAMPLES = os.path.join(ROOT, "examples")


def run_cli(*args, env=None):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def usable_bash():
    """PATH bash first; fall back to a default Git-bash location (Windows
    boxes ship a WSL stub bash.exe on PATH that fails --version)."""
    candidates = [shutil.which("bash")]
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(os.path.join(program_files, "Git", "usr", "bin",
                                       "bash.exe"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            probe = subprocess.run([candidate, "--version"],
                                   capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return candidate
    return None


class DocproofContract(unittest.TestCase):
    def test_broken_directory_blocks_the_build(self):
        code, out, _ = run_cli(EXAMPLES, "--format", "json")
        self.assertEqual(code, 1, out)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["counts"]["fail"], 3)
        self.assertEqual({f["level"] for f in data["findings"] if f["level"] == "fail"},
                         {"fail"})
        for finding in data["findings"]:
            self.assertTrue(finding["file"].endswith(".md"))
            self.assertGreater(finding["line"], 0)

    def test_good_file_is_fully_verified(self):
        bash = usable_bash()
        args = [os.path.join(EXAMPLES, "good.md"), "--no-color"]
        if bash:
            args += ["--bash", bash]
        code, out, _ = run_cli(*args)
        self.assertEqual(code, 0, out)
        # parse counts from a JSON re-run
        code, out, _ = run_cli(os.path.join(EXAMPLES, "good.md"),
                               "--format", "json",
                               *(["--bash", bash] if bash else []))
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertGreaterEqual(data["counts"]["checked"], 3)  # py, json, js
        self.assertEqual(data["counts"]["fail"], 0)
        self.assertEqual(data["counts"]["unchecked"], 1)  # go
        self.assertGreaterEqual(data["counts"]["skipped"], 2)  # text + skip

    def test_console_output_lines_are_never_commands(self):
        bash = usable_bash()
        if not bash:
            self.skipTest("no usable bash on this machine")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("```console\n"
                         "$ echo fine\n"
                         "$( garbage that is not a command\n"
                         "```\n")
            path = handle.name
        try:
            code, out, _ = run_cli(path, "--bash", bash, "--format", "json")
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads(out)["counts"]["fail"], 0)
        finally:
            os.unlink(path)

    def test_console_command_with_bad_syntax_fails(self):
        bash = usable_bash()
        if not bash:
            self.skipTest("no usable bash on this machine")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("```console\n$ python (\n```\n")
            path = handle.name
        try:
            code, out, _ = run_cli(path, "--bash", bash, "--no-color")
            self.assertEqual(code, 1, out)
            self.assertIn("FAIL", out)
        finally:
            os.unlink(path)

    def test_missing_checker_warns_and_strict_blocks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("```javascript\nconst x = 1;\n```\n")
            path = handle.name
        empty_path = dict(os.environ, PATH="")
        try:
            code, out, _ = run_cli(path, "--format", "json", env=empty_path)
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertEqual(data["counts"]["warn"], 1)
            self.assertIn("not found", data["findings"][0]["message"])
            code, out, _ = run_cli(path, "--strict", "--format", "json",
                                   env=empty_path)
            self.assertEqual(code, 1, out)
        finally:
            os.unlink(path)

    def test_run_mode_catches_runtime_lies(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("```python\nraise SystemExit(3)\n```\n")
            path = handle.name
        try:
            code, out, _ = run_cli(path, "--format", "json")
            self.assertEqual(code, 0, out)  # parses fine, never executed
            code, out, _ = run_cli(path, "--run", "--no-color")
            self.assertEqual(code, 1, out)
            self.assertIn("exited 3", out)
        finally:
            os.unlink(path)

    def test_missing_path_is_usage_error(self):
        code, _, err = run_cli(os.path.join("nope", "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)

    def test_ignore_comment_opts_a_block_out(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("<!-- docproof-ignore -->\n"
                         "```python\ndef broken(:\n```\n")
            path = handle.name
        try:
            code, out, _ = run_cli(path, "--format", "json")
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertEqual(data["counts"]["skipped"], 1)
            self.assertEqual(data["counts"]["fail"], 0)
        finally:
            os.unlink(path)

    def test_unchecked_language_never_blocks_even_strict(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as handle:
            handle.write("```yaml\nkey: value\n```\n")
            path = handle.name
        try:
            code, out, _ = run_cli(path, "--strict", "--format", "json")
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertEqual(data["counts"]["unchecked"], 1)
            self.assertTrue(data["ok"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
