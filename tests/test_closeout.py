"""Automatic closeout (ADR-094): readiness decisions, open-loop mirroring and the validator checks.

The commands that call git and gh are exercised by the owner's own closeout runs; these tests cover
every decision they make from the data those calls return.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import closeout  # noqa: E402

SPEC = importlib.util.spec_from_file_location("validate_project_closeout", ROOT / "scripts" / "validate_project.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

CODEX = {"login": "chatgpt-codex-connector[bot]"}
HEAD = "9967655070453697de2933ac15d710470ee9c2b5"


def review(sha, at):
    return {"user": CODEX, "commit_id": sha, "submitted_at": at}


def summary(sha, status="Completed"):
    return {"user": CODEX, "updated_at": "2026-10-08T05:09:41Z",
            "body": f"| 📝 **Code Review** | ✅ **{status}** <relative-time>t</relative-time> | `{sha}` | Manual request |"}


class ReadinessTests(unittest.TestCase):
    def test_review_on_the_exact_head_with_no_open_thread_is_ready(self):
        signals = closeout.review_signals([review("c97ce9b8ef", "1"), review(HEAD, "2")], [])
        self.assertEqual(closeout.assess(HEAD, signals, 0), [])

    def test_a_clean_round_counts_from_the_summary_comment(self):
        # A Codex round with no findings posts no review, only a Completed summary row.
        signals = closeout.review_signals([], [summary(HEAD[:7])])
        self.assertEqual(signals, [HEAD[:7]])
        self.assertEqual(closeout.assess(HEAD, signals, 0), [])
        self.assertEqual(closeout.review_signals([], [summary(HEAD[:7], status="Running")]), [])

    def test_a_human_comment_is_not_a_review_signal(self):
        human = {"user": {"login": "henslewm"}, "body": f"**Reviewed commit:** `{HEAD[:7]}`"}
        self.assertEqual(closeout.review_signals([], [human]), [])

    def test_stale_review_asks_for_the_next_round(self):
        reasons = closeout.assess(HEAD, ["c97ce9b", "43fa5d9"], 0)
        self.assertEqual(len(reasons), 1)
        self.assertIn("round 3 of 4", reasons[0])

    def test_pr_110_history_reports_the_cap_not_another_round(self):
        # PR #110: five rounds, the final head 0fb220d unreviewed.
        signals = ["a1b2c3d", "b2c3d4e", "c3d4e5f", "7e3b36f", "1fa6e78"]
        reasons = closeout.assess("0fb220d" + "0" * 33, signals, 0)
        self.assertIn("review cap exceeded", reasons[0])

    def test_cap_is_enforced_even_when_the_head_was_reviewed(self):
        # PR #116 Codex round 1 P1: a fifth round on the head still goes to the maintainer.
        self.assertIn("review cap exceeded", closeout.assess(HEAD, [HEAD], 0, rounds=5)[0])
        self.assertEqual(closeout.assess(HEAD, [HEAD], 0, rounds=4), [])

    def test_repeat_rounds_on_one_commit_each_count_and_the_summary_does_not(self):
        reviews = [review(HEAD, "1"), review(HEAD, "2")]
        clean = {"user": CODEX, "body": f"Codex Review: Didn't find any major issues.\n\n**Reviewed commit:** `{HEAD[:10]}`"}
        self.assertEqual(closeout.review_rounds(reviews, [clean, summary(HEAD[:7])]), 3)

    def test_more_threads_and_requested_changes_block(self):
        reasons = closeout.assess(HEAD, [HEAD], 0, rounds=1, more_threads=True,
                                  changes=closeout.changes_requested([{**review(HEAD, "1"), "state": "CHANGES_REQUESTED"}], HEAD))
        self.assertEqual(len(reasons), 2)
        self.assertIn("more than 100", reasons[0])
        self.assertIn("requests changes", reasons[1])
        self.assertFalse(closeout.changes_requested([{**review("c97ce9b8ef", "1"), "state": "CHANGES_REQUESTED"}], HEAD))

    def test_unresolved_threads_block_even_a_reviewed_head(self):
        reasons = closeout.assess(HEAD, [HEAD], 2)
        self.assertEqual(len(reasons), 1)
        self.assertIn("2 unresolved review thread", reasons[0])


class MergeTests(unittest.TestCase):
    """PR #116 Codex round 2: a queued merge never deletes the branch."""

    def merge_with(self, state):
        calls = []
        args = type("Args", (), {"pr": "116"})()
        view = {"number": 116, "headRefName": "claude/auto-closeout", "baseRefName": "main", "headRefOid": HEAD}
        originals = (closeout.readiness, closeout.run, closeout.gh_json)
        closeout.readiness = lambda pr: (view, [])
        closeout.run = lambda cmd, check=True, timeout=0: calls.append(cmd) or ""
        closeout.gh_json = lambda args_: state
        try:
            return closeout.cmd_merge(args), calls
        finally:
            closeout.readiness, closeout.run, closeout.gh_json = originals

    def test_queued_merge_keeps_the_branch(self):
        code, calls = self.merge_with({"state": "OPEN", "mergeCommit": None})
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("--delete-branch", calls[0])
        self.assertFalse(any("--delete" in part for cmd in calls for part in cmd))

    def test_merged_state_is_required_before_cleanup(self):
        self.assertIsNone(closeout.merged_commit({"state": "OPEN", "mergeCommit": {"oid": HEAD}}))
        self.assertEqual(closeout.merged_commit({"state": "MERGED", "mergeCommit": {"oid": HEAD}}), HEAD)


