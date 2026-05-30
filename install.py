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

        destination_path = install_dir / source_path.name
        if link_points_to_source(destination_path, source_path):
            installed.append(source_path.name)
            log.info("%s is already installed", source_path.name)
            continue

        if destination_path.exists() or destination_path.is_symlink():
            log.warning("Conflicting file %s", source_path.name)
            conflicts.append(source_path.name)
            continue

        if dryrun:
            print(f"{source_path.name} would be installed")
        else:
            create_symlink(source_path, destination_path)
            print(f"{source_path.name} installed")
        installs.append(source_path.name)

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
