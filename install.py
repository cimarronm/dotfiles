import os

ignoredfiles = set((".git",".gitignore",__file__))

def installfile(file):
    os.symlink(os.path.relpath(file, start=os.path.expanduser("~")),
            os.path.join(os.path.expanduser("~"), file))
    print("{} installed".format(file))

for file in os.listdir():
    errors = False
    if file in ignoredfiles:
        continue
    try:
        if os.path.samefile(file, os.path.expanduser(os.path.join("~",file))):
            print("{} is already installed".format(file))
        else:
            print("{} is different".format(file))
            errors = True
    except FileNotFoundError:
        installfile(file)

    if errors:
        import sys
        sys.exit(1)
