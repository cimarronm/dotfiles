if [ -z "$PS1" ]; then
   return
fi

shopt -s histappend

export EDITOR=vi

pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH+=":$1"
    fi
}

setwintitle() {
    printf "\e]0;$USER@$HOSTNAME\a"
}

export CLICOLOR=1;

if command -v fastfetch &> /dev/null; then
    fastfetch
fi

if [ -f .aliases ]; then
    . .aliases
fi

if [ -f .projectsettings ]; then
    . .projectsettings
fi

if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
    starship_precmd_user_func="setwintitle"
fi

if command -v fzf &> /dev/null; then
    source <(fzf --bash)
fi

if command -v gh &> /dev/null; then
    source <(gh completion -s bash)
fi
