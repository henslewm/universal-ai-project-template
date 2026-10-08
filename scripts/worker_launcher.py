#!/usr/bin/env python3
"""Run one reserved, prepared worker attempt with a scoped provider environment (ADR-073, ADR-077).

Run explicitly by the architect session (ADR-096) or an operator: no script calls this, and it never writes the task ledger.
"""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import json
import os
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import acceptance
import cli_exit
import execution_harness as harness
import feedback
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
MARKER = "launch.json"
GUARD_STORE_SENTINEL = "LAUNCH_GUARD_STORE"
# Short waits keep Ctrl+C prompt on Windows, where a long process wait is not interruptible.
WAIT_SLICE_SECONDS = 0.2
EXIT_CODES = {"REPORT_WRITTEN": 0, "NO_REPORT": 2, "TIMED_OUT": 2, "INTERRUPTED": 130}
require = harness.require


def current_time():
    return datetime.now(timezone.utc)


def child_environment(names, source=None):
    """Exactly the named credential variables, read now; nothing else is inherited, not even PATH."""
    source = os.environ if source is None else source
    environment = {}
    for name in names:
        value = source.get(name)
        # Name the variable, never its value: this message reaches stderr.
        require(bool(value), f"Required credential variable {name} is not set in the launcher's environment")
        environment[name] = value
    return environment


def dispatch_record(directory, sequence, head, dispatch_id):
    """The ledger's DISPATCH data for the pending reservation, from the event replay just verified."""
    event = wp.read_json(Path(directory) / f"{sequence:08d}.json")
    claimed = event.pop("hash", None)
    require(claimed == head and feedback.router.digest(event) == head,
            "The feedback ledger changed while the launch was being checked")
    data = event["data"] if event.get("kind") == "DISPATCH" else {}
    require(isinstance(data.get("plan"), dict) and data["plan"]["routing"]["decision"]["decision_id"] == dispatch_id,
            "The pending reservation is not the ledger's latest dispatch")
    return data


def verify_prepared(rundir, expected):
    """The run directory still holds exactly the brief, rules and invocation the launcher verified."""
    require((rundir / "brief.json").read_bytes().decode("utf-8") == expected["brief"],
            "brief.json differs from what dispatch renders for this reservation, its binding and its startup sources")
    require((rundir / "BOUNDED_WORKER_RULES.md").read_bytes().decode("utf-8") == expected["rules"],
            "BOUNDED_WORKER_RULES.md differs from the bounded worker rules")
    require(wp.read_json(rundir / "invocation.json") == expected["invocation"],
            "invocation.json differs from what the current configuration prepares for this attempt")


def launch_guard(directory, dispatch_id):
    """The one-launch guard, beside the ledger: a path the worker is never given, so it lasts the whole run.

    The ledger is resolved first, so every alias of one ledger names the same guard."""
    directory = Path(directory).resolve()
    return directory.with_name(f".{directory.name}.launch-guards") / f"{dispatch_id}.json"


def guard_store(guard):
    """Create or accept the guard's directory only when it is this launcher's own store, never another ledger."""
    store = guard.parent
    try:
        store.mkdir()
    except FileExistsError:
        pass
    else:
        create_exclusive(store / GUARD_STORE_SENTINEL, "Launch guards written by scripts/worker_launcher.py.\n")
    sentinel = store / GUARD_STORE_SENTINEL
    require(store.is_dir() and not store.is_symlink() and sentinel.is_file() and not sentinel.is_symlink(),
            f"{store} exists but is not a launch guard store; move it aside before launching")


def create_exclusive(path, text):
    """Create path exclusively with text; a failed write removes the partial file this call created."""
    path = Path(path)
    stream = path.open("xb")
    try:
        with stream:
            stream.write(text.encode("utf-8"))
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def marker_intact(marker, record):
    """The marker is still the regular file holding record; a FIFO or other special file is never opened."""
    expected = record.encode("utf-8")
    try:
        info = os.lstat(marker)
        return stat.S_ISREG(info.st_mode) and info.st_size == len(expected) and marker.read_bytes() == expected
    except OSError:
        return False


def require_unreported(rundir):
    require(not os.path.lexists(rundir / "report.json"),
            "The run directory already holds report.json; ingest it instead of launching again")


def remaining_seconds(deadline):
    """Seconds left before the reservation's absolute deadline in the ledger; refuses once it passed."""
    remaining = (feedback.instant(deadline) - current_time()).total_seconds()
    require(remaining > 0, "The reservation's deadline has passed; record the attempt with abandon")
    return remaining


