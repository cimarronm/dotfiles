autoload compinit && compinit -i

export CLICOLOR=1;

if [ -f .aliases ]; then
    source .aliases
fi
