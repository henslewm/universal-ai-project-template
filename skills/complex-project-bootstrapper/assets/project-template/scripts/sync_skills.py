#!/usr/bin/env python3
"""Synchronize bootstrap entrypoints, native skills and the standalone template."""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import os
import shutil
import stat
import tempfile
from pathlib import Path

import cli_exit

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills/complex-project-bootstrapper'
# 'Claude outputs' is where the Claude desktop app saves session artifacts when the working
# folder is this repository; those are personal working files, never template payload.
EXCLUDED = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'dist', 'build', 'assets',
            'Claude outputs'}
# Pruning skips only regenerated caches and version-control state, which bootstrap_project.py never
# ships and which running the test suite legitimately creates inside the native mirrors.
PRUNE_SKIPPED = {'.git', '__pycache__', '.pytest_cache'}


def files_under(root: Path, every_file: bool = False):
    """Files under `root`.

    By default only files that may become payload, never descending into EXCLUDED directories.
    `every_file=True` is for pruning a mirror, whose invariant is that it holds exactly what the
    copy produced: it yields every file present, whatever its name or directory, except under
    PRUNE_SKIPPED, so anything the copy filters would never have produced is found and removed."""
    skipped = PRUNE_SKIPPED if every_file else EXCLUDED
    for directory, dirs, files in os.walk(root):
        # os.walk does not stop at a Windows junction on its own (is_symlink() is False for one),
        # so it is excluded from descent here explicitly, the same as an excluded/skipped name.
        dirs[:] = sorted(name for name in dirs
                         if name not in skipped and not is_junction(Path(directory) / name))
        for name in sorted(files):
            # A symlinked file is never a legitimate copy source, wherever under `root` it is
            # found: files_under(ROOT) walks the whole repository, including the native mirror
            # directories that unlink_all reports but, under --check, does not yet remove, so a
            # link left there must not be picked up here and read through as if it were content.
            if (Path(directory) / name).is_symlink():
                continue
            # EXCLUDED names are excluded as files too: in a git worktree or submodule `.git`
            # is a pointer file, and it must never become payload.
            if every_file or (name not in EXCLUDED and not name.endswith(('.pyc', '.zip'))
                              and name not in {'bootstrap-answers.local.json', 'bootstrap.json', 'bootstrap.json.tmp', 'BOOTSTRAP_REVIEW.md'}):
                yield Path(directory) / name


def links_under(root: Path):
    """Every symbolic link or junction (file or directory) under `root`, outside PRUNE_SKIPPED; never
    followed. A Windows junction is not reported by is_symlink(), so it is checked separately."""
    for directory, dirs, files in os.walk(root):
        for name in sorted([*dirs, *files]):
            path = Path(directory) / name
            if path.is_symlink() or is_junction(path):
                yield path
        dirs[:] = sorted(name for name in dirs if name not in PRUNE_SKIPPED
                         and not (Path(directory) / name).is_symlink()
                         and not is_junction(Path(directory) / name))


def is_junction(path: Path) -> bool:
    """True for a Windows junction. `Path.is_junction` exists from Python 3.12; on an older
    Python, or on a platform without junctions, there is none to detect."""
    method = getattr(path, 'is_junction', None)
    return bool(method and method())


def remove_link(path: Path):
    try:
        path.unlink()
    except OSError:
        os.rmdir(path)  # a Windows directory symlink or junction


def refuse_linked_path(target: Path):
    """The sync never reads, writes or deletes through a link: refuse a destination that is, or sits
    beneath, a symbolic link or junction between ROOT and itself."""
    path = ROOT
    for part in target.relative_to(ROOT).parts:
        path = path / part
        if path.is_symlink() or is_junction(path):
            raise ValueError(f'Refusing to sync through a link: {path.relative_to(ROOT).as_posix()}')


