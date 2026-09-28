#!/usr/bin/env python3
"""Run one reserved, prepared worker attempt for the operator with a scoped provider environment (ADR-073).

Optional and operator-invoked only: no controller calls this, and it never writes the task ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import acceptance
import execution_harness as harness
import feedback
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
MARKER = "launch.json"
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


def prepared_run(directory, config, rundir, root, timeout=None):
    """Check every launch precondition and return what the launch needs; write nothing."""
    harness.config_valid(config)
    require(config["enabled"], "Execution harness dispatch is disabled")
    require(timeout is None or timeout > 0, "--timeout-seconds must be positive")
    state = feedback.replay(directory)[0]
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
    require(brief.get("binding") == feedback.binding(state["packet"]),
            "The run directory's brief is bound to a different task revision")
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
    plan = harness.invocation(selected, bindings[0], paths)
    require(wp.read_json(rundir / "invocation.json") == plan,
            "invocation.json differs from what the current configuration prepares for this attempt")
    require(not os.path.lexists(rundir / "report.json"),
            "The run directory already holds report.json; ingest it instead of launching again")
    require(not os.path.lexists(rundir / MARKER),
            f"The run directory was already launched ({MARKER} exists); record the attempt with ingest or abandon")
    remaining = (feedback.instant(attempt["deadline"]) - current_time()).total_seconds()
    require(remaining > 0, "The reservation's deadline has passed; record the attempt with abandon")
    return {"dispatch_id": state["pending"], "argv": plan["argv"], "names": plan["required_environment"],
            "environment": child_environment(plan["required_environment"]), "deadline": attempt["deadline"],
            "bound": remaining if timeout is None else min(float(timeout), remaining), "rundir": rundir}


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
    timed_out = interrupted = False
    with Interrupts() as interrupts:
        interrupts.holding = True
        # Exclusive creation is the guard: this run directory launches once. It holds names only.
        try:
            wp.write_new(marker, json.dumps({"dispatch_id": run["dispatch_id"], "launched_at": wp.now(),
                                             "deadline": run["deadline"], "bound_seconds": round(run["bound"], 3),
                                             "environment_names": run["names"]}, indent=2) + "\n")
        except FileExistsError as exc:
            raise ValueError("Another launch of this run directory started first") from exc
        try:
            process = acceptance.ProcessTree.launch(run["argv"], None, env=run["environment"],
                                                    stdin=subprocess.DEVNULL, stdout=2, stderr=2)
        except OSError as exc:
            marker.unlink()  # Nothing ran, so the run directory is not spent.
            raise ValueError(f"The harness could not be started, so nothing ran: {exc}") from exc
        try:
            with acceptance.ProcessTree.own(process) as tree:
                try:
                    interrupts.holding = False
                    if interrupts.pending:
                        raise KeyboardInterrupt
                    timed_out = wait_within(process, run["bound"])
                finally:
                    interrupts.holding = True  # The teardown in own() completes before any interrupt acts.
        except KeyboardInterrupt:
            interrupted = True
        require(tree.stopped, f"The harness process tree (pid {process.pid}) could not be confirmed stopped; "
                              "stop it before recording the attempt")
        interrupted = interrupted or interrupts.pending
    present = (run["rundir"] / "report.json").is_file()
    status = ("INTERRUPTED" if interrupted else "TIMED_OUT" if timed_out
              else "REPORT_WRITTEN" if present else "NO_REPORT")
    return {"status": status, "dispatch_id": run["dispatch_id"], "started": True,
            "harness_exit_code": process.returncode, "tree_stopped": True, "report_present": present,
            "next_action": "ingest" if present else "abandon", "bound_seconds": round(run["bound"], 3),
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
    try:
        result = launch(args.ledger, wp.read_json(args.config), args.rundir, args.root, args.timeout_seconds)
    except KeyboardInterrupt:
        # Outside the owned run: either nothing was started, or the tree was already confirmed stopped.
        print("Worker launcher interrupted; no harness it started is still running.", file=sys.stderr)
        return 130
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Worker launcher refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
