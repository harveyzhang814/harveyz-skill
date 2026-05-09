#!/usr/bin/env zsh
# p-launch — interactive project launcher
# Usage: p-launch              launch picker
#        p-launch --config     set project directories
#        p-launch --uninstall  remove everything
#        p-launch --help       show help

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_DIRS=()
# Define PROJECT_DIRS in ~/.config/p-launch/config.zsh (written by installer)
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
# Output: "PADDED_NAME \t PATH \t DISPLAY_PARENT" per line (name padded for alignment)
_format() {
  local -a names=() paths=() parents=()
  while IFS= read -r p; do
    names+=("${p:t}")
    paths+=("$p")
    parents+=("${${p:h}/$HOME/~}")
  done

  local maxlen=0
  local n
  for n in "${names[@]}"; do
    (( ${#n} > maxlen )) && maxlen=${#n}
  done

  local i
  for (( i = 1; i <= ${#names}; i++ )); do
    printf "%-${maxlen}s\t%s\t%s\n" "${names[$i]}" "${paths[$i]}" "${parents[$i]}"
  done
}

# ── Launch ───────────────────────────────────────────────────────────────────
_launch() {
  local path="$1"
  local name="${path:t}"
  local display="${path/$HOME/~}"
  local cursor_ok=false ghostty_ok=false ghostty_err="not installed"

  # Cursor IDE — CLI first, fall back to .app
  if command -v cursor &>/dev/null; then
    cursor "$path" &>/dev/null &
    cursor_ok=true
  elif [[ -d "/Applications/Cursor.app" ]]; then
    /usr/bin/open -na "Cursor" --args "$path" && cursor_ok=true
  fi

  # Ghostty — find app via Spotlight (handles /Applications, ~/Applications,
  # or any custom install path), then invoke "New Ghostty Window Here" service
  # via NSPerformService — same code path as Finder right-click service.
  local ghostty_app
  ghostty_app=$(mdfind "kMDItemCFBundleIdentifier == 'com.mitchellh.ghostty'" 2>/dev/null | /usr/bin/head -1)
  if [[ -z "$ghostty_app" ]]; then
    # mdfind can miss apps before first Spotlight index; fall back to known paths
    for _p in "/Applications/Ghostty.app" "$HOME/Applications/Ghostty.app"; do
      [[ -d "$_p" ]] && { ghostty_app="$_p"; break }
    done
  fi

  if [[ -n "$ghostty_app" ]]; then
    ghostty_err="failed to open"
    # Ghostty's service handler does dirname on the path, so pass a child of
    # the target dir — dirname(target/child) == target.
    local _child service_path
    _child=$(/bin/ls -1A "$path" 2>/dev/null | /usr/bin/head -1)
    service_path="${path}/${_child}"
    /usr/bin/osascript 2>/dev/null <<OSASCRIPT && ghostty_ok=true
use framework "AppKit"
use scripting additions
set thePboard to current application's NSPasteboard's generalPasteboard()
thePboard's clearContents()
thePboard's setPropertyList:{"${service_path}"} forType:"NSFilenamesPboardType"
return current application's NSPerformService("New Ghostty Window Here", thePboard)
OSASCRIPT
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
    printf "  ${C[yl]}⚠${C[rs]} Ghostty  %s\n" "$ghostty_err"
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

# ── Config ───────────────────────────────────────────────────────────────────
_config() {
  local config_file="$HOME/.config/p-launch/config.zsh"

  printf '\n'
  printf "  ${C[bd]}p-launch config${C[rs]}\n\n"

  # Show current dirs
  if [[ -f "$config_file" ]]; then
    printf "  ${C[cy]}Current PROJECT_DIRS:${C[rs]}\n"
    source "$config_file"
    if (( ${#PROJECT_DIRS[@]} > 0 )); then
      for d in "${PROJECT_DIRS[@]}"; do
        printf "    ${C[dim]}%s${C[rs]}\n" "$d"
      done
    else
      printf "    ${C[dim]}(none)${C[rs]}\n"
    fi
  else
    printf "  ${C[yl]}No config file found.${C[rs]}\n"
  fi

  printf '\n'
  printf "  Enter project dirs, one per line. Empty line when done.\n"
  printf "  ${C[dim]}(leave blank to keep current)${C[rs]}\n\n"

  local -a new_dirs=()
  local line
  local idx=1
  while true; do
    printf "  Dir %d: " "$idx"
    read -r line
    [[ -z "$line" ]] && break
    new_dirs+=("$line")
    (( idx++ ))
  done

  if (( ${#new_dirs[@]} == 0 )); then
    printf '\n  No changes made.\n\n'
    return
  fi

  mkdir -p "${config_file:h}"
  {
    printf 'PROJECT_DIRS=(\n'
    for d in "${new_dirs[@]}"; do
      printf '  "%s"\n' "$d"
    done
    printf ')\n'
  } > "$config_file"

  printf '\n'
  printf "  ${C[gr]}✓${C[rs]} Saved to ${config_file/$HOME/~}\n"
  printf '\n'
  printf "  ${C[cy]}New PROJECT_DIRS:${C[rs]}\n"
  for d in "${new_dirs[@]}"; do
    printf "    ${C[dim]}%s${C[rs]}\n" "$d"
  done
  printf '\n'
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    printf '\n'
    printf "  ${C[bd]}p-launch${C[rs]} — interactive project launcher\n\n"
    printf "  ${C[cy]}Usage:${C[rs]}\n"
    printf "    p-launch               open project picker\n"
    printf "    p-launch --config      set project directories\n"
    printf "    p-launch --uninstall   remove all installed files\n"
    printf "    p-launch --help        show this help\n\n"
    printf "  ${C[cy]}Config:${C[rs]}\n"
    printf "    ~/.config/p-launch/config.zsh   define PROJECT_DIRS\n\n"
    printf "  ${C[cy]}Dependencies:${C[rs]}\n"
    printf "    fzf   brew install fzf\n\n"
    return
  fi

  if [[ "$1" == "--config" || "$1" == "config" ]]; then
    _config
    return
  fi

  if [[ "$1" == "--uninstall" || "$1" == "uninstall" ]]; then
    _uninstall
    return
  fi

  _check_deps

  local projects
  projects=$(_collect) || {
    printf "${C[yl]}no projects found${C[rs]} — check PROJECT_DIRS in ~/.config/p-launch/config.zsh\n"
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
