autoload compinit && compinit -i

export CLICOLOR=1;

if [ -f .aliases ]; then
    source .aliases
fi

if command -v starship &> /dev/null; then
    eval "$(starship init zsh)"
fi
