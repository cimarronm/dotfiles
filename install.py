import os

ignoredfiles = set((".git",".gitignore",__file__))

def installfile(file):
    os.symlink(os.path.relpath(file, start=os.path.expanduser("~")),
            os.path.join(os.path.expanduser("~"), file))
    print("{} installed".format(file))

for file in os.listdir():
    if file in ignoredfiles:
        continue
    try:
        if os.path.samefile(file, os.path.expanduser(os.path.join("~",file))):
            print("{} is already installed".format(file))
        else:
            print("{} is different".format(file))
    except FileNotFoundError:
        installfile(file)