def prepared_run(directory, config, rundir, root, timeout=None):
    """Check every launch precondition and return what the launch needs; write nothing."""
    harness.config_valid(config)
    require(config["enabled"], "Execution harness dispatch is disabled")
    require(timeout is None or timeout > 0, "--timeout-seconds must be positive")
    state, sequence, head = feedback.replay(directory)
    require(state["pending"], "No reserved dispatch is awaiting a launch")
    attempt = state["attempts"][-1]
    try:
        anchor = feedback.active_anchor(root, state["packet"]["domain_profile"])
    except OSError as exc:
        raise ValueError(f"ACTIVE bootstrap required: {exc}") from exc
    require(anchor == state["anchor"], "Approved architecture differs from this task's INIT")
    rundir = Path(rundir)
    brief = wp.read_json(rundir / "brief.json")
    require(isinstance(brief, dict) and brief.get("dispatch_id") == state["pending"],
            "The run directory was not prepared for the pending dispatch")
    recorded = brief.get("paths")
    require(isinstance(recorded, dict) and isinstance(recorded.get("brief"), str),
            "The brief does not record its run directory")
    paths = harness.run_paths(Path(recorded["brief"]).parent)
    require(recorded == {key: str(paths[key]) for key in ("workspace", "brief", "rules", "report")},
            "The brief's recorded paths are not a prepared run directory's")
    require(paths["rundir"].resolve() == rundir.resolve(),
            "The run directory differs from the one the brief records; launch from where dispatch ran")
    bindings = [item for item in config["bindings"] if item["resource_id"] == attempt["resource_id"]]
    require(len(bindings) == 1, f"No harness binding for reserved resource {attempt['resource_id']}")
    selected = next(item for item in config["harnesses"] if item["id"] == bindings[0]["harness_id"])
    # The whole brief is what dispatch renders from the ledger's own record of this reservation, so an
    # edited contract, context or startup text never reaches the worker (PR #70 Codex round 1).
    recorded_dispatch = dispatch_record(directory, sequence, head, state["pending"])
    reserved = recorded_dispatch["plan"]
    startup = harness.startup_bundle(root, reserved["context"]["contract"], config)
    readable = harness.brief(reserved["context"], reserved["routing"], bindings[0], state["pending"],
                             paths, startup)[2]
    rules = "".join(startup["rules"]["content_lines"])
    plan = harness.invocation(selected, bindings[0], paths)
    expected = {"brief": readable, "rules": rules, "invocation": plan}
    verify_prepared(rundir, expected)
    # The current configuration must still judge the prepared prompt to fit, as dispatch did
    # (PR #70 Codex round 2), from the router configuration and request the ledger recorded.
    router_config = recorded_dispatch["config"]
    harness.bindings_consistent(config, router_config)
    estimate = harness.context_estimate(config, selected, bindings[0],
                                        harness.routed_resource(router_config, reserved["routing"]),
                                        recorded_dispatch["options"], len(readable),
                                        len(rules) if any("{rules}" in item for item in selected["argv"]) else 0)
    require(estimate["headroom_tokens"] >= 0,
            f"The prepared run needs about {estimate['required_tokens']} tokens, but the current configuration "
            f"serves a {estimate['served_context_window']}-token window; record the attempt with abandon")
    require_unreported(rundir)
    require(not os.path.lexists(rundir / MARKER) and not os.path.lexists(launch_guard(directory, state["pending"])),
            f"The run directory was already launched ({MARKER} exists); record the attempt with ingest or abandon")
    remaining = remaining_seconds(attempt["deadline"])
    return {"dispatch_id": state["pending"], "argv": plan["argv"], "names": plan["required_environment"],
            "environment": child_environment(plan["required_environment"]), "deadline": attempt["deadline"],
            "bound": remaining if timeout is None else min(float(timeout), remaining), "rundir": rundir,
            "expected": expected, "ledger": (Path(directory), sequence, head)}


class Interrupts:
    """Hold Ctrl+C while the harness is started or torn down, so no interrupt leaves an unowned tree."""

    def __init__(self):
        self.holding = False
        self.pending = False
        self.installed = False

    def __call__(self, signum, frame):
        if self.holding:
            self.pending = True
        else:
            raise KeyboardInterrupt

    def __enter__(self):
        try:
            self.previous = signal.signal(signal.SIGINT, self)
            self.installed = True
        except ValueError:
            pass  # Not the main thread, where no KeyboardInterrupt is ever delivered.
        return self

    def __exit__(self, *exc):
        if self.installed:
            signal.signal(signal.SIGINT, self.previous)


def wait_within(process, bound):
    """Wait for the harness leader; True when the bound passed first."""
    deadline = time.monotonic() + bound
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            process.wait(timeout=min(WAIT_SLICE_SECONDS, remaining))
            return False
        except subprocess.TimeoutExpired:
            pass
    return process.poll() is None


