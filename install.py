#!/usr/bin/python3
#
# Script to install symbolic links for dot files/config files/etc. Used to maintain
# a common shell configuration between machines
# <cimarronm@gmail.com>

import os
import sys
import logging

log = logging.getLogger(__name__)
ignoredfiles = set((".git", ".gitignore", ".gitmodules", os.path.basename(__file__)))


def installfile(file, installdir):
    try:
        os.symlink(os.path.relpath(file, start=installdir),
               os.path.join(installdir, file))
    except:
        log.exception("Problem creating symbolic link")

def do_install(installdir=os.path.expanduser("~"), dryrun=False):
    if not os.path.isdir(installdir):
        log.error(f"Cannot install to {installdir}. It is not a directory")
        raise RuntimeError("installdir is not directory")

    installs = []
    installed = []
    conflicts = []
    for file in os.listdir('.'):
        if file in ignoredfiles:
            continue
        try:
            if os.path.samefile(file, os.path.join(installdir, file)):
                installed.append(file)
                log.info("f{file} is already installed")
            else:
                log.warning(f"Conflicting file {file}")
                conflicts.append(file)
        except OSError:  # FileNotFoundError: OSError instead for python 2 compatibility
            if not dryrun:
                installfile(file, installdir)
            installs.append(file)
            print(f"{file} installed")

    return dict(installs=installs, installed=installed, conflicts=conflicts)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    defaultinstall = os.path.expanduser("~")
    parser.add_argument("installpath",
                        help=f"Path to install symbolic links (default:{defaultinstall})",
                        default=defaultinstall, nargs='?', type=os.path.expanduser)
    parser.add_argument("--log", help="log level", type=int)
    parser.add_argument("-n", "--dryrun", help="Perform dry run, don't actually do anything",
                        action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=args.log)
    try:
        results = do_install(installdir=args.installpath, dryrun=args.dryrun)
    except:
        errors = True
    else:
        errors = False

    if errors or results['conflicts']:
        sys.exit(1)
