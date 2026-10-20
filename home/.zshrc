# Shell basics (replaces Oh My Zsh: same robbyrussell-style prompt, completion and history)
HISTFILE=~/.zsh_history HISTSIZE=50000 SAVEHIST=10000
setopt extended_history hist_expire_dups_first hist_ignore_dups hist_ignore_space hist_verify share_history
setopt auto_cd auto_pushd pushd_ignore_dups pushd_minus interactive_comments no_flow_control
setopt complete_in_word always_to_end prompt_subst long_list_jobs

autoload -Uz compinit && compinit -C
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z-_}={A-Za-z_-}' 'r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' list-colors ''

# Up/Down search history for what's already typed; Ctrl/Option-arrows move by word.
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search; zle -N down-line-or-beginning-search
bindkey -e
bindkey '^[[A' up-line-or-beginning-search '^[OA' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search '^[OB' down-line-or-beginning-search
bindkey '^[[1;5C' forward-word '^[[1;5D' backward-word '^[[1;3C' forward-word '^[[1;3D' backward-word
bindkey '^[[H' beginning-of-line '^[[F' end-of-line '^[[3~' delete-char

# Prompt: ➜ (red after a failed command)  dir  git:(branch) ✗
git_prompt_info() {
  local b=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null) || return
  [[ -z $b ]] && return
  if [[ -n $(git status --porcelain --untracked-files=normal 2>/dev/null | head -1) ]]; then
    print -n "%B%F{blue}git:(%F{red}$b%F{blue}) %F{yellow}✗%f%b "
  else
    print -n "%B%F{blue}git:(%F{red}$b%F{blue})%f%b "
  fi
}
PROMPT='%B%(?:%F{green}➜:%F{red}➜)%f%b %F{cyan}%c%f $(git_prompt_info)'

# User configuration

export PATH="$HOME/.local/bin:$PATH"

# Omarchy-inspired shell tools — added 2026-09-14
# Skip the aliases in agent shells (Claude Code sets CLAUDECODE=1); agents expect POSIX ls/cat/grep/find/cd.
eval "$(zoxide init zsh)"
if [[ -z $CLAUDECODE ]]; then
  alias ls="eza -lh --group-directories-first"
  alias lsa="eza -lha --group-directories-first"
  alias lt="eza --tree --level=2 --long --git"
  alias lta="eza --tree --level=2 --long --git --all"
  alias cat='bat --paging=never'
  alias grep='rg'
  alias find='fd'
  alias top='btop'
  alias cd='z'
fi
source /opt/homebrew/opt/fzf/shell/key-bindings.zsh
source /opt/homebrew/opt/fzf/shell/completion.zsh
# Grey inline suggestions from history (→ or Ctrl-E accepts, Alt-F takes one word) — from omerxx/dotfiles
source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
# atuin owns Ctrl-R (after fzf so it wins); Up keeps the prefix search above
eval "$(atuin init zsh --disable-up-arrow)"
# Prefer Homebrew Python 3.13 and its unversioned python/pip commands.
if [[ ":$PATH:" != *":$(brew --prefix python@3.13)/libexec/bin:"* ]]; then
export PATH="$(brew --prefix python@3.13)/libexec/bin:$(brew --prefix python@3.13)/bin:$PATH"
fi

# Android development toolchain
export ANDROID_HOME="$HOME/Library/Android/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME="/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$JAVA_HOME/bin:$PATH"
export CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1
[ -f ~/.agents/jev/.env ] && export $(grep -v "^#" ~/.agents/jev/.env | xargs)

# Cloudflare (token lives in macOS Keychain, service "cloudflare-api-token")
export CLOUDFLARE_API_TOKEN="$(security find-generic-password -s cloudflare-api-token -w 2>/dev/null)"

# IDs and other machine-local values (not in dotfiles): ~/.zshrc.local
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
