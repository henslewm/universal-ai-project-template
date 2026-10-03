"""CLI exit codes (ADR-072) and Ctrl+C handling (#31, #32) for every scripts/*.py command line.

README.md, "CLI exit codes", is the table these tests hold the commands to. Nothing here
reclassifies an outcome: each case pins the code a command already returned.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from test_acceptance import (ARCHITECT, CONTROLLER, IMPLEMENTERS, AcceptanceBase, acceptance, make_artifact,
                             make_result, process_alive)
from test_acceptance import make_packet as review_packet
from test_bootstrap_integration import answers
from test_execution_harness import configuration as harness_configuration
from test_feedback import ANCHOR, active_project, options, policy, timestamp
from test_model_router import config as router_config
from test_model_router import make_packet as ready_packet
from test_model_router import request as routing_request
from test_model_router import resource

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cli_exit  # noqa: E402

feedback = acceptance.feedback
harness = acceptance.harness
wp = acceptance.wp
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
# A check that stays busy and leaves a descendant, recording both pids once both exist.
HOLDING_CHECK = ("import os, subprocess, sys, time\n"
                 "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                 "open('pids.part', 'w').write(f'{os.getpid()} {child.pid}')\n"
                 "os.replace('pids.part', 'pids')\n"
                 "time.sleep(120)")
# Runs a script's real `__main__` block and interrupts the main thread, as Ctrl+C does, once
# `marker` exists. Only the controller is interrupted, so the check must be ended by its owner.
INTERRUPTING_RUNNER = ("import _thread, runpy, sys, threading, time\n"
                       "from pathlib import Path\n"
                       "marker, script, *argv = sys.argv[1:]\n"
                       "def watch():\n"
                       "    deadline = time.monotonic() + 60\n"
                       "    while not Path(marker).exists() and time.monotonic() < deadline:\n"
                       "        time.sleep(0.05)\n"
                       "    _thread.interrupt_main()\n"
                       "threading.Thread(target=watch, daemon=True).start()\n"
                       "sys.path.insert(0, str(Path(script).parent))\n"
                       "sys.argv = [script, *argv]\n"
                       "runpy.run_path(script, run_name='__main__')\n")

# Runs a script's real `__main__` path and delivers Ctrl+C at the first module import once
# `cli_exit` starts loading, i.e. while the CLI is still loading, before `cli_exit.run` is reached.
STARTUP_RUNNER = ("import runpy, sys\n"
                  "from pathlib import Path\n"
                  "script, *argv = sys.argv[1:]\n"
                  "class Interrupt:\n"
                  "    def find_spec(self, name, path=None, target=None):\n"
                  "        if 'cli_exit' in sys.modules:\n"
                  "            sys.meta_path.remove(self)\n"
                  "            raise KeyboardInterrupt\n"
                  "        return None\n"
                  "sys.meta_path.insert(0, Interrupt())\n"
                  "sys.path.insert(0, str(Path(script).parent))\n"
                  "sys.argv = [script, *argv]\n"
                  "runpy.run_path(script, run_name='__main__')\n")


def cli(script, *args, cwd=None):
    path = script if isinstance(script, Path) else SCRIPTS / script
    return subprocess.run([sys.executable, str(path), *map(str, args)], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", timeout=120, env=ENV)


def entry_points():
    """Every scripts/*.py command line: a module that defines `main()`; the rest are libraries."""
    return [path for path in sorted(SCRIPTS.glob("*.py"))
            if any(isinstance(node, ast.FunctionDef) and node.name == "main"
                   for node in ast.parse(path.read_text(encoding="utf-8")).body)]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return path


def reap(pids):
    """Test cleanup only: end anything a failing run left behind."""
    for pid in pids:
        with contextlib.suppress(OSError):
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
            else:
                os.kill(pid, signal.SIGKILL)


def default_sigint_or_skip(test):
    if signal.getsignal(signal.SIGINT) is not signal.default_int_handler:
        test.skipTest("the test runner replaced Python's SIGINT handler")


class CliAssertions:
    def expect(self, completed, code, key=None, value=None):
        detail = f"exit {completed.returncode}\nstdout: {completed.stdout}\nstderr: {completed.stderr}"
        self.assertEqual(completed.returncode, code, detail)
        self.assertNotIn("Traceback", completed.stderr, detail)
        if key is not None:
            self.assertEqual(json.loads(completed.stdout)[key], value, detail)
        return completed

    def usage(self, completed):
        """Exit 2 from argparse: a usage message on stderr and nothing on stdout."""
        self.expect(completed, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("usage:", completed.stderr)
        return completed


class SharedWrapperTests(unittest.TestCase):
    def setUp(self):
        default_sigint_or_skip(self)

    def test_run_passes_the_exit_code_through_and_maps_ctrl_c_to_130_without_a_traceback(self):
        self.assertEqual(cli_exit.run(lambda: 2), 2)
        self.assertEqual(cli_exit.run(lambda code: code, 1), 1)

        def interrupted():
            raise KeyboardInterrupt

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(cli_exit.run(interrupted), cli_exit.INTERRUPTED)
        self.assertEqual(cli_exit.INTERRUPTED, 130)
        self.assertIn("Interrupted", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

        def usage_error():
            raise SystemExit(2)

        def failure():
            raise ValueError("not an interrupt")

        with self.assertRaises(SystemExit):
            cli_exit.run(usage_error)
        with self.assertRaises(ValueError):
            cli_exit.run(failure)

    def test_a_held_interrupt_is_raised_only_after_the_block_completes(self):
        finished = []
        with self.assertRaises(KeyboardInterrupt):
            with cli_exit.interrupts_held() as held:
                signal.raise_signal(signal.SIGINT)
                finished.append(True)
        self.assertEqual(finished, [True])
        self.assertEqual(held, [signal.SIGINT])
        self.assertIs(signal.getsignal(signal.SIGINT), signal.default_int_handler)

    def test_a_refusal_inside_the_block_is_never_masked_by_a_held_interrupt(self):
        with self.assertRaisesRegex(ValueError, "refused inside"):
            with cli_exit.interrupts_held():
                signal.raise_signal(signal.SIGINT)
                raise ValueError("refused inside the held block")
        self.assertIs(signal.getsignal(signal.SIGINT), signal.default_int_handler)

    def test_an_ignored_or_replaced_sigint_and_other_threads_are_left_alone(self):
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            with cli_exit.interrupts_held() as held:
                signal.raise_signal(signal.SIGINT)
            self.assertEqual(held, [])
            self.assertIs(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
        finally:
            signal.signal(signal.SIGINT, previous)
        seen = []

        def elsewhere():
            with cli_exit.interrupts_held() as held_there:
                seen.append((signal.getsignal(signal.SIGINT), held_there))

        worker = threading.Thread(target=elsewhere)
        worker.start()
        worker.join()
        self.assertEqual(seen, [(signal.default_int_handler, [])])

    def test_ctrl_c_while_a_cli_is_still_importing_also_exits_130_without_a_traceback(self):
        # Codex P2 on PR #71, rounds 4 and 5: an interrupt during a CLI's module imports, or
        # during the import of `cli_exit` itself, arrived before any handler and printed a traceback.
        for path in entry_points():
            with self.subTest(script=path.name):
                completed = subprocess.run([sys.executable, "-c", STARTUP_RUNNER, str(path)], capture_output=True,
                                           text=True, encoding="utf-8", timeout=120, env=ENV)
                self.assertEqual(completed.returncode, cli_exit.INTERRUPTED, completed.stdout + completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertIn("Interrupted", completed.stderr)

    def test_the_startup_guard_needs_nothing_the_interpreter_has_not_already_loaded(self):
        # Codex P2 on PR #71, rounds 5 and 6: importing `cli_exit` loaded contextlib, threading
        # and (under `python -S`) os before the guard existed. Only `sys`, always loaded, may be.
        module = ast.parse((SCRIPTS / "cli_exit.py").read_text(encoding="utf-8"))
        imported = {alias.name for node in module.body if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in node.names} | {node.module for node in module.body if isinstance(node, ast.ImportFrom)}
        self.assertLessEqual(imported, {"annotations", "__future__", "sys"})

    def test_interrupt_reporting_never_changes_the_exit_code(self):
        # Codex P2 on PR #71, round 5: with stderr closed, the report raised and the CLI exited 1.
        def interrupted():
            raise KeyboardInterrupt

        closed = io.StringIO()
        closed.close()
        with contextlib.redirect_stderr(closed):
            self.assertEqual(cli_exit.run(interrupted), cli_exit.INTERRUPTED)
        previous = sys.excepthook
        self.addCleanup(setattr, sys, "excepthook", previous)
        cli_exit.guard_startup()
        with contextlib.redirect_stderr(closed), \
                mock.patch.object(os, "_exit", side_effect=SystemExit) as exited:
            with self.assertRaises(SystemExit):
                sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        exited.assert_called_once_with(cli_exit.INTERRUPTED)

    def test_every_cli_entry_point_goes_through_the_shared_wrapper(self):
        guarded = {}
        for path in sorted(SCRIPTS.glob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"))
            guards = [node for node in module.body if isinstance(node, ast.If)
                      and ast.unparse(node.test) in ("__name__ == '__main__'", '__name__ == "__main__"')]
            if guards:
                guarded[path.name] = [ast.unparse(guard) for guard in guards]
        # Every command line is guarded; a module without one is a library (cli_exit, progress).
        self.assertEqual(sorted(guarded), sorted(path.name for path in entry_points()))
        self.assertGreaterEqual(len(guarded), 12)
        for name, guards in guarded.items():
            with self.subTest(script=name):
                # The first statement after the future import guards startup; the last runs main.
                module = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
                self.assertEqual(ast.unparse(module.body[2]), guards[0])
                self.assertIn("cli_exit.guard_startup()", guards[0])
                self.assertIn("cli_exit.run(main)", guards[-1])


class ExitCodeTableTests(CliAssertions, unittest.TestCase):
    """Each CLI's documented codes; the domain stops are the ones ADR-072 keeps on 2."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_acceptance(self):
        config = ROOT / "config/acceptance.example.json"
        self.expect(cli("acceptance.py", "--config", config, "validate-config"), 0, "valid", True)
        self.usage(cli("acceptance.py", "validate-config"))
        refused = self.expect(cli("acceptance.py", "--config", self.directory / "absent.json", "validate-config"), 1)
        self.assertIn("Acceptance refused", refused.stderr)

    def test_bootstrap_project_gate_and_validators(self):
        intake = write_json(self.directory / "answers.json", answers("software-hardware"))
        generated = self.directory / "generated"
        self.expect(cli("bootstrap_project.py", "--answers", intake, "--destination", generated, "--no-git"), 0)
        self.usage(cli("bootstrap_project.py", "--answers", intake))
        self.usage(cli("bootstrap_project.py", "--destination", self.directory / "no-intake"))
        refused = self.expect(cli("bootstrap_project.py", "--answers", intake, "--destination",
                                  self.directory / "elsewhere", "--template-root", self.directory), 1)
        self.assertIn("Not a recognized template root", refused.stderr)

        state = generated / "config/bootstrap.json"
        self.expect(cli("validate_bootstrap.py", state), 0)
        self.expect(cli("validate_bootstrap.py", state, "--require-active"), 1)
        self.expect(cli("validate_bootstrap.py", ROOT / "config/bootstrap.example.json", "--require-active"), 1)
        for arguments in ((self.directory / "absent.json",), (self.directory / "config/bootstrap.json", "--require-active")):
            unreadable = self.expect(cli("validate_bootstrap.py", *arguments), 2)
            self.assertTrue(unreadable.stdout.startswith("BOOTSTRAP INVALID:"), unreadable.stdout)
        self.usage(cli("validate_bootstrap.py", "--unknown-flag"))

        self.expect(cli(generated / "scripts/validate_project.py"), 0)
        self.expect(cli("bootstrap_gate.py", "review", "--root", generated), 0)
        blocked = self.expect(cli("bootstrap_gate.py", "review", "--root", self.directory / "no-project"), 1)
        self.assertIn("BOOTSTRAP BLOCKED", blocked.stdout)
        self.usage(cli("bootstrap_gate.py", "publish"))

    def test_validate_project_and_sync_skills_on_disposable_trees(self):
        broken = self.directory / "broken" / "scripts"
        broken.mkdir(parents=True)
        for name in ("validate_project.py", "validate_bootstrap.py", "cli_exit.py"):
            shutil.copyfile(SCRIPTS / name, broken / name)
        failed = self.expect(cli(broken / "validate_project.py"), 1)
        self.assertIn("VALIDATION FAILED", failed.stdout)

        tree = self.directory / "tree"
        (tree / "scripts").mkdir(parents=True)
        for name in ("sync_skills.py", "cli_exit.py", "bootstrap_project.py", "bootstrap_gate.py",
                     "validate_bootstrap.py", "validate_project.py"):
            shutil.copyfile(SCRIPTS / name, tree / "scripts" / name)
        (tree / "skills/complex-project-bootstrapper").mkdir(parents=True)
        (tree / "skills/complex-project-bootstrapper/SKILL.md").write_text("# Synthetic skill\n", encoding="utf-8")
        sync = tree / "scripts/sync_skills.py"
        self.usage(cli(sync, "--unknown-flag"))
        drift = self.expect(cli(sync, "--check"), 1)
        self.assertIn("BOOTSTRAP PAYLOAD DRIFT", drift.stdout)
        self.expect(cli(sync), 0)
        self.expect(cli(sync, "--check"), 0)

    def test_work_packet_and_domain_tools(self):
        packet = write_json(self.directory / "packet.json", ready_packet())
        self.expect(cli("work_packet.py", "validate", packet), 0)
        self.usage(cli("work_packet.py"))
        refused = self.expect(cli("work_packet.py", "validate", self.directory / "absent.json"), 1)
        self.assertIn("WORK PACKET INVALID", refused.stderr)
        for script, profile in (("software_hardware.py", "software-hardware"),):
            with self.subTest(script=script):
                example = ROOT / f"examples/work-packets/{profile}.contract.json"
                self.expect(cli(script, "validate-contract", example), 0, "valid", True)
                self.usage(cli(script))
                refused = self.expect(cli(script, "validate-contract", self.directory / "absent.json"), 1)
                self.assertIn("Domain rule refused", refused.stderr)

    def test_hash_file(self):
        self.expect(cli("hash_file.py", ROOT / "README.md"), 0)
        self.usage(cli("hash_file.py"))
        not_a_file = self.usage(cli("hash_file.py", self.directory))
        self.assertIn("Not a file", not_a_file.stderr)

    def test_model_router(self):
        example = ROOT / "config/model-router.example.json"
        self.expect(cli("model_router.py", "validate-config", example), 0)
        self.usage(cli("model_router.py", "route"))
        refused = self.expect(cli("model_router.py", "validate-config", self.directory / "absent.json"), 1)
        self.assertIn("Model routing failed", refused.stderr)
        packet = ready_packet()
        stopped = router_config(resource())
        stopped["resources"][0]["enabled"] = False
        self.expect(cli("model_router.py", "route", write_json(self.directory / "packet.json", packet),
                        "--config", write_json(self.directory / "router.json", stopped),
                        "--request", write_json(self.directory / "request.json", routing_request(packet)),
                        "--output", self.directory / "record.json"), 2, "status", "STOP")


class ControllerExitCodeTests(CliAssertions, AcceptanceBase):
    """Feedback, harness and acceptance holds on real ledgers under an approved synthetic project."""

    def setUp(self):
        super().setUp()
        self.router = router_config(resource())
        stopped = copy.deepcopy(self.router)
        stopped["resources"][0]["enabled"] = False
        self.routed = write_json(self.directory / "router.json", self.router)
        self.stopped = write_json(self.directory / "stopped-router.json", stopped)
        self.options = write_json(self.directory / "options.json", options())
        self.harness = write_json(self.directory / "harness.json", harness_configuration())
        self.packet = ready_packet()

    def project(self, name):
        root = self.directory / name
        active_project(root)
        for document in harness.GOVERNANCE_DOCUMENTS:
            if not (root / document).exists():
                (root / document).write_text(f"# Synthetic governance: {document}\n", encoding="utf-8")
        return root

    def feedback_ledger(self, name, root):
        path = self.directory / name
        feedback.initialize(path, self.packet, [self.packet], policy(), self.router, root,
                            "Synthetic architect", timestamp())
        return path

    def test_feedback(self):
        root = self.project("project")
        held = self.feedback_ledger("held", root)
        self.expect(cli("feedback.py", "status", held), 0, "status", "READY")
        self.usage(cli("feedback.py"))
        refused = self.expect(cli("feedback.py", "status", self.directory / "absent"), 1)
        self.assertIn("Feedback control refused", refused.stderr)
        self.expect(cli("feedback.py", "next", held, "--config", self.stopped, "--options", self.options,
                        "--root", root), 2, "status", "BLOCKED")
        self.expect(cli("feedback.py", "next", self.feedback_ledger("dispatched", root), "--config", self.routed,
                        "--options", self.options, "--root", root), 0, "status", "DISPATCH")

    def test_execution_harness(self):
        self.expect(cli("execution_harness.py", "--config", ROOT / "config/execution-harness.example.json",
                        "validate-config"), 0, "valid", True)
        self.usage(cli("execution_harness.py", "validate-config"))
        refused = self.expect(cli("execution_harness.py", "--config", self.directory / "absent.json",
                                  "validate-config"), 1)
        self.assertIn("Execution harness refused", refused.stderr)
        root = self.project("project")
        self.expect(cli("execution_harness.py", "--config", self.harness, "--root", root, "dispatch",
                        self.feedback_ledger("blocked", root), self.directory / "run-blocked",
                        "--router-config", self.stopped, "--request", self.options), 2, "status", "BLOCKED")
        # Only BLOCKED exits 2 here; every other hold is reported in `status` with exit 0 (ADR-072
        # reclassifies nothing), which is why callers read `status` rather than the code alone.
        revoked = self.project("revoked")
        ledger = self.feedback_ledger("revoked-ledger", revoked)
        (revoked / "CONNECTOR_PLAN.md").write_text("# Changed after approval\n", encoding="utf-8")
        self.expect(cli("execution_harness.py", "--config", self.harness, "--root", revoked, "dispatch", ledger,
                        self.directory / "run-revoked", "--router-config", self.routed, "--request", self.options),
                    0, "status", "NEEDS_DECISION")

    def test_acceptance_terminal_statuses_exit_2_and_others_exit_0(self):
        config = ROOT / "config/acceptance.example.json"
        ledger, _ = self.start(risk="critical")
        self.expect(cli("acceptance.py", "--config", config, "status", ledger), 0, "status", "GATES_PENDING")
        self.checked(ledger)
        acceptance.append(ledger, "DECISION", {"decision": {"decider": "Synthetic user", "decision": "reject",
                                                            "reason": "Synthetic user rejection"}},
                          previous_state=acceptance.replay(ledger))
        self.expect(cli("acceptance.py", "--config", config, "status", ledger), 2, "status", "USER_REJECTED")


class InterruptTests(AcceptanceBase):
    """Ctrl+C during an active check: the owner ends the tree, then the CLI exits 130."""

    def setUp(self):
        super().setUp()
        default_sigint_or_skip(self)

    def holding_ledger(self):
        ledger, _ = self.start(argv=[sys.executable, "-c", HOLDING_CHECK])
        space = self.workspace()
        return ledger, space, sorted(path.read_bytes() for path in ledger.iterdir())

    def wait_for_pids(self, space, controller):
        deadline = time.monotonic() + 60
        while not (space / "pids").exists():
            if controller.poll() is not None or time.monotonic() > deadline:
                self.fail(f"the check never started: {controller.communicate()}")
            time.sleep(0.05)
        pids = [int(value) for value in (space / "pids").read_text().split()]
        self.addCleanup(reap, pids)
        return pids

    def assert_cancelled(self, controller, pids, ledger, before, started):
        stdout, stderr = controller.communicate(timeout=120)
        self.assertEqual(controller.returncode, 130, stdout + stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertIn("Interrupted", stderr)
        self.assertEqual(stdout, "")
        # Well inside the check's own 120-second life: the controller did not wait it out.
        self.assertLess(time.monotonic() - started, 60)
        for pid in pids:
            self.assertFalse(process_alive(pid), f"pid {pid} outlived a cancelled run")
        self.assertEqual(sorted(path.read_bytes() for path in ledger.iterdir()), before, "the ledger changed")
        self.assertIsNone(self.state(ledger)["checks"])
        self.assertEqual(self.state(ledger)["status"], "GATES_PENDING")

    def controller(self, *command):
        return subprocess.Popen([sys.executable, *map(str, command)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8", env=ENV)

    def run_checks_arguments(self, ledger, space):
        return (SCRIPTS / "acceptance.py", "--config", ROOT / "config/acceptance.example.json",
                "run-checks", ledger, "--workspace", space)

    def test_ctrl_c_during_an_active_check_stops_its_tree_and_exits_130_on_this_os(self):
        ledger, space, before = self.holding_ledger()
        started = time.monotonic()
        controller = self.controller("-c", INTERRUPTING_RUNNER, space / "pids",
                                     *self.run_checks_arguments(ledger, space))
        pids = self.wait_for_pids(space, controller)
        self.assert_cancelled(controller, pids, ledger, before, started)

    @unittest.skipIf(os.name == "nt", "a POSIX signal; the interrupt_main test covers Windows")
    def test_sigint_during_an_active_check_stops_its_tree_and_exits_130(self):
        ledger, space, before = self.holding_ledger()
        started = time.monotonic()
        controller = self.controller(*self.run_checks_arguments(ledger, space))
        pids = self.wait_for_pids(space, controller)
        os.kill(controller.pid, signal.SIGINT)
        self.assert_cancelled(controller, pids, ledger, before, started)

    @unittest.skipIf(os.name == "nt", "a POSIX signal at a prompt")
    def test_sigint_at_an_interactive_prompt_exits_130_and_writes_nothing(self):
        destination = self.directory / "never-created"
        process = subprocess.Popen([sys.executable, str(SCRIPTS / "bootstrap_project.py"), "--interactive",
                                    "--profile", "software-hardware", "--destination", str(destination), "--no-git"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        ready, _, _ = select.select([process.stdout], [], [], 60)
        self.assertTrue(ready and os.read(process.stdout.fileno(), 4096), "no intake prompt was shown")
        os.kill(process.pid, signal.SIGINT)
        _, stderr = process.communicate(timeout=60)
        stderr = stderr.decode("utf-8")
        self.assertEqual(process.returncode, 130, stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertFalse(destination.exists())

    def test_an_interrupt_while_a_check_launches_is_held_until_its_owner_can_end_it(self):
        ledger, space, _ = self.holding_ledger()
        real_launch = acceptance.ProcessTree.launch
        launched = []

        def launch(argv, cwd):
            process = real_launch(argv, cwd)
            launched.append(process.pid)
            self.addCleanup(reap, [process.pid])
            signal.raise_signal(signal.SIGINT)  # Ctrl+C arrives the instant the check exists.
            return process

        with mock.patch.object(acceptance.ProcessTree, "launch", side_effect=launch):
            with self.assertRaises(KeyboardInterrupt):
                acceptance.run_checks(ledger, space)
        self.assertEqual(len(launched), 1)
        self.assertFalse(process_alive(launched[0]), "a check launched as Ctrl+C arrived was left unowned")
        self.assertIsNone(self.state(ledger)["checks"])

    def test_an_interrupted_run_whose_tree_cannot_be_confirmed_stopped_refuses(self):
        ledger, space, _ = self.holding_ledger()
        real_wait = subprocess.Popen.wait

        def wait(process, timeout=None):
            if timeout is None:  # ProcessTree.kill() waits without a timeout; let it.
                return real_wait(process)
            signal.raise_signal(signal.SIGINT)
            return real_wait(process, timeout)

        with mock.patch.object(subprocess.Popen, "wait", wait), \
                mock.patch.object(acceptance.ProcessTree, "close", return_value=False):
            with self.assertRaises((ValueError, KeyboardInterrupt)) as raised:
                acceptance.run_checks(ledger, space)
        self.assertIsInstance(raised.exception, ValueError,
                              "an unconfirmed tree was reported as a clean cancellation")
        self.assertIn("could not be confirmed stopped", str(raised.exception))
        self.assertIsNone(self.state(ledger)["checks"])


    def test_a_ctrl_c_after_the_stop_check_never_reports_an_unconfirmed_tree_as_cancelled(self):
        # Codex P2 on PR #71, round 3: an interrupt arriving after the teardown's stop check had
        # passed, but before the held block exited, was re-raised as a clean cancellation (130)
        # although close() had not confirmed the tree stopped.
        ledger, _ = self.start()
        real_require = acceptance.require

        def require(condition, message):
            real_require(condition, message)
            if "confirmed stopped" in message:
                signal.raise_signal(signal.SIGINT)  # Ctrl+C lands just after the check passed.

        with mock.patch.object(acceptance.ProcessTree, "close", return_value=False), \
                mock.patch.object(acceptance, "require", require):
            with self.assertRaises((ValueError, KeyboardInterrupt)) as raised:
                acceptance.run_checks(ledger, self.workspace())
        self.assertIsInstance(raised.exception, ValueError,
                              "an unconfirmed tree was reported as a clean cancellation")
        self.assertIsNone(self.state(ledger)["checks"])


class InterruptingWriter:
    """A new record's stream on which Ctrl+C arrives just before the first write."""

    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stream.close()
        return False

    def write(self, text):
        signal.raise_signal(signal.SIGINT)
        return self.stream.write(text)

    def __getattr__(self, name):
        return getattr(self.stream, name)


class InterruptedWriteTests(AcceptanceBase):
    """Ctrl+C never leaves a ledger event or a new output file cut short (#31: preserve ledgers)."""

    def setUp(self):
        super().setUp()
        default_sigint_or_skip(self)
        real_open = Path.open

        def open_(path, mode="r", *args, **kwargs):
            stream = real_open(path, mode, *args, **kwargs)
            return InterruptingWriter(stream) if mode == "x" else stream

        self.interrupting = mock.patch.object(Path, "open", open_)

    def test_an_acceptance_event_is_written_whole(self):
        ledger, _ = self.start(risk="critical")
        self.checked(ledger)
        decision = {"decision": {"decider": "Synthetic user", "decision": "reject", "reason": "Synthetic"}}
        with self.interrupting, self.assertRaises(KeyboardInterrupt):
            acceptance.append(ledger, "DECISION", decision, previous_state=acceptance.replay(ledger))
        self.assertEqual(self.state(ledger)["status"], "USER_REJECTED")

    def test_a_feedback_event_is_written_whole(self):
        packet = ready_packet()
        ledger = self.directory / "feedback"
        with mock.patch.object(feedback, "active_anchor", return_value=ANCHOR):
            with self.interrupting, self.assertRaises(KeyboardInterrupt):
                feedback.initialize(ledger, packet, [packet], policy(), router_config(resource()), self.directory,
                                    "Synthetic architect", timestamp())
        self.assertEqual(feedback.replay(ledger)[0]["status"], "READY")

    def test_a_new_ledger_is_never_left_without_its_first_event(self):
        # Codex P2 on PR #71: Ctrl+C between creating the ledger directory and appending INIT left
        # an empty ledger that replay refuses and that blocks a retry (the directory exists).
        real_sync = feedback.sync_directory

        def sync(directory):
            if Path(directory) == self.directory:  # The parent sync, after mkdir and before INIT.
                signal.raise_signal(signal.SIGINT)
            return real_sync(directory)

        packet = ready_packet()
        ledger = self.directory / "feedback"
        with mock.patch.object(feedback, "active_anchor", return_value=ANCHOR), \
                mock.patch.object(feedback, "sync_directory", sync), self.assertRaises(KeyboardInterrupt):
            feedback.initialize(ledger, packet, [packet], policy(), router_config(resource()), self.directory,
                                "Synthetic architect", timestamp())
        self.assertEqual(feedback.replay(ledger)[0]["status"], "READY")
        packet = review_packet()
        ledger = self.directory / "acceptance"
        with mock.patch.object(feedback, "sync_directory", sync), self.assertRaises(KeyboardInterrupt):
            acceptance.initialize(ledger, self.config(), packet, make_result(packet), make_artifact(), CONTROLLER,
                                  ARCHITECT, IMPLEMENTERS, [])
        self.assertEqual(self.state(ledger)["status"], "GATES_PENDING")

    def test_a_new_output_file_is_written_whole(self):
        output = self.directory / "record.json"
        with self.interrupting, self.assertRaises(KeyboardInterrupt):
            wp.write_new(output, "complete record\n")
        self.assertEqual(output.read_text(encoding="utf-8"), "complete record\n")


if __name__ == "__main__":
    unittest.main()
