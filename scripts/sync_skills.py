#!/usr/bin/env python3
"""Synchronize bootstrap entrypoints, native skills and the standalone template."""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

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
        dirs[:] = sorted(name for name in dirs if name not in skipped)
        for name in sorted(files):
            # EXCLUDED names are excluded as files too: in a git worktree or submodule `.git`
            # is a pointer file, and it must never become payload.
            if every_file or (name not in EXCLUDED and not name.endswith(('.pyc', '.zip'))
                              and name not in {'bootstrap-answers.local.json', 'bootstrap.json', 'bootstrap.json.tmp', 'BOOTSTRAP_REVIEW.md'}):
                yield Path(directory) / name


def links_under(root: Path):
    """Every symbolic link (file or directory) under `root`, outside PRUNE_SKIPPED; never followed."""
    for directory, dirs, files in os.walk(root):
        for name in sorted([*dirs, *files]):
            if (Path(directory) / name).is_symlink():
                yield Path(directory) / name
        dirs[:] = sorted(name for name in dirs
                         if name not in PRUNE_SKIPPED and not (Path(directory) / name).is_symlink())


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
    beneath, a symbolic link between ROOT and itself."""
    path = ROOT
    for part in target.relative_to(ROOT).parts:
        path = path / part
        if path.is_symlink():
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
                    if (ROOT / parent).is_symlink() or ((ROOT / parent).exists() and not (ROOT / parent).is_dir())]
        if target.is_symlink() or (target.exists() and not target.is_file()):
            blocking.append(target)
        if (not blocking and target.is_file() and target.stat().st_nlink == 1
                and source.read_bytes() == target.read_bytes()):
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
        # shares its inode with another name (a hard link) never changes that other file.
        temporary = target.with_name(target.name + '.sync-tmp')
        try:
            shutil.copyfile(source, temporary)
            shutil.copymode(source, temporary)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    for name in ('bootstrap_project.py', 'bootstrap_gate.py', 'validate_bootstrap.py', 'validate_project.py'):
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
            dirs[:] = sorted(name for name in dirs if name not in PRUNE_SKIPPED)
            for name in list(dirs):
                path = Path(directory) / name
                if path not in produced:
                    obsolete.append(path)
                    dirs.remove(name)  # the topmost obsolete directory covers everything below
        for path in obsolete:
            differences.append(path.relative_to(ROOT).as_posix() + '/')
            if not check:
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
    raise SystemExit(main())