def launch(directory, config, rundir, root, timeout=None):
    """Run the prepared harness once, owning its whole tree until it is confirmed stopped."""
    run = prepared_run(directory, config, rundir, root, timeout)
    marker = run["rundir"] / MARKER
    guard = launch_guard(run["ledger"][0], run["dispatch_id"])
    timed_out = interrupted = False
    bound = run["bound"]
    with Interrupts() as interrupts:
        interrupts.holding = True
        # Exclusive creation of the guard beside the ledger, then of the marker in RUNDIR, makes this
        # reservation launch once; the worker can remove the marker but is never given the guard.
        record = json.dumps({"dispatch_id": run["dispatch_id"], "launched_at": wp.now(),
                             "deadline": run["deadline"], "bound_seconds": round(run["bound"], 3),
                             "environment_names": run["names"]}, indent=2) + "\n"
        guard_store(guard)
        try:
            create_exclusive(guard, record)
        except FileExistsError as exc:
            raise ValueError("Another launch of this run directory started first") from exc
        try:
            create_exclusive(marker, record)
        except FileExistsError as exc:
            guard.unlink()
            raise ValueError("Another launch of this run directory started first") from exc
        except OSError:
            guard.unlink()  # Nothing ran, so the reservation is not spent.
            raise
        try:
            # Checked again once the marker is held, so a change after the precondition check is caught.
            # Everything that can change is checked again here: the ledger (so the reservation is
            # still the pending, latest dispatch), the run files, report absence and the deadline.
            directory_, sequence, head = run["ledger"]
            require(feedback.replay(directory_)[1:] == (sequence, head),
                    "The feedback ledger changed after the launch was checked; the reservation may be closed")
            verify_prepared(run["rundir"], run["expected"])
            require_unreported(run["rundir"])
            remaining_seconds(run["deadline"])
        except (ValueError, OSError):
            marker.unlink()  # Nothing ran, so the run directory is not spent.
            guard.unlink()
            raise
        try:
            process = acceptance.ProcessTree.launch(run["argv"], None, env=run["environment"],
                                                    stdin=subprocess.DEVNULL, stdout=2, stderr=2)
        except OSError as exc:
            marker.unlink()  # Nothing ran, so the run directory is not spent.
            guard.unlink()
            raise ValueError(f"The harness could not be started, so nothing ran: {exc}") from exc
        try:
            with acceptance.ProcessTree.own(process) as tree:
                try:
                    interrupts.holding = False
                    if interrupts.pending:
                        raise KeyboardInterrupt
                    # Measured from the absolute deadline again, so start-up time counts against it.
                    left = (feedback.instant(run["deadline"]) - current_time()).total_seconds()
                    bound = max(0.0, left if timeout is None else min(float(timeout), left))
                    timed_out = wait_within(process, bound)
                finally:
                    interrupts.holding = True  # The teardown in own() completes before any interrupt acts.
        except KeyboardInterrupt:
            interrupted = True
        require(tree.stopped, f"The harness process tree (pid {process.pid}) could not be confirmed stopped; "
                              "stop it before recording the attempt")
        # The worker can write in its run directory, so the one-launch guard is checked and, once the
        # tree is stopped, restored: a deleted marker must never let this reservation run twice.
        if not marker_intact(marker, record):
            # A link, directory or special file in its place is never written through; the guard still holds.
            if not os.path.lexists(marker) or stat.S_ISREG(os.lstat(marker).st_mode):
                marker.write_text(record, encoding="utf-8")
            raise ValueError(f"The harness changed {MARKER} while it ran; the one-launch guard is kept so this run "
                             "directory is not launched again; do not ingest its report; record the attempt with abandon")
        try:
            verify_prepared(run["rundir"], run["expected"])
        except (ValueError, OSError) as exc:
            raise ValueError(f"The run directory changed while the harness ran ({exc}); do not ingest its "
                             "report; record the attempt with abandon") from exc
        # Read last, while interrupts are still held, so none arriving during the checks is lost.
        interrupted = interrupted or interrupts.pending
    present = (run["rundir"] / "report.json").is_file()
    status = ("INTERRUPTED" if interrupted else "TIMED_OUT" if timed_out
              else "REPORT_WRITTEN" if present else "NO_REPORT")
    return {"status": status, "dispatch_id": run["dispatch_id"], "started": True,
            "harness_exit_code": process.returncode, "tree_stopped": True, "report_present": present,
            "next_action": "ingest" if present else "abandon", "bound_seconds": round(bound, 3),
            "environment_names": run["names"], "recorded_in_ledger": False, "independent_acceptance": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("launch", help="Run the harness prepared for the pending reservation")
    run.add_argument("ledger", type=Path)
    run.add_argument("rundir", type=Path)
    run.add_argument("--timeout-seconds", type=int, help="Shorten the reservation's own deadline")
    args = parser.parse_args(argv)
    # An interrupt outside the owned run (nothing started yet, or the tree already confirmed
    # stopped) propagates to cli_exit.run, which reports it and exits 130 like every command.
    try:
        result = launch(args.ledger, wp.read_json(args.config), args.rundir, args.root, args.timeout_seconds)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Worker launcher refused: {exc}", file=sys.stderr)
        return 1
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, ValueError):
        pass  # A closed stdout must not replace the outcome's exit code (ADR-072).
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(cli_exit.run(main))
