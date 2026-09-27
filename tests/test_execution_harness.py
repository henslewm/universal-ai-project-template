from __future__ import annotations

import copy
import hashlib
import json
import posixpath
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from test_feedback import ANCHOR, active_project, options, policy, result, timestamp
from test_model_router import config as router_config
from test_model_router import make_packet, resource


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import execution_harness as harness

wp = harness.wp


def configuration():
    value = wp.read_json(ROOT / "config/execution-harness.example.json")
    value["enabled"] = True
    value["bindings"] = [{"resource_id": "local", "harness_id": "cline-cli", "provider": "lmstudio",
                          "model": "synthetic-local-coder", "api_base": "http://127.0.0.1:1234/v1",
                          "credential_env": None, "served_context_window": None}]
    return value


class HarnessConfigTests(unittest.TestCase):
    def test_real_template_governance_fits_the_example_brief_limit(self):
        config = wp.read_json(ROOT / "config/execution-harness.example.json")
        bundle = harness.startup_bundle(ROOT, config)
        self.assertEqual(bundle["role"], "worker")
        # Keep room for the contract and dispatch metadata, not just the source text.
        size = len(json.dumps(bundle, indent=2, ensure_ascii=False))
        self.assertLess(size + 10000, config["limits"]["brief_max_chars"])

    def test_example_configuration_is_valid_disabled_and_credential_free(self):
        example = wp.read_json(ROOT / "config/execution-harness.example.json")
        harness.config_valid(example)
        self.assertFalse(example["enabled"], "The committed example must not be dispatch-enabled")
        for binding in example["bindings"]:
            self.assertIsNone(binding["credential_env"] or None if binding["credential_env"] is None else None)
        self.assertTrue(any(binding["credential_env"] for binding in example["bindings"]),
                        "A cloud tier should demonstrate environment-named credentials")
        self.assertTrue(any(item["adapter"] == "command" for item in example["harnesses"]),
                        "A replacement harness must be demonstrated so Cline is visibly optional")

    def test_configuration_refuses_credentials_unknown_placeholders_and_bad_bindings(self):
        for mutate, expected in (
            (lambda c: c["bindings"][0].update(credential_env="not-an-env-name"), "environment-variable name"),
            (lambda c: c["bindings"][0].update(harness_id="absent-harness"), "unknown harness"),
            (lambda c: c["bindings"][0].update(api_base="file:///etc/passwd"), "Unsafe API base"),
            (lambda c: c["harnesses"][0]["argv"].append("--key={provider_secret}"), "Unsupported placeholder"),
            (lambda c: c["harnesses"][0].update(command="{brief}"), "command itself cannot be templated"),
            (lambda c: c["harnesses"][0].update(argv=[a.replace("{brief}", "") for a in c["harnesses"][0]["argv"]]),
             "must receive the brief"),
            (lambda c: c["harnesses"][0].update(argv=[a.replace("{report}", "") for a in c["harnesses"][0]["argv"]]),
             "must write a report"),
            (lambda c: c["harnesses"][0]["argv"].append("--api-key=sk-abcdefghijklmnopqrstuvwxyz"), "credential-like"),
            (lambda c: c["harnesses"][0]["argv"].append("authorization: Bearer x"), "credential-like"),
        ):
            with self.subTest(expected=expected):
                value = configuration()
                mutate(value)
                with self.assertRaisesRegex(ValueError, expected):
                    harness.config_valid(value)

    def test_every_harness_declares_its_own_context_overhead_and_the_limits_declare_a_divisor(self):
        example = wp.read_json(ROOT / "config/execution-harness.example.json")
        harness.config_valid(example)
        self.assertGreater(example["limits"]["chars_per_token"], 0)
        cline = next(item for item in example["harnesses"] if item["adapter"] == "cline")
        self.assertGreater(cline["context_overhead_tokens"], 0,
                           "a harness with its own system prompt consumes context before the brief")
        for drop, expected in (
            (lambda c: c["limits"].pop("chars_per_token"), "chars_per_token"),
            (lambda c: c["harnesses"][0].pop("context_overhead_tokens"), "context_overhead_tokens"),
            (lambda c: c["bindings"][0].pop("served_context_window"), "served_context_window"),
            (lambda c: c["limits"].pop("context_growth_reserve_tokens"), "context_growth_reserve_tokens"),
        ):
            with self.subTest(expected=expected):
                value = configuration()
                drop(value)
                with self.assertRaisesRegex(ValueError, expected):
                    harness.config_valid(value)

    def test_duplicate_harness_and_resource_bindings_are_refused(self):
        value = configuration()
        value["harnesses"].append(copy.deepcopy(value["harnesses"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate harness id"):
            harness.config_valid(value)
        value = configuration()
        value["bindings"].append(copy.deepcopy(value["bindings"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate routed resource"):
            harness.config_valid(value)


class HarnessBase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        active_project(self.project)
        for name in harness.STARTUP_DOCUMENTS:
            path = self.project / name
            if not path.exists():
                path.write_text(f"# Synthetic startup instruction: {name}\nStay within the packet.\n", encoding="utf-8")
        self.ledger = self.base / "ledger"
        self.config = configuration()
        self.router = router_config(resource())
        self.packet = make_packet()
        patch = mock.patch.object(harness.feedback, "active_anchor", return_value=ANCHOR)
        patch.start()
        self.addCleanup(patch.stop)
        harness.feedback.initialize(self.ledger, self.packet, [self.packet], policy(), self.router,
                                    self.project, "Synthetic architect", timestamp())

    def fresh_ledger(self, name):
        path = self.base / name
        harness.feedback.initialize(path, self.packet, [self.packet], policy(), self.router,
                                    self.project, "Synthetic architect", timestamp())
        return path

    def prepare(self, destination="run-1"):
        return harness.dispatch(self.ledger, self.config, self.router, options(),
                                self.project, self.base / destination)

class HarnessDispatchTests(HarnessBase):
    def test_dispatch_embeds_complete_ordered_startup_for_brief_only_harnesses(self):
        (self.project / "AGENTS.md").write_text("# Local startup\nKeep packet boundaries.\n", encoding="utf-8")
        nested = self.project / "module"
        nested.mkdir()
        extra = nested / "AGENTS.md"
        extra.write_bytes("# Scoped instructions\r\nPreserve café fixtures.\r\n".encode("utf-8"))
        self.config["startup_documents"] = ["module/AGENTS.md"]
        self.config["bindings"][0]["harness_id"] = "replacement-harness"
        prepared = self.prepare()
        document = wp.read_json(Path(prepared["destination"]) / "brief.json")
        self.assertEqual(document["schema_version"], "1.1")
        startup = document["startup"]
        self.assertEqual(startup["role"], "worker")
        sources = startup["documents"]
        self.assertEqual([item["path"] for item in sources],
                         [*harness.STARTUP_DOCUMENTS, "AGENTS.md", "module/AGENTS.md", harness.WORKER_RULES_PATH])
        for item in sources:
            base = self.project if item["source"] == "project" else ROOT
            original = (base / item["path"]).read_bytes()
            self.assertEqual("".join(item["content_lines"]), original.decode("utf-8"))
            self.assertEqual(item["sha256"], hashlib.sha256(original).hexdigest())
        self.assertNotIn(str(Path(prepared["destination"]) / "BOUNDED_WORKER_RULES.md"),
                         prepared["invocation"]["argv"], "This harness receives only the brief and report paths")
        self.assertEqual(document["contract"], wp.current(self.packet)["contract"])
        steps = " ".join(startup["steps"])
        for required in ("before implementation", "contract.context_scope", "review_rejections",
                         "BLOCKED", "ARCHITECTURE_CONFLICT"):
            self.assertIn(required, steps)

    def test_bad_startup_documents_refuse_without_spending_attempts_or_creating_run(self):
        required = self.project / harness.STARTUP_DOCUMENTS[0]
        original = required.read_bytes()
        for name, content, expected in (
            ("missing", None, "missing or unreadable"),
            ("empty", b" \r\n", "empty"),
            ("invalid-utf8", b"\xff\xfe", "missing or unreadable"),
            ("credential", b"api_key: sk-abcdefghijklmnopqrstuvwxyz", "credential-like"),
            ("oversized", b"x" * (self.config["limits"]["brief_max_chars"] + 1), "configured brief bound"),
        ):
            with self.subTest(case=name):
                required.unlink()
                if content is not None:
                    required.write_bytes(content)
                destination = self.base / name
                with mock.patch.object(harness.feedback, "reserve") as reserve:
                    with self.assertRaisesRegex(ValueError, expected):
                        harness.dispatch(self.ledger, self.config, self.router, options(), self.project, destination)
                    reserve.assert_not_called()
                self.assertFalse(destination.exists())
                required.write_bytes(original)
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"], [])

    def test_unreadable_startup_file_is_refused_before_reservation(self):
        blocked = self.project / harness.STARTUP_DOCUMENTS[0]
        original_open = Path.open

        def open_file(path, *args, **kwargs):
            if path == blocked:
                raise PermissionError("Synthetic unreadable governance")
            return original_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", new=open_file), mock.patch.object(harness.feedback, "reserve") as reserve:
            with self.assertRaisesRegex(ValueError, "missing or unreadable"):
                self.prepare()
            reserve.assert_not_called()

    def test_explicit_extra_instruction_is_required_even_for_normally_optional_file(self):
        for extra in ("missing/handoff.md", "CONTRIBUTING.md"):
            with self.subTest(extra=extra):
                self.config["startup_documents"] = [extra]
                with mock.patch.object(harness.feedback, "reserve") as reserve:
                    with self.assertRaisesRegex(ValueError, "missing or unreadable"):
                        self.prepare()
                    reserve.assert_not_called()

    def test_case_sensitive_instruction_paths_are_not_deduplicated(self):
        # Exercise POSIX identities even on a Windows test host. A case-sensitive filesystem
        # may hold both spellings, or only the uppercase canonical source.
        extra = "master_instructions.md"
        self.config["startup_documents"] = [extra]
        read_document = harness.startup_document
        content = "Distinct lowercase instruction file.\n"

        def read_case_sensitive(root, relative, source, remaining, optional=False):
            if relative == extra:
                return {"source": source, "path": relative, "content_lines": [content],
                        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
            return read_document(root, relative, source, remaining, optional)

        with mock.patch.object(harness, "startup_identity", side_effect=posixpath.normcase):
            with mock.patch.object(harness, "startup_document", side_effect=read_case_sensitive):
                bundle = harness.startup_bundle(self.project, self.config)
            names = [document["path"] for document in bundle["documents"]]
            self.assertIn("MASTER_INSTRUCTIONS.md", names)
            self.assertIn(extra, names)

            def missing_case_sensitive(root, relative, source, remaining, optional=False):
                if relative == extra:
                    raise ValueError("Startup document is missing or unreadable: " + extra)
                return read_document(root, relative, source, remaining, optional)

            with mock.patch.object(harness, "startup_document", side_effect=missing_case_sensitive), \
                    mock.patch.object(harness.feedback, "reserve") as reserve:
                with self.assertRaisesRegex(ValueError, "missing or unreadable"):
                    self.prepare()
                reserve.assert_not_called()

    def test_startup_paths_refuse_escape_and_cross_platform_absolute_names(self):
        for extra in ("../outside.md", "module/../../outside.md", "module\\..\\outside.md",
                      "/absolute.md", "C:\\absolute.md", "C:relative.md", "\\\\server\\share\\doc.md",
                      "module/file.md:stream", "module//file.md", ".. /outside.md", "module./file.md",
                      "module/file.md ", "NUL.md", "CON", "aux.txt", "COM1.md", "LPT¹.log",
                      "CONIN$", "module/CON .txt", "bad\x00name.md"):
            with self.subTest(extra=extra):
                self.config["startup_documents"] = [extra]
                with mock.patch.object(harness.feedback, "reserve") as reserve:
                    with self.assertRaises(ValueError):
                        self.prepare()
                    reserve.assert_not_called()

    def test_reparse_directory_is_refused_before_reading_its_document(self):
        nested = self.project / "linked"
        nested.mkdir()
        (nested / "AGENTS.md").write_text("Never read this source", encoding="utf-8")
        self.config["startup_documents"] = ["linked/AGENTS.md"]
        original_lstat = Path.lstat

        def lstat(path, *args, **kwargs):
            metadata = original_lstat(path, *args, **kwargs)
            if path == nested:
                return SimpleNamespace(st_mode=metadata.st_mode, st_file_attributes=0x400)
            return metadata

        with mock.patch.object(Path, "lstat", new=lstat), mock.patch.object(harness.feedback, "reserve") as reserve:
            with self.assertRaisesRegex(ValueError, "symlink or reparse point"):
                self.prepare()
            reserve.assert_not_called()

    def test_startup_documents_are_cumulatively_bounded_before_reservation(self):
        self.config["limits"]["brief_max_chars"] = 3000
        for name in harness.STARTUP_DOCUMENTS:
            (self.project / name).write_text("x" * 700, encoding="utf-8")
        with mock.patch.object(harness.feedback, "reserve") as reserve:
            with self.assertRaisesRegex(ValueError, "configured brief bound"):
                self.prepare()
            reserve.assert_not_called()

    def test_dispatch_prepares_a_bounded_brief_and_never_executes_the_harness(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("the adapter must not run a harness")):
            prepared = self.prepare()
        self.assertEqual(prepared["status"], "PREPARED")
        self.assertFalse(prepared["executed"])
        self.assertFalse(prepared["execution_authorized"])
        destination = Path(prepared["destination"])
        brief = wp.read_json(destination / "brief.json")
        self.assertEqual(brief["dispatch_id"], prepared["dispatch_id"])
        self.assertEqual(brief["harness"]["model"], "synthetic-local-coder")
        self.assertTrue((destination / "BOUNDED_WORKER_RULES.md").exists())
        self.assertTrue((destination / "workspace").is_dir())
        self.assertFalse((destination / "report.json").exists(), "the worker writes its own report")
        plan = wp.read_json(destination / "invocation.json")
        self.assertEqual(plan["argv"][0], "cline")
        rendered = "\u0000".join(plan["argv"])
        for path in ("brief.json", "report.json", "BOUNDED_WORKER_RULES.md", "workspace"):
            self.assertIn(str(destination / path), rendered)
        self.assertNotIn("{", rendered, "every placeholder must be substituted")
        self.assertEqual(plan["required_environment"], [])

    def test_brief_is_readable_line_by_line_and_states_the_whole_report_contract(self):
        prepared = self.prepare()
        path = Path(prepared["destination"]) / "brief.json"
        text = path.read_text(encoding="utf-8")
        # A line-based reader must not need a workaround: the brief is indented, not one long line.
        self.assertGreater(len(text.splitlines()), 20)
        self.assertLess(max(len(line) for line in text.splitlines()), 2000)
        contract = wp.read_json(path)["report_contract"]
        self.assertEqual(contract["validation_check_fields"],
                         sorted(harness.feedback.SCHEMA["$defs"]["validation_check"]["required"]))
        self.assertIn("check_id", contract["validation_check_fields"])
        self.assertNotIn("id", contract["validation_check_fields"])
        rules = " ".join(contract["rules"])
        self.assertIn("check_id, not id", rules)
        # The worker must never have to guess a path: every one is substituted, none left templated.
        document = wp.read_json(path)
        self.assertEqual(contract["write_to"], str(Path(prepared["destination"]) / "report.json"))
        self.assertEqual(document["paths"], {
            "workspace": str(Path(prepared["destination"]) / "workspace"),
            "brief": str(path), "rules": str(Path(prepared["destination"]) / "BOUNDED_WORKER_RULES.md"),
            "report": str(Path(prepared["destination"]) / "report.json")})
        for value in list(document["paths"].values()) + [contract["write_to"]]:
            self.assertNotIn("{", value, "a templated path would force the worker to guess")
        self.assertIn("exactly the write_to path", rules)
        # Every value the validator enforces is stated, so a compliant worker can actually comply.
        self.assertEqual(sorted(contract["required_fields"]), sorted(harness.REPORT_FIELDS))
        self.assertIn("PROVIDER_UNAVAILABLE", contract["outcomes"])
        self.assertEqual(contract["scope_status_values"], ["within", "violated", "unknown"])
        # A report built strictly from the stated contract is accepted.
        report = {field: None for field in contract["required_fields"]}
        report.update(dispatch_id=prepared["dispatch_id"], outcome="PASS", scope_status="within",
                      summary="Built only from the fields the brief states.", architecture_conflict=False,
                      evidence=["command, stdout and exit code"], discoveries=[], api_cost_usd=0,
                      cost_evidence="Local worker; no metered usage.",
                      validation=[{"check_id": check["id"], "passed": True, "failure_code": "",
                                   "expected": "checker exits 0", "actual": "checker exited 0",
                                   "evidence": ["python workspace/check.py -> ALL CHECKS PASSED"]}
                                  for check in wp.read_json(path)["contract"]["validation"]])
        wp.write_new(Path(prepared["destination"]) / "report.json", json.dumps(report, indent=2))
        ingested = harness.ingest(self.ledger, self.config, Path(prepared["destination"]) / "report.json")
        self.assertEqual(ingested["outcome"], "PASS")

    def test_brief_carries_only_packet_permitted_context_and_stays_bounded(self):
        prepared = self.prepare()
        brief = wp.read_json(Path(prepared["destination"]) / "brief.json")
        harness.feedback.exact(brief, harness.BRIEF_FIELDS)
        contract = wp.current(self.packet)["contract"]
        self.assertEqual(brief["contract"], contract)
        for required in ("scope", "context_scope", "architecture_boundaries", "non_goals", "validation"):
            self.assertIn(required, brief["contract"])
        self.assertIn("Execute only this contract", brief["worker_rule"])
        self.assertLessEqual(brief["bounds"]["remaining_task_attempts"], contract["retry_budget"]["max_attempts"])


    def test_disabled_configuration_refuses_before_spending_a_reservation(self):
        disabled = configuration()
        disabled["enabled"] = False
        with self.assertRaisesRegex(ValueError, "disabled"):
            harness.dispatch(self.ledger, disabled, self.router, options(), self.project, self.base / "off")
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"], [])

    def test_unpreparable_dispatch_closes_its_attempt_as_provider_unavailable(self):
        for name, mutate, expected in (
            ("unbound", lambda c: c["bindings"][0].update(resource_id="some-other-resource"),
             "No harness binding for routed resource"),
            # A window the worker cannot physically accept is a refusal, not a run that fails on
            # its first tool call: the routed resource here declares 100000 tokens, the local
            # server is loaded with 8192, and the harness prompt alone claims 7000 of them.
            ("served-window-too-small", lambda c: c["bindings"][0].update(served_context_window=8192),
             "is served a 8192-token window"),
        ):
            with self.subTest(case=name):
                value = configuration()
                mutate(value)
                # A spent reservation escalates the controller, so each case needs its own ledger.
                outcome = harness.dispatch(self.fresh_ledger("ledger-" + name), value, self.router,
                                           options(), self.project, self.base / name)
                self.assertEqual(outcome["status"], "HARNESS_UNAVAILABLE")
                self.assertRegex(outcome["reason"], expected)
                self.assertFalse(outcome["prepared"])
                self.assertTrue(outcome["attempt_closed"])
                state = harness.feedback.replay(self.base / ("ledger-" + name))[0]
                self.assertIsNone(state["pending"], "a spent reservation must not be left pending")
                self.assertEqual(state["status"], "NEEDS_ARCHITECT")
                self.assertEqual(state["attempts"][-1]["result"]["outcome"], "PROVIDER_UNAVAILABLE")
                self.assertFalse((self.base / name / "brief.json").exists())

    def test_dispatch_measures_the_brief_against_the_window_the_worker_is_served(self):
        prepared = self.prepare()
        estimate = prepared["context_estimate"]
        # The router checked the architect's declared tokens against the declared window. This
        # accounts for what the harness itself adds, which the router cannot see.
        self.assertEqual(estimate["declared_context_window"], 100000)
        self.assertEqual(estimate["served_context_window"], 100000, "no served override was configured")
        self.assertEqual(estimate["harness_overhead_tokens"],
                         next(item["context_overhead_tokens"] for item in self.config["harnesses"]
                              if item["id"] == "cline-cli"))
        self.assertEqual(estimate["reserved_output_tokens"], options()["output_tokens"])
        divisor = harness.router.dec(self.config["limits"]["chars_per_token"])
        text = (Path(prepared["destination"]) / "brief.json").read_text(encoding="utf-8")
        rules = (Path(prepared["destination"]) / "BOUNDED_WORKER_RULES.md").read_text(encoding="utf-8")
        for chars, key in ((len(text), "brief_tokens"), (len(rules), "rules_tokens")):
            self.assertGreaterEqual(harness.router.dec(estimate[key]) * divisor, chars,
                                    "the estimate must not understate the material handed over")
        self.assertEqual(estimate["required_tokens"],
                         estimate["harness_overhead_tokens"] + estimate["brief_tokens"]
                         + estimate["rules_tokens"] + estimate["reserved_output_tokens"]
                         + estimate["growth_reserve_tokens"])
        self.assertEqual(estimate["headroom_tokens"],
                         estimate["served_context_window"] - estimate["required_tokens"])
        self.assertGreater(estimate["headroom_tokens"], 0)

    def test_a_binding_overstating_its_window_is_refused_before_a_reservation_is_spent(self):
        value = configuration()
        value["bindings"][0].update(served_context_window=200000)
        with self.assertRaisesRegex(ValueError, "more than the 100000 it declares"):
            harness.dispatch(self.ledger, value, self.router, options(), self.project, self.base / "overstated")
        # A configuration contradiction needs no attempt to detect, so it must not cost one.
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"], [])
        self.assertFalse((self.base / "overstated").exists(), "no run directory for a refused dispatch")

    def test_a_refused_reservation_leaves_no_run_directory_to_block_a_retry(self):
        blocked = self.fresh_ledger("ledger-held")
        # An approval anchor that no longer matches this task's INIT holds the reservation.
        with mock.patch.object(harness.feedback, "active_anchor", return_value="0" * 64):
            outcome = harness.dispatch(blocked, self.config, self.router, options(), self.project,
                                       self.base / "held")
        self.assertEqual(outcome["status"], "NEEDS_DECISION")
        self.assertFalse(outcome["prepared"])
        self.assertFalse((self.base / "held").exists(),
                         "a directory created for an attempt that never existed would block the retry")

    def test_capacity_check_reserves_room_for_the_run_growing_past_its_first_prompt(self):
        prepared = self.prepare()
        estimate = prepared["context_estimate"]
        reserve = self.config["limits"]["context_growth_reserve_tokens"]
        self.assertGreater(reserve, 0, "the committed example must reserve room for observed growth")
        self.assertEqual(estimate["growth_reserve_tokens"], reserve)
        self.assertIn(reserve, [estimate["required_tokens"] - sum(
            estimate[key] for key in ("harness_overhead_tokens", "brief_tokens", "rules_tokens",
                                      "reserved_output_tokens"))])
        # A window that fits the opening prompt but not the run is refused, not dispatched.
        value = configuration()
        opening = estimate["required_tokens"] - reserve
        value["bindings"][0].update(served_context_window=opening + 1)
        outcome = harness.dispatch(self.fresh_ledger("ledger-growth"), value, self.router, options(),
                                   self.project, self.base / "growth")
        self.assertEqual(outcome["status"], "HARNESS_UNAVAILABLE")
        self.assertRegex(outcome["reason"], "declared growth reserve")

    def test_the_brief_bound_measures_the_file_the_worker_is_handed(self):
        value = configuration()
        prepared = harness.dispatch(self.fresh_ledger("ledger-size"), value, self.router, options(),
                                    self.project, self.base / "sized")
        delivered = (Path(prepared["destination"]) / "brief.json").read_text(encoding="utf-8")
        # The readable file is larger than the canonical form, so a bound that measured only the
        # canonical form would let an oversize brief reach the worker.
        self.assertGreater(len(delivered), prepared["brief_chars"])
        value = configuration()
        value["limits"]["brief_max_chars"] = len(delivered) - 1
        outcome = harness.dispatch(self.fresh_ledger("ledger-tight"), value, self.router, options(),
                                   self.project, self.base / "tight")
        self.assertEqual(outcome["status"], "HARNESS_UNAVAILABLE")
        self.assertRegex(outcome["reason"], "exceeds its configured bound")

    def test_the_brief_field_set_is_declared_once(self):
        prepared = self.prepare()
        document = wp.read_json(Path(prepared["destination"]) / "brief.json")
        self.assertEqual(set(document), harness.BRIEF_FIELDS)
        harness.feedback.exact(document, harness.BRIEF_FIELDS)

    def test_a_second_dispatch_cannot_reserve_while_one_attempt_is_pending(self):
        prepared = self.prepare()
        self.assertEqual(prepared["status"], "PREPARED")
        with self.assertRaisesRegex(ValueError, "pending dispatch"):
            self.prepare("run-2")

    def test_reused_destination_is_refused_so_evidence_is_never_overwritten(self):
        prepared = self.prepare()
        with self.assertRaises(FileExistsError):
            harness.dispatch(self.ledger, self.config, self.router, options(), self.project,
                             Path(prepared["destination"]))


class HarnessReportTests(HarnessBase):
    def report(self, prepared, **changes):
        value = result({"dispatch_id": prepared["dispatch_id"]}, self.packet, **changes)
        path = Path(prepared["destination"]) / "report.json"
        wp.write_new(path, json.dumps(value, indent=2))
        return value, path

    def test_failed_attempt_is_recorded_with_preserved_evidence_for_the_next_tier(self):
        prepared = self.prepare()
        _, path = self.report(prepared, outcome="FAIL", passed=False)
        ingested = harness.ingest(self.ledger, self.config, path)
        self.assertEqual(ingested["outcome"], "FAIL")
        self.assertTrue(ingested["evidence_preserved"])
        self.assertFalse(ingested["independent_acceptance"])
        self.assertEqual(ingested["attempts_used"], 1)
        state = harness.feedback.replay(self.ledger)[0]
        self.assertIsNone(state["pending"])
        self.assertTrue(state["attempts"][-1]["fingerprint"])
        # The preserved failure reaches the next worker brief rather than being rebuilt.
        following = self.prepare("run-next")
        brief = wp.read_json(Path(following["destination"]) / "brief.json")
        self.assertEqual(len(brief["prior_failures"]), 1)
        self.assertEqual(brief["prior_failures"][0]["fingerprint"], state["attempts"][-1]["fingerprint"])

    def test_report_must_match_its_dispatch_contract_and_carry_no_credentials(self):
        prepared = self.prepare()
        contract = wp.current(self.packet)["contract"]
        for mutate, expected in (
            (lambda r: r.update(dispatch_id="f" * 64), "does not match the reserved dispatch"),
            (lambda r: r["validation"].append({**r["validation"][0], "check_id": "invented-check"}),
             "and no other id"),
            (lambda r: r["validation"].clear(), "Report every contract validation check"),
            (lambda r: r.update(evidence=[]), "requires evidence"),
            (lambda r: r.update(outcome="PASS"), "PASS requires every validation check to pass"),
            (lambda r: r.update(extra_field="widened"), "Expected fields"),
            (lambda r: r.update(cost_evidence="api_key: sk-abcdefghijklmnopqrstuvwxyz"), "credential-like"),
        ):
            with self.subTest(expected=expected):
                value = result({"dispatch_id": prepared["dispatch_id"]}, self.packet)
                mutate(value)
                with self.assertRaisesRegex(ValueError, expected):
                    harness.report_valid(value, contract, prepared["dispatch_id"],
                                         self.config["limits"], len(json.dumps(value)))
        oversize = configuration()
        oversize["limits"]["report_max_bytes"] = 200
        _, path = self.report(prepared)
        with self.assertRaisesRegex(ValueError, "Worker report exceeds"):
            harness.ingest(self.ledger, oversize, path)

    def test_a_worker_cannot_claim_pass_while_reporting_scope_or_architecture_problems(self):
        prepared = self.prepare()
        contract = wp.current(self.packet)["contract"]
        for field, value in (("scope_status", "violated"), ("scope_status", "unknown"),
                             ("architecture_conflict", True)):
            with self.subTest(field=field, value=value):
                report = result({"dispatch_id": prepared["dispatch_id"]}, self.packet,
                                outcome="PASS", passed=True)
                report[field] = value
                with self.assertRaises(ValueError):
                    harness.report_valid(report, contract, prepared["dispatch_id"],
                                         self.config["limits"], len(json.dumps(report)))

    def test_verify_report_checks_a_run_without_recording_or_accepting_it(self):
        prepared = self.prepare()
        brief_path = Path(prepared["destination"]) / "brief.json"
        _, path = self.report(prepared, outcome="PASS", passed=True)
        verified = harness.verify_report(self.config, brief_path, path)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["outcome"], "PASS")
        self.assertEqual(verified["checks_passed"], verified["checks_total"])
        self.assertFalse(verified["recorded_in_ledger"])
        self.assertFalse(verified["independent_acceptance"])
        # Verification must not touch the ledger, so the attempt is still pending.
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        # It applies the same report contract as ingestion.
        broken = wp.read_json(path)
        broken["validation"][0]["check_id"] = "invented-check"
        wp.write_new(Path(prepared["destination"]) / "broken.json", json.dumps(broken))
        with self.assertRaisesRegex(ValueError, "and no other id"):
            harness.verify_report(self.config, brief_path, Path(prepared["destination"]) / "broken.json")
        # A brief that is not a harness brief is refused rather than trusted.
        wp.write_new(Path(prepared["destination"]) / "not-a-brief.json", json.dumps({"contract": {}}))
        with self.assertRaisesRegex(ValueError, "Expected fields"):
            harness.verify_report(self.config, Path(prepared["destination"]) / "not-a-brief.json", path)

    def test_report_verification_retains_legacy_briefs_and_requires_startup_for_new_briefs(self):
        prepared = self.prepare()
        brief_path = Path(prepared["destination"]) / "brief.json"
        document = wp.read_json(brief_path)
        _, report_path = self.report(prepared, outcome="PASS", passed=True)
        legacy = copy.deepcopy(document)
        legacy["schema_version"] = "1.0"
        legacy.pop("startup")
        legacy_path = self.base / "legacy-brief.json"
        wp.write_new(legacy_path, json.dumps(legacy))
        self.assertTrue(harness.verify_report(self.config, legacy_path, report_path)["valid"])
        for name, value in (
            ("missing", {key: value for key, value in document.items() if key != "startup"}),
            ("empty", {**document, "startup": {}}),
            ("wrong-role", {**document, "startup": {**document["startup"], "role": "reviewer"}}),
            ("unknown-version", {**document, "schema_version": "9.9"}),
            ("legacy-extra", {**document, "schema_version": "1.0"}),
        ):
            with self.subTest(case=name):
                path = self.base / (name + "-brief.json")
                wp.write_new(path, json.dumps(value))
                with self.assertRaises(ValueError):
                    harness.verify_report(self.config, path, report_path)

    def test_report_verification_refuses_malformed_or_changed_startup_snapshots(self):
        prepared = self.prepare()
        document = wp.read_json(Path(prepared["destination"]) / "brief.json")
        _, report_path = self.report(prepared, outcome="PASS", passed=True)

        def change_content(startup, content):
            startup["documents"][0]["content_lines"] = [content]
            startup["documents"][0]["sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()

        for name, mutate in (
            ("null-steps", lambda s: s.update(steps=[None])),
            ("blank-steps", lambda s: s.update(steps=[" "])),
            ("null-documents", lambda s: s.update(documents=[None])),
            ("extra-bundle-field", lambda s: s.update(unknown=True)),
            ("extra-record-field", lambda s: s["documents"][0].update(unknown=True)),
            ("unknown-source", lambda s: s["documents"][0].update(source="untrusted")),
            ("unsafe-path", lambda s: s["documents"][0].update(path=".. /outside.md")),
            ("null-content", lambda s: s["documents"][0].update(content_lines=[None])),
            ("blank-content", lambda s: change_content(s, " \n")),
            ("changed-digest", lambda s: s["documents"][0].update(sha256="0" * 64)),
            ("changed-content", lambda s: s["documents"][0].update(content_lines=["Changed without a new hash"])),
            ("missing-canonical", lambda s: s["documents"].pop(0)),
            ("wrong-order", lambda s: s["documents"].insert(0, s["documents"].pop(1))),
            ("missing-worker-rules", lambda s: s["documents"].pop()),
            ("duplicate-document", lambda s: s["documents"].insert(-1, copy.deepcopy(s["documents"][0]))),
            ("credential-content", lambda s: change_content(s, "api_key: sk-abcdefghijklmnopqrstuvwxyz")),
            ("oversized-content", lambda s: change_content(s, "x" * (self.config["limits"]["brief_max_chars"] + 1))),
        ):
            with self.subTest(case=name):
                broken = copy.deepcopy(document)
                mutate(broken["startup"])
                brief_path = self.base / (name + ".json")
                wp.write_new(brief_path, json.dumps(broken))
                with self.assertRaises(ValueError):
                    harness.verify_report(self.config, brief_path, report_path)

    def test_a_worker_that_writes_nothing_does_not_strand_the_attempt(self):
        prepared = self.prepare()
        missing = Path(prepared["destination"]) / "report.json"
        self.assertFalse(missing.exists())
        # Absence is refused rather than inferred, and the reservation is still pending.
        with self.assertRaisesRegex(ValueError, "record the attempt with abandon"):
            harness.ingest(self.ledger, self.config, missing)
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        for reason, expected in (("too short", "requires a specific recorded reason"),
                                 ("api_key: sk-abcdefghijklmnopqrstuvwxyz0123", "credential-like")):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, expected):
                    harness.abandon(self.ledger, self.config, reason)
        closed = harness.abandon(self.ledger, self.config,
                                 "The local worker narrated tool calls as prose, never read the brief and wrote no report.")
        self.assertEqual(closed["outcome"], "FAIL")
        self.assertTrue(closed["evidence_preserved"])
        self.assertTrue(closed["fingerprint"])
        state = harness.feedback.replay(self.ledger)[0]
        self.assertIsNone(state["pending"], "an abandoned attempt must not stay pending")
        self.assertIn("attempt-abandoned", state["attempts"][-1]["result"]["evidence"][0])
        with self.assertRaisesRegex(ValueError, "No reserved dispatch"):
            harness.abandon(self.ledger, self.config, "Nothing is pending, so there is nothing to abandon here.")
        # Scope is genuinely unknown when nothing was reported, so the architect decides rather than
        # the controller looping a worker that may be structurally unable to complete the packet.
        self.assertEqual(closed["status"], "NEEDS_ARCHITECT")
        self.assertEqual(state["status"], "NEEDS_ARCHITECT")
        with self.assertRaisesRegex(ValueError, "Controller hold"):
            self.prepare("run-after-abandon")
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"][-1]["result"]["scope_status"], "unknown")

    def test_a_refused_malformed_report_can_also_be_abandoned(self):
        prepared = self.prepare()
        broken = Path(prepared["destination"]) / "report.json"
        wp.write_new(broken, json.dumps({"validation": "not even the right shape"}))
        with self.assertRaises(ValueError):
            harness.ingest(self.ledger, self.config, broken)
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        closed = harness.abandon(self.ledger, self.config,
                                 "The worker wrote a report that does not match the required field set.")
        self.assertEqual(closed["outcome"], "FAIL")
        self.assertIsNone(harness.feedback.replay(self.ledger)[0]["pending"])

    def test_ingest_requires_a_reserved_dispatch(self):
        _, path = self.report({"dispatch_id": "a" * 64, "destination": str(self.base)})
        with self.assertRaisesRegex(ValueError, "No reserved dispatch"):
            harness.ingest(self.ledger, self.config, path)


if __name__ == "__main__":
    unittest.main()
