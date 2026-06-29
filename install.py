#!/usr/bin/env python3
#
# Script to install symbolic links for dot files/config files/etc. Used to maintain
# a common shell configuration between machines
# <cimarronm@gmail.com>

import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys

log = logging.getLogger(__name__)
SCRIPT_DIR = Path(__file__).resolve().parent
IGNORED_FILES = {".git", ".gitignore", ".gitmodules", Path(__file__).name}


def parse_log_level(value):
    try:
        return int(value)
    except ValueError:
        level = getattr(logging, value.upper(), None)
        if isinstance(level, int):
            return level
    raise argparse.ArgumentTypeError(f"Invalid log level: {value}")


def create_symlink(source_path, destination_path):
    relative_target = os.path.relpath(source_path, start=destination_path.parent)
    destination_path.symlink_to(relative_target)


def link_points_to_source(destination_path, source_path):
    if not destination_path.is_symlink():
        return False

    link_target = destination_path.readlink()
    if not link_target.is_absolute():
        link_target = (destination_path.parent / link_target).resolve()
    return link_target == source_path.resolve()


def is_gitignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", str(path.relative_to(SCRIPT_DIR))],
        cwd=SCRIPT_DIR,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def install_file(source_path, destination_path, label, installs, installed, conflicts, dryrun):
    """Install a single symlink from source_path to destination_path."""
    if link_points_to_source(destination_path, source_path):
        installed.append(label)
        log.info("%s is already installed", label)
        return

    if destination_path.exists() or destination_path.is_symlink():
        log.warning("Conflicting file %s", label)
        conflicts.append(label)
        return

    if dryrun:
        print(f"{label} would be installed")
    else:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        create_symlink(source_path, destination_path)
        print(f"{label} installed")
    installs.append(label)


def collect_files(directory):
    """Recursively yield all files under a directory."""
    for child in sorted(directory.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            yield from collect_files(child)
        else:
            yield child


def do_install(installdir=Path.home(), dryrun=False):
    install_dir = Path(installdir).expanduser()
    if not install_dir.is_dir():
        log.error("Cannot install to %s. It is not a directory", install_dir)
        raise RuntimeError("installdir is not directory")

    installs = []
    installed = []
    conflicts = []
    for source_path in sorted(SCRIPT_DIR.iterdir(), key=lambda path: path.name):
        if source_path.name in IGNORED_FILES or is_gitignored(source_path):
            continue

        if source_path.is_dir():
            # For directories (e.g. .config/, .ssh/), symlink individual files
            # rather than the directory itself, creating parent dirs as needed.
            for source_file in collect_files(source_path):
                relative = source_file.relative_to(SCRIPT_DIR)
                if is_gitignored(source_file):
                    continue
                destination_path = install_dir / relative
                label = str(relative)
                install_file(source_file, destination_path, label, installs, installed, conflicts, dryrun)
        else:
            destination_path = install_dir / source_path.name
            install_file(source_path, destination_path, source_path.name, installs, installed, conflicts, dryrun)

    return dict(installs=installs, installed=installed, conflicts=conflicts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    defaultinstall = str(Path.home())
    parser.add_argument(
        "installpath",
        help=f"Path to install symbolic links (default:{defaultinstall})",
        default=defaultinstall,
        nargs="?",
        type=Path,
    )
    parser.add_argument("--log", help="log level", default="WARNING", type=parse_log_level)
    parser.add_argument(
        "-n",
        "--dryrun",
        help="Perform dry run, don't actually do anything",
        action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.log)
    try:
        results = do_install(installdir=args.installpath, dryrun=args.dryrun)
    except Exception:
        log.exception("Install failed")
        errors = True
    else:
        errors = False

    if errors or results["conflicts"]:
        sys.exit(1)
