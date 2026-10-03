"""Exercise the delivered commands in disposable projects; never activate real work."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate_bootstrap import BOUND_DOCUMENTS, DOMAIN_FIELDS, NO_HARDWARE, architecture_fingerprint
import bootstrap_gate
from bootstrap_project import track_for

FIXTURES = {"software-hardware": "config/bootstrap.example.json"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def answers(profile):
    data = read(ROOT / FIXTURES[profile])
    project = data["project"]
    return {"domain_profile": profile, "project_name": project["name"], "objective": project["objective"],
            "success_criteria": project["definition_of_done"], "out_of_scope": project["non_goals"],
            "constraints": project["constraints"], "source_locations": data["sources"], "owner": "Synthetic test user",
            "risk_tier": "high", "sensitivity": "private", "connectors": ["github"], "connector_permissions": {"github": "read"},
            "bootstrap": {key: data[key] for key in ("architecture", "risks", "routing", "workflow", "human_gates", "domain", "unresolved")}}


class BootstrapIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_cli(self, script, *args, stdin="", ok=True):
        result = subprocess.run([sys.executable, str(script), *map(str, args)], input=stdin,
                                cwd=self.base, text=True, encoding="utf-8", capture_output=True,
                                env={**os.environ, "PYTHONUTF8": "1"})
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
        return result

    def generate(self, profile="software-hardware", script=None, data=None, extra=()):
        dest = self.base / (profile + "-" + str(len(list(self.base.iterdir()))))
        source = self.base / (dest.name + "-answers.json")
        write(source, data if data is not None else answers(profile))
        self.run_cli(script or ROOT / "scripts/bootstrap_project.py", "--answers", source, "--destination", dest, "--no-git", *extra)
        return dest

    def active_check(self, root, ok):
        return self.run_cli(root / "scripts/validate_bootstrap.py", root / "config/bootstrap.json", "--require-active", ok=ok)

    def activate(self, root):
        self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root)
        data = read(root / "config/bootstrap.json")
        fingerprint = architecture_fingerprint(data)
        self.run_cli(root / "scripts/bootstrap_gate.py", "activate", "--root", root,
                     stdin=f"Synthetic test user\nAPPROVE {fingerprint}\n")
        self.active_check(root, True)

    def test_no_hardware_selects_the_web_ui_track_and_fills_the_hardware_intake(self):
        data = answers("software-hardware")
        data["hardware_in_scope"] = False
        for key in ("hardware_identity", "physical_access"):
            data["bootstrap"]["domain"][key] = "TBD"
        root = self.generate(data=data)
        imports = [l for l in (root / "CLAUDE.md").read_text(encoding="utf-8").splitlines() if l.startswith("@instructions/tracks/")]
        self.assertEqual(imports, ["@instructions/tracks/web-ui.md"])
        state = read(root / "config/bootstrap.json")
        self.assertEqual(state["domain"]["hardware_identity"], NO_HARDWARE)
        self.assertEqual(state["domain"]["physical_access"], NO_HARDWARE)
        self.assertFalse(read(root / "config/project.json")["hardware_in_scope"] is True)
        self.activate(root)
        # The flag may not be a string; it silently disabling the hardware intake would be unsafe.
        data["hardware_in_scope"] = "false"
        dest = self.base / "bad-flag"
        write(self.base / "bad-flag.json", data)
        self.run_cli(ROOT / "scripts/bootstrap_project.py", "--answers", self.base / "bad-flag.json",
                     "--destination", dest, "--no-git", ok=False)

    def test_all_profiles_through_root_native_and_standalone_entrypoints(self):
        standalone = self.base / "installed-skill"
        shutil.copytree(ROOT / "skills/complex-project-bootstrapper", standalone, ignore=shutil.ignore_patterns("__pycache__"))
        scripts = [ROOT / "scripts/bootstrap_project.py", ROOT / ".agents/skills/complex-project-bootstrapper/scripts/bootstrap_project.py", standalone / "scripts/bootstrap_project.py"]
        for script in scripts:
            for profile in FIXTURES:
                with self.subTest(script=script, profile=profile):
                    root = self.generate(profile, script)
                    data = read(root / "config/bootstrap.json")
                    self.assertEqual(data["state"], "INTAKE")
                    self.assertFalse(data["approval"]["approved"])
                    self.assertEqual(data["domain_profile"], profile)
                    self.assertIn("autonomy OFF", (root / "PROJECT_STATE.md").read_text(encoding="utf-8"))
                    # A fresh project starts its own history, not the template's (#49).
                    decisions = (root / "DECISIONS.md").read_text(encoding="utf-8")
                    self.assertIn("ADR-000", decisions)
                    self.assertNotIn("ADR-001", decisions)
                    self.assertEqual(sorted(p.name for p in (root / "docs").glob("*VALIDATION.md")), [])
                    self.assertEqual(sorted(p.name for p in (root / "archive").glob("*_ARCHIVE_*.md")) if (root / "archive").exists() else [], [],
                                     "template ADR and changelog archives are template history, not the project's")
                    self.assertTrue((root / "docs/PLATFORMIO.md").exists(), "reusable docs stay")
                    # ADR-082: a generated project imports its own track, and only that one.
                    track = track_for({})
                    imports = [l for l in (root / "CLAUDE.md").read_text(encoding="utf-8").splitlines() if l.startswith("@instructions/tracks/")]
                    self.assertEqual(imports, [f"@instructions/tracks/{track}.md"])
                    self.assertTrue((root / f"instructions/tracks/{track}.md").is_file())
                    self.assertFalse((root / "skills/complex-project-bootstrapper/assets/project-template").exists(),
                                     "a generated project has no payload, so CI skips the payload check")
                    self.assertFalse((root / "archive/legal").exists(), "ADR-083: retired legal profiles are not served")
                    charter_text = (root / "PROJECT_CHARTER.md").read_text(encoding="utf-8")
                    self.assertNotIn("legal", charter_text.lower(), "OL-031: no legal wording in a generated charter")
                    self.assertNotIn("Jurisdiction", charter_text)
                    self.active_check(root, False)
                    self.activate(root)
                    self.run_cli(root / "scripts/validate_project.py")
                    # The same standalone/native payload must deliver usable packet tooling.
                    packet = root / "synthetic-packet.json"
                    self.run_cli(root / "scripts/work_packet.py", "create",
                                 root / "examples/work-packets" / f"{profile}.contract.json",
                                 "--task-id", "DELIVERY-1", "--profile", profile,
                                 "--actor", "Synthetic architect", "--reason", "Distribution test",
                                 "--output", packet)
                    self.run_cli(root / "scripts/work_packet.py", "validate", packet)
                    rendered = self.run_cli(root / "scripts/work_packet.py", "render", packet)
                    self.assertIn("DELIVERY-1", rendered.stdout)
                    # Routing stays offline even with enabled synthetic resources.
                    for state in ("ARCHITECTED", "READY"):
                        next_packet = root / f"synthetic-packet-{state}.json"
                        self.run_cli(root / "scripts/work_packet.py", "transition", packet,
                                     "--to", state, "--role", "architect", "--actor", "Synthetic architect",
                                     "--reason", "Router delivery check", "--output", next_packet)
                        packet = next_packet
                    data = read(packet)
                    revision = data["revision_history"][-1]
                    request = root / "synthetic-routing-request.json"
                    write(request, {"schema_version": "1.0", "binding": {
                        "task_id": data["task_id"], "revision": revision["version"],
                        "contract_hash": revision["hash"], "role": "worker"},
                        "task_class": "delivery-test", "input_tokens": 100, "output_tokens": 100,
                        "unavailable_providers": [], "unavailable_resources": [], "attempts": [], "observations": []})
                    resources = read(root / "config/model-router.example.json")
                    for resource in resources["resources"]:
                        resource["enabled"] = True
                    config = root / "synthetic-routing-config.json"
                    write(config, resources)
                    ledger = root / "synthetic-routing-record.json"
                    routed = self.run_cli(root / "scripts/model_router.py", "route", packet,
                                         "--config", config, "--request", request, "--output", ledger)
                    self.assertEqual(json.loads(routed.stdout)["status"], "ROUTED")
                    self.assertFalse(json.loads(routed.stdout)["execution_authorized"])
                    self.run_cli(root / "scripts/model_router.py", "verify", ledger)
                    options = root / "synthetic-feedback-options.json"
                    write(options, {key: read(request)[key] for key in (
                        "task_class", "input_tokens", "output_tokens", "unavailable_providers", "unavailable_resources")})
                    feedback_ledger = root / "synthetic-feedback-ledger"
                    self.run_cli(root / "scripts/feedback.py", "init", feedback_ledger,
                                 "--root", root, "--packet", packet, "--graph", packet,
                                 "--policy", root / "config/feedback.example.json", "--config", config,
                                 "--architect", "Synthetic architect")
                    dispatched = self.run_cli(root / "scripts/feedback.py", "next", feedback_ledger,
                                              "--root", root, "--config", config, "--options", options)
                    intent = json.loads(dispatched.stdout)
                    self.assertEqual(intent["status"], "DISPATCH")
                    result = root / "synthetic-feedback-result.json"
                    write(result, {"dispatch_id": intent["dispatch_id"], "outcome": "PASS",
                        "summary": "Synthetic distribution check", "scope_status": "within", "architecture_conflict": False,
                        "validation": [{"check_id": check["id"], "passed": True, "failure_code": "", "expected": "", "actual": "",
                                        "evidence": ["Synthetic check only"]} for check in revision["contract"]["validation"]],
                        "evidence": ["Synthetic evidence only"], "discoveries": [], "api_cost_usd": 0,
                        "cost_evidence": "No model invoked; synthetic test"})
                    completed = self.run_cli(root / "scripts/feedback.py", "complete", feedback_ledger, result)
                    self.assertEqual(json.loads(completed.stdout)["status"], "REVIEW_PENDING")
                    replayed = self.run_cli(root / "scripts/feedback.py", "status", feedback_ledger)
                    self.assertEqual(json.loads(replayed.stdout)["total_attempts"], 1)
                    self.run_cli(root / "scripts/feedback.py", "render", feedback_ledger)
                    published_packet = json.loads(self.run_cli(root / "scripts/feedback.py", "packet", feedback_ledger).stdout)
                    raw_events = [read(path) for path in sorted(feedback_ledger.glob("*.json"))]

    def test_interactive_only_asks_missing_material_domain_field(self):
        for profile in FIXTURES:
            with self.subTest(profile=profile):
                raw = answers(profile)
                field = next(iter(DOMAIN_FIELDS[profile]))
                expected = raw["bootstrap"]["domain"].pop(field)
                source = self.base / f"{profile}.json"
                write(source, raw)
                dest = self.base / profile
                result = self.run_cli(ROOT / "scripts/bootstrap_project.py", "--interactive", "--answers", source,
                                      "--destination", dest, "--no-git", stdin=expected + "\n")
                self.assertNotIn("Project name:", result.stdout)
                self.assertIn(DOMAIN_FIELDS[profile][field], result.stdout)
                self.assertEqual(read(dest / "config/bootstrap.json")["domain"][field], expected)
                self.active_check(dest, False)

    def test_fresh_interactive_intake_and_architect_handoff_for_every_profile(self):
        keys = ("project_name", "objective", "success_criteria", "out_of_scope", "constraints", "source_locations", "owner", "risk_tier", "sensitivity")
        for profile in FIXTURES:
            with self.subTest(profile=profile):
                raw = answers(profile)
                responses = ["; ".join(raw[key]) if isinstance(raw[key], list) else raw[key] for key in keys]
                responses.append("y")  # Does the project involve hardware?
                responses += [raw["bootstrap"]["domain"][key] for key in DOMAIN_FIELDS[profile]]
                root = self.base / profile
                self.run_cli(ROOT / "scripts/bootstrap_project.py", "--interactive", "--profile", profile,
                             "--destination", root, "--no-git", stdin="\n".join(responses) + "\n")
                self.active_check(root, False)
                self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root, ok=False)
                data = read(root / "config/bootstrap.json")
                # A synthetic architect completes the proposal after the staged intake.
                data.update(raw["bootstrap"])
                write(root / "config/bootstrap.json", data)
                self.activate(root)

    def test_profile_recovery_from_each_canonical_branch_profile(self):
        # Copies of the existing branch profiles exercise the common extension hook.
        for profile in FIXTURES:
            with self.subTest(profile=profile):
                template = self.base / (profile + "-template")
                shutil.copytree(ROOT, template, ignore=shutil.ignore_patterns(".git", "assets", "__pycache__"))
                shutil.copyfile(ROOT / "templates" / profile / "PROFILE.md", template / "DOMAIN_PROFILE.md")
                raw = answers(profile)
                raw.pop("domain_profile")
                root = self.generate(profile, data=raw, extra=("--template-root", template))
                self.assertEqual(read(root / "config/bootstrap.json")["domain_profile"], profile)

    def test_supplied_active_state_and_approval_cannot_activate_generation(self):
        raw = answers("software-hardware")
        raw["bootstrap"].update({"state": "ACTIVE", "approval": {"approved": True}})
        root = self.generate(data=raw)
        self.active_check(root, False)
        self.assertFalse(read(root / "config/bootstrap.json")["approval"]["approved"])

    def test_failed_generation_cannot_inherit_source_project_approval(self):
        source = self.generate()
        self.activate(source)
        raw = answers("software-hardware")
        raw["bootstrap"]["architecture"] = []
        answer_file = self.base / "failed-copy.json"
        write(answer_file, raw)
        dest = self.base / "failed-new-project"
        self.run_cli(ROOT / "scripts/bootstrap_project.py", "--template-root", source, "--answers", answer_file,
                     "--destination", dest, "--no-git", ok=False)
        self.assertFalse((dest / "config/bootstrap.json").exists())
        self.assertFalse((dest / "BOOTSTRAP_REVIEW.md").exists())
        self.active_check(dest, False)
        self.active_check(source, True)

    def test_missing_or_wrong_confirmation_leaves_package_inactive(self):
        root = self.generate()
        self.run_cli(root / "scripts/bootstrap_gate.py", "activate", "--root", root, ok=False)
        self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root)
        for stdin in ("", "Synthetic test user\nyes\n", "Synthetic test user\nAPPROVE wrong\n"):
            self.run_cli(root / "scripts/bootstrap_gate.py", "activate", "--root", root, stdin=stdin, ok=False)
            self.active_check(root, False)

    def test_incomplete_or_blocked_architecture_cannot_be_reviewed(self):
        raw = answers("software-hardware")
        raw["bootstrap"] = {}
        root = self.generate(data=raw)
        self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root, ok=False)
        self.active_check(root, False)
        root = self.generate()
        data = read(root / "config/bootstrap.json")
        data["unresolved"] = ["Owner must choose the supported hardware"]
        write(root / "config/bootstrap.json", data)
        self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root, ok=False)

    def test_review_refuses_placeholder_phrases_and_unassessed_risks(self):
        for field, value in (("architecture", "TBD later"), ("risks", [])):
            with self.subTest(field=field):
                root = self.generate()
                data = read(root / "config/bootstrap.json")
                if field == "architecture":
                    data[field]["summary"] = value
                else:
                    data[field] = value
                write(root / "config/bootstrap.json", data)
                self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root, ok=False)
                self.active_check(root, False)

    def test_project_configuration_and_all_bound_documents_invalidate_approval(self):
        root = self.generate()
        self.activate(root)
        config_path = root / "config/project.json"
        original = config_path.read_bytes()
        data = read(config_path)
        data["connector_permissions"]["github"] = "write"
        write(config_path, data)
        self.active_check(root, False)
        self.run_cli(root / "scripts/validate_project.py", ok=False)
        config_path.write_bytes(original)
        for name in BOUND_DOCUMENTS:
            with self.subTest(document=name):
                path = root / name
                before = path.read_bytes()
                path.write_bytes(before + b"\nMaterial change after approval.\n")
                self.active_check(root, False)
                path.write_bytes(before)
        self.active_check(root, True)

    def test_rebootstrap_refused_and_user_records_preserved(self):
        root = self.generate()
        self.activate(root)
        before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and "__pycache__" not in str(p)}
        raw = answers("software-hardware")
        raw["objective"] = "Changed objective"
        source = self.base / "changed.json"
        write(source, raw)
        self.run_cli(root / "scripts/bootstrap_project.py", "--answers", source, "--destination", root,
                     "--template-root", root, "--no-git", ok=False)
        after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and "__pycache__" not in str(p)}
        self.assertEqual(before, after)
        self.active_check(root, True)

    def test_review_revokes_approval_and_missing_state_fails_project_validation(self):
        root = self.generate()
        self.activate(root)
        self.run_cli(root / "scripts/bootstrap_gate.py", "review", "--root", root)
        self.active_check(root, False)
        self.assertFalse(read(root / "config/bootstrap.json")["approval"]["approved"])
        self.assertIn("SETUP — autonomy OFF", (root / "PROJECT_STATE.md").read_text(encoding="utf-8"))
        (root / "config/bootstrap.json").unlink()
        self.run_cli(root / "scripts/validate_project.py", ok=False)

    @unittest.skipUnless(shutil.which("git"), "Git is needed for the approval portability regression")
    def test_approval_survives_git_commit_and_fresh_clone(self):
        root = self.generate()
        # Force the Windows representation even when CI runs on Linux.
        for name in BOUND_DOCUMENTS:
            path = root / name
            path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        self.activate(root)
        for args in (("init",), ("add", "."), ("-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid", "-c", "commit.gpgsign=false", "commit", "-m", "Synthetic approved foundation")):
            result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        clone = self.base / "fresh-clone"
        result = subprocess.run(["git", "clone", "--no-hardlinks", str(root), str(clone)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.active_check(clone, True)

    def test_malformed_cli_input_fails_without_traceback(self):
        root = self.generate()
        for data in ([], None, {"domain_profile": []}, {"state": "ACTIVE"}):
            write(root / "config/bootstrap.json", data)
            self.active_check(root, False)

    def test_malformed_answers_are_rejected_before_generation(self):
        for field, values in {"success_criteria": [[{}], None, 42], "source_locations": [[{}], [""]], "objective": [{}, 123], "connector_permissions": [[], {"github": {}}], "bootstrap": [[]]}.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    raw = answers("software-hardware")
                    raw[field] = value
                    source = self.base / "malformed.json"
                    write(source, raw)
                    dest = self.base / "must-not-exist"
                    self.run_cli(ROOT / "scripts/bootstrap_project.py", "--answers", source, "--destination", dest, "--no-git", ok=False)
                    self.assertFalse(dest.exists())


class ApprovalInteractionTests(unittest.TestCase):
    """#29: the framed approval banner, and the typed confirmation it must not weaken."""

    def setUp(self):
        self.helper = BootstrapIntegrationTests("run")
        self.helper.setUp()
        self.addCleanup(self.helper.temp.cleanup)
        self.root = self.helper.generate()
        self.helper.run_cli(self.root / "scripts/bootstrap_gate.py", "review", "--root", self.root)
        self.state = self.root / "config/bootstrap.json"
        self.fingerprint = architecture_fingerprint(read(self.state))

    def activate(self, *replies):
        """Run activation in-process; each reply is a string or an exception raised by input()."""
        pending = list(replies)
        prompts = []

        def fake_input(prompt=""):
            prompts.append(prompt)
            reply = pending.pop(0)
            if isinstance(reply, BaseException) or (isinstance(reply, type) and issubclass(reply, BaseException)):
                raise reply
            return reply(self) if callable(reply) else reply

        output = io.StringIO()
        with mock.patch("builtins.input", fake_input), contextlib.redirect_stdout(output):
            try:
                return None, bootstrap_gate.activate(self.root), output.getvalue(), prompts
            except BaseException as exc:  # noqa: BLE001 - the tests assert on the exception type
                return exc, None, output.getvalue(), prompts

    def assert_inactive(self, before):
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual("AWAITING_APPROVAL", read(self.state)["state"])
        self.helper.active_check(self.root, False)

    def test_banner_frames_state_full_fingerprint_and_consequence(self):
        banner = bootstrap_gate.approval_banner(read(self.state), self.fingerprint)
        lines = banner.splitlines()
        self.assertTrue(lines[0].startswith("=") and lines[-1].startswith("="))
        self.assertTrue(all(ch.isascii() for ch in banner))
        self.assertTrue(all(len(line) <= 80 for line in lines), max(map(len, lines)))
        self.assertIn("AWAITING_APPROVAL", banner)
        self.assertIn("autonomy is OFF", banner)
        self.assertIn(self.fingerprint, banner)
        self.assertIn("ACTIVE", banner)
        self.assertIn("APPROVE " + self.fingerprint, banner)
        self.assertIn("blank", banner.lower())
        self.assertNotIn("\x1b", banner)

    def test_banner_escapes_control_characters_and_wraps_long_names(self):
        data = read(self.state)
        data["project"]["name"] = "Evil\x1b[2J\r\u202eName " + "X" * 200
        banner = bootstrap_gate.approval_banner(data, self.fingerprint)
        self.assertTrue(all(ch.isprintable() for line in banner.splitlines() for ch in line), repr(banner))
        self.assertIn("\\x1b[2J\\r\\u202eName", banner)
        self.assertTrue(all(len(line) <= 80 for line in banner.splitlines()), max(map(len, banner.splitlines())))
        self.assertEqual(1, banner.count("   APPROVE " + self.fingerprint))
        # Wide or combining characters would make code-point wrapping misjudge terminal columns.
        data["project"]["name"] = "\u754c" * 43 + " Cafe\u0301 \U0001F600"
        banner = bootstrap_gate.approval_banner(data, self.fingerprint)
        self.assertTrue(all(ch.isascii() and ch.isprintable() for line in banner.splitlines() for ch in line), repr(banner))
        self.assertIn("\\u754c", banner)
        self.assertTrue(all(len(line) <= 80 for line in banner.splitlines()), max(map(len, banner.splitlines())))

    def test_exact_confirmation_activates_and_banner_precedes_prompts(self):
        banner = bootstrap_gate.approval_banner(read(self.state), self.fingerprint)
        exc, data, output, prompts = self.activate("Synthetic test user", f"APPROVE {self.fingerprint}")
        self.assertIsNone(exc)
        self.assertEqual("ACTIVE", data["state"])
        self.assertEqual(["Approving user identity: ", f"Type APPROVE {self.fingerprint}: "], prompts)
        self.assertIn(banner, output)
        self.assertTrue(output.endswith(banner + "\n"), "the banner must sit directly above the prompts")
        self.helper.active_check(self.root, True)

    def test_wrong_fingerprint_blank_and_generic_yes_leave_autonomy_off(self):
        before = self.state.read_bytes()
        wrong = "0" * 64 if self.fingerprint != "0" * 64 else "1" * 64
        for identity, decision in (("Synthetic test user", f"APPROVE {wrong}"), ("Synthetic test user", ""),
                                   ("", f"APPROVE {self.fingerprint}"), ("Synthetic test user", "yes"),
                                   ("Synthetic test user", f"approve {self.fingerprint}")):
            with self.subTest(identity=identity, decision=decision):
                exc, data, _, _ = self.activate(identity, decision)
                self.assertIsInstance(exc, ValueError)
                self.assertIsNone(data)
                self.assert_inactive(before)

    def test_eof_and_interrupt_leave_autonomy_off(self):
        before = self.state.read_bytes()
        for replies, expected in (((EOFError,), EOFError), (("Synthetic test user", EOFError), EOFError),
                                  ((KeyboardInterrupt,), KeyboardInterrupt),
                                  (("Synthetic test user", KeyboardInterrupt), KeyboardInterrupt)):
            with self.subTest(replies=replies):
                exc, data, _, _ = self.activate(*replies)
                self.assertIsInstance(exc, expected)
                self.assertIsNone(data)
                self.assert_inactive(before)

    def test_foundation_change_during_input_still_refuses(self):
        def tamper(test):
            data = read(test.state)
            data["architecture"]["boundaries"].append("Changed during approval")
            write(test.state, data)
            return f"APPROVE {test.fingerprint}"
        exc, data, _, _ = self.activate("Synthetic test user", tamper)
        self.assertIsInstance(exc, ValueError)
        self.assertIn("changed during approval", str(exc))
        self.assertNotEqual("ACTIVE", read(self.state)["state"])
        self.helper.active_check(self.root, False)


if __name__ == "__main__":
    unittest.main()
