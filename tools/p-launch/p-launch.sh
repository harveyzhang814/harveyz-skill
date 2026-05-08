#!/usr/bin/env zsh
# p-launch — interactive project launcher
# Usage: p-launch            launch picker
#        p-launch --uninstall  remove everything

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_DIRS=(
  "{{PROJECT_DIR}}"
)
# Additional paths or overrides: define PROJECT_DIRS in ~/.config/p-launch/config.zsh
[[ -f "$HOME/.config/p-launch/config.zsh" ]] && source "$HOME/.config/p-launch/config.zsh"

# ── Colors ──────────────────────────────────────────────────────────────────
typeset -A C=(
  [rs]=$'\033[0m'   [bd]=$'\033[1m'    [dim]=$'\033[2m'
  [rd]=$'\033[31m'  [gr]=$'\033[32m'   [yl]=$'\033[33m'   [cy]=$'\033[36m'
)

# ── Helpers ─────────────────────────────────────────────────────────────────
_die() { printf "${C[rd]}error:${C[rs]} %s\n" "$*" >&2; exit 1 }

_check_deps() {
  command -v fzf &>/dev/null || _die "fzf not installed — fix with: brew install fzf"
}

# ── Project Collection ───────────────────────────────────────────────────────
# Scans all PROJECT_DIRS, emits paths sorted by mtime descending
_collect() {
  local -a rows=()
  local mtime
  for base in "${PROJECT_DIRS[@]}"; do
    [[ -d "$base" ]] || continue
    for d in "$base"/*/; do
      [[ -d "$d" ]] || continue
      mtime=$(stat -f "%m" "$d" 2>/dev/null) || continue
      rows+=("${mtime}"$'\t'"${d%/}")
    done
  done
  (( ${#rows} == 0 )) && return 1
  printf '%s\n' "${rows[@]}" | sort -t$'\t' -k1,1rn | cut -f2-
}

# ── fzf Display Formatting ───────────────────────────────────────────────────
# Input:  one path per line
# Output: "NAME \t PATH \t DISPLAY_PARENT" per line
_format() {
  while IFS= read -r p; do
    local name="${p:t}"
    local parent="${${p:h}/$HOME/~}"
    printf '%s\t%s\t%s\n' "$name" "$p" "$parent"
  done
}

# ── Launch ───────────────────────────────────────────────────────────────────
_launch() {
  local path="$1"
  local name="${path:t}"
  local display="${path/$HOME/~}"
  local cursor_ok=false ghostty_ok=false

  # Cursor IDE
  if command -v cursor &>/dev/null; then
    cursor "$path" &>/dev/null &
    cursor_ok=true
  fi

  # Ghostty — force a new window at the project directory
  if [[ -d "/Applications/Ghostty.app" ]]; then
    open -na "Ghostty" --args --working-directory="$path"
    ghostty_ok=true
  fi

  # ── Launch Report ──────────────────────────────────────────────────────────
  printf '\n'
  printf "  ${C[bd]}${C[cy]}%s${C[rs]}  ${C[dim]}%s${C[rs]}\n" "$name" "$display"
  printf '\n'

  if $cursor_ok; then
    printf "  ${C[gr]}✓${C[rs]} Cursor   opened\n"
  else
    printf "  ${C[yl]}⚠${C[rs]} Cursor   cursor CLI not found\n"
  fi

  if $ghostty_ok; then
    printf "  ${C[gr]}✓${C[rs]} Ghostty  new window opened\n"
  else
    printf "  ${C[yl]}⚠${C[rs]} Ghostty  /Applications/Ghostty.app not found\n"
  fi

  printf '\n'
  printf "  ${C[dim]}environment ready — good session.${C[rs]}\n"
  printf '\n'
}

# ── Uninstall ────────────────────────────────────────────────────────────────
_uninstall() {
  local self="${ZSH_SCRIPT:A}"
  local zshrc="$HOME/.zshrc"
  local config_dir="$HOME/.config/p-launch"
  local zshrc_marker="# >>> p-launch"

  local -a targets=("$self")
  [[ -f "$zshrc" ]] && grep -q "$zshrc_marker" "$zshrc" && \
    targets+=("~/.zshrc block (PATH + alias p)")
  [[ -d "$config_dir" ]] && \
    targets+=("${config_dir/$HOME/~}")

  printf '\n'
  printf "  ${C[bd]}${C[rd]}p-launch uninstall${C[rs]}\n\n"
  printf "  Will remove:\n"
  for t in "${targets[@]}"; do
    printf "    ${C[dim]}%s${C[rs]}\n" "$t"
  done
  printf '\n'
  printf "  Confirm removal? [y/N] "
  read -r reply
  [[ "$reply" =~ ^[Yy]$ ]] || { printf '\n  aborted.\n\n'; exit 0 }
  printf '\n'

  # 1. Remove the script itself (runs from memory, safe to delete)
  if rm -- "$self" 2>/dev/null; then
    printf "  ${C[gr]}✓${C[rs]} removed %s\n" "$self"
  else
    printf "  ${C[rd]}✗${C[rs]} could not remove %s\n" "$self"
  fi

  # 2. Strip the marked block from .zshrc
  if [[ -f "$zshrc" ]] && grep -q "$zshrc_marker" "$zshrc"; then
    sed -i '' '/^# >>> p-launch/,/^# <<< p-launch/d' "$zshrc"
    printf "  ${C[gr]}✓${C[rs]} cleaned ~/.zshrc\n"
  fi

  # 3. Remove config directory
  if [[ -d "$config_dir" ]]; then
    rm -rf -- "$config_dir"
    printf "  ${C[gr]}✓${C[rs]} removed %s\n" "${config_dir/$HOME/~}"
  fi

  printf '\n'
  printf "  ${C[dim]}done. run: source ~/.zshrc${C[rs]}\n\n"
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  if [[ "$1" == "--uninstall" || "$1" == "uninstall" ]]; then
    _uninstall
    return
  fi

  _check_deps

  local projects
  projects=$(_collect) || {
    printf "${C[yl]}no projects found${C[rs]} — check PROJECT_DIRS in this script\n"
    exit 0
  }

  local selected
  selected=$(
    _format <<< "$projects" | \
    fzf --ansi \
        --delimiter=$'\t' \
        --with-nth='1,3' \
        --prompt='  › ' \
        --header='  p-launch  ·  ↵ launch  ·  esc cancel  ·  ctrl-p preview' \
        --height=50% \
        --layout=reverse \
        --border=rounded \
        --color='header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold' \
        --preview='ls -1 {2} 2>/dev/null' \
        --preview-window='right:30%:wrap:hidden' \
        --bind='ctrl-p:toggle-preview'
  )

  [[ -z "$selected" ]] && exit 0

  local proj_path
  proj_path=$(printf '%s' "$selected" | cut -f2)
  _launch "$proj_path"
}

[[ -z "${_P_LAUNCH_TEST:-}" ]] && main "$@"