LOOPS = """# Open Loops

## Open

<!-- issue-mirror-from: OL-041 -->

| ID | Priority | Open item | Owner | Next action | Dependency | Due | Status |
|---|---|---|---|---|---|---|---|
| OL-040 | Medium | Older loop | Owner | Decide | None | Not set | Open |
| OL-041 | High | New loop | Owner | Fix | None | Not set | Open |

## Closed

| ID | Priority | Open item | Owner | Next action | Dependency | Due | Status |
|---|---|---|---|---|---|---|---|
| OL-001 | High | Done | Owner | None | None | Complete | Closed |
"""
URL = "https://github.com/henslewm/universal-ai-project-template/issues/130"


class LoopMirrorTests(unittest.TestCase):
    def test_link_then_close_moves_the_row_and_keeps_the_link(self):
        linked = closeout.link_issue(LOOPS, "OL-041", 130, URL)
        self.assertEqual(closeout.mirrored_rows(linked), [("OL-041", "Open", 130)])
        with self.assertRaisesRegex(closeout.Refused, "already mirrors"):
            closeout.link_issue(linked, "OL-041", 131, URL)
        closed = closeout.close_loop(linked, "OL-041", "Closed 2026-10-08: issue #130 closed")
        self.assertEqual(closeout.mirrored_rows(closed), [("OL-041", "Closed", 130)])
        last_row = [line for line in closed.split("\n") if line.startswith("| OL-")][-1]
        self.assertTrue(last_row.startswith("| OL-041 |"))

    def test_closing_creates_the_closed_section_a_generated_project_lacks(self):
        # PR #116 Codex round 1 P2: generated OPEN_LOOPS.md files start with only an Open table.
        open_only = LOOPS.split("## Closed")[0].rstrip("\n") + "\n"
        closed = closeout.close_loop(closeout.link_issue(open_only, "OL-041", 130, URL), "OL-041", "Closed")
        self.assertEqual(closeout.mirrored_rows(closed), [("OL-041", "Closed", 130)])

    def test_unknown_loop_is_refused(self):
        with self.assertRaisesRegex(closeout.Refused, "no row OL-099"):
            closeout.link_issue(LOOPS, "OL-099", 1, URL)


DENIES = list(VALIDATOR.KEPT_DENIES)
MASTER = "# Master\n\n## Automatic closeout (ADR-094)\n\nText.\n"


class ValidatorTests(unittest.TestCase):
    def project(self, master=MASTER, permissions=None, loops=LOOPS):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (directory / ".claude").mkdir()
        (directory / "MASTER_INSTRUCTIONS.md").write_text(master, encoding="utf-8")
        (directory / ".claude/settings.json").write_text(
            json.dumps({"permissions": permissions if permissions is not None else {"deny": DENIES}}), encoding="utf-8")
        (directory / "OPEN_LOOPS.md").write_text(loops, encoding="utf-8")
        return directory

    def test_complete_setup_passes_without_github(self):
        self.assertEqual(VALIDATOR.validate_closeout(self.project(), github=False), [])

    def test_missing_section_marker_or_denies_fail(self):
        errors = VALIDATOR.validate_closeout(
            self.project(master="# Master\n", permissions={"deny": []}, loops=LOOPS.replace("<!-- issue-mirror-from: OL-041 -->\n", "")),
            github=False)
        self.assertTrue(any("Automatic closeout" in e for e in errors))
        self.assertTrue(any("issue-mirror-from" in e for e in errors))
        self.assertTrue(any("git push --force" in e for e in errors))

    def test_a_gated_closeout_command_fails(self):
        errors = VALIDATOR.validate_closeout(
            self.project(permissions={"deny": DENIES, "ask": ["Bash(gh pr merge *)"]}), github=False)
        self.assertEqual(len(errors), 1)
        self.assertIn("gh pr merge", errors[0])

    def test_on_github_loops_from_the_marker_need_an_issue(self):
        errors = VALIDATOR.validate_closeout(self.project(), github=True)
        self.assertEqual(len(errors), 1)
        self.assertIn("OL-041", errors[0])
        linked = closeout.link_issue(LOOPS, "OL-041", 130, URL)
        self.assertEqual(VALIDATOR.validate_closeout(self.project(loops=linked), github=True), [])


if __name__ == "__main__":
    unittest.main()
