if [ -z "$PS1" ]; then
   return
fi

export CLICOLOR=1;

if [ -f .aliases ]; then
    . .aliases
fi

