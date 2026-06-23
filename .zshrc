autoload compinit && compinit -i

if command -v fastfetch &> /dev/null; then
    fastfetch
fi

if command -v starship &> /dev/null; then
    eval "$(starship init zsh)"
fi

if command -v fzf &> /dev/null; then
    source <(fzf --zsh)
fi

if command -v gh &> /dev/null; then
    source <(gh completion -s zsh)
fi

if [ -f ~/.aliases ]; then
    source ~/.aliases
fi
