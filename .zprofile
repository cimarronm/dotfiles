export CLICOLOR=1
export EDITOR=vi
export PAGER="less -iR"

if [[ -e "$HOME/.homebrew_env" ]]; then
  source "$HOME/.homebrew_env"
fi
