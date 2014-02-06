if [ -z "$PS1" ]; then
   return
fi

pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH+=":$1"
    fi
}

export CLICOLOR=1;

if [ -f .aliases ]; then
    . .aliases
fi

pathadd "$HOME/projects/mocaUtilities"