def sync(check: bool = False) -> list[str]:
    differences = []
    expected = set()
    mirrors = [ROOT / native / SKILL.name for native in ('.agents/skills', '.claude/skills')]
    asset = SKILL / 'assets/project-template'
    # Checked once, before anything is copied, pruned or unlinked: every destination root and each
    # directory above it is real, so no write or deletion can land outside the repository.
    for destination in [SKILL / 'scripts', *mirrors, asset]:
        refuse_linked_path(destination)

    def unlink_all(mirror: Path):
        # The copy never creates a link. A link in a mirror would be followed by the copy (writing
        # outside the mirror) or by the generator's copytree (shipping whatever it points at), so
        # every link is drift, removed before anything is copied into the mirror.
        if not mirror.is_dir():
            return
        for link in list(links_under(mirror)):
            differences.append(link.relative_to(ROOT).as_posix())
            if not check:
                remove_link(link)

    def copy(source: Path, target: Path):
        expected.add(target)
        # Anything at the target, or at a directory above it, that is not what the copy would have
        # made (a link, a directory where a file belongs, a file where a directory belongs) is drift.
        # It is reported without being read, and a sync removes it before writing.
        blocking = [ROOT / parent for parent in reversed(target.relative_to(ROOT).parents)
                    if (ROOT / parent).is_symlink() or is_junction(ROOT / parent)
                    or ((ROOT / parent).exists() and not (ROOT / parent).is_dir())]
        if target.is_symlink() or is_junction(target) or (target.exists() and not target.is_file()):
            blocking.append(target)
        if not blocking:
            try:
                target_stat = target.stat()
            except FileNotFoundError:
                target_stat = None
            matches = False
            if target_stat is not None and stat.S_ISREG(target_stat.st_mode) and target_stat.st_nlink == 1:
                # A source that is itself stale drift (e.g. a native-mirror entry prune() has
                # already reported but --check left in place) may not be safely readable; report
                # the already-known difference instead of raising out of the fast path.
                try:
                    matches = (stat.S_IMODE(source.stat().st_mode) == stat.S_IMODE(target_stat.st_mode)
                               and source.read_bytes() == target.read_bytes())
                except OSError:
                    matches = False
            if matches:
                return
        differences.append(target.relative_to(ROOT).as_posix())
        if check:
            return
        for path in blocking:
            if path.is_symlink() or is_junction(path):
                remove_link(path)
            elif path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        # Replace the directory entry rather than writing into the existing file, so a target that
        # shares its inode with another name (a hard link) never changes that other file. The name
        # is allocated by mkstemp, not derived from the target's own name, so it can never collide
        # with an actual source file that happens to share that name (round 11).
        descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=target.name + '.',
                                                        suffix='.sync-tmp')
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source, temporary)
            shutil.copymode(source, temporary)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    for name in ('bootstrap_project.py', 'bootstrap_gate.py', 'validate_bootstrap.py', 'validate_project.py', 'cli_exit.py'):
        copy(ROOT / 'scripts' / name, SKILL / 'scripts' / name)
    def prune(mirror: Path):
        # A mirror holds only what its source produces: a file deleted or renamed at the source
        # is obsolete, reported by --check and removed by a sync.
        if not mirror.is_dir():
            return
        for target in files_under(mirror, every_file=True):
            if target not in expected and not target.is_symlink():  # links: see unlink_all
                differences.append(target.relative_to(ROOT).as_posix())
                if not check:
                    target.unlink()
        # The same invariant for directories: one the copy produced lies above an expected file.
        # Any other directory is obsolete, including one left empty by the pruning above; the
        # topmost is reported, and removed with whatever regenerated caches remain inside it.
        produced = {parent for target in expected if target.is_relative_to(mirror)
                    for parent in target.parents if parent.is_relative_to(mirror)}
        obsolete = []
        for directory, dirs, _ in os.walk(mirror):
            # A junction is not stopped by PRUNE_SKIPPED and is not reported by is_symlink(), so
            # it is found and excluded from descent here explicitly, the same as in
            # files_under/links_under: this walk must not rely on unlink_all's earlier sweep of
            # the same tree to have already removed it. A junction is never something the copy
            # produced, so it is unconditionally obsolete, not merely absent from `produced`.
            junctions = [name for name in dirs if is_junction(Path(directory) / name)]
            obsolete.extend(Path(directory) / name for name in junctions)
            dirs[:] = sorted(name for name in dirs if name not in PRUNE_SKIPPED and name not in junctions)
            for name in list(dirs):
                path = Path(directory) / name
                if path not in produced:
                    obsolete.append(path)
                    dirs.remove(name)  # the topmost obsolete directory covers everything below
        for path in obsolete:
            # A link or junction here is the same defense-in-depth case as copy()'s own removal
            # loop: never follow it into shutil.rmtree, whatever swept the rest of the tree
            # earlier. It is reported the same bare way unlink_all reports one (no trailing
            # slash), so a junction --check finds here as well as via unlink_all's own earlier
            # pass over the same still-present path (nothing is deleted under --check) collapses
            # to the single entry the final dict.fromkeys dedup already promises, rather than
            # being listed twice under two different spellings of the same path.
            is_link = path.is_symlink() or is_junction(path)
            differences.append(path.relative_to(ROOT).as_posix() + ('' if is_link else '/'))
            if not check:
                if is_link:
                    remove_link(path)
                else:
                    shutil.rmtree(path)

    for mirror in mirrors:
        unlink_all(mirror)
    for source in files_under(SKILL):
        for mirror in mirrors:
            copy(source, mirror / source.relative_to(SKILL))
    # Prune the native mirrors before they are themselves copied into the payload, so one sync
    # converges instead of carrying an obsolete file into the payload for one more round.
    for mirror in mirrors:
        prune(mirror)
    unlink_all(asset)
    for source in files_under(ROOT):
        copy(source, asset / source.relative_to(ROOT))
    prune(asset)
    return list(dict.fromkeys(differences))  # a path reported by two passes is listed once


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail on payload drift without writing files')
    args = parser.parse_args()
    try:
        differences = sync(args.check)
    except ValueError as exc:
        print(f'BOOTSTRAP PAYLOAD REFUSED: {exc}')
        return 1
    if args.check and differences:
        print('BOOTSTRAP PAYLOAD DRIFT\n' + '\n'.join(differences))
        return 1
    print(f'Bootstrap payloads {"verified" if args.check else "synchronized"}; {len(differences)} files differed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(cli_exit.run(main))
