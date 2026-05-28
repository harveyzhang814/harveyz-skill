#!/usr/bin/env zsh
# p-launch — local repository manager
# Usage: p-launch              open repository manager
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

# ── Git Status Detection ─────────────────────────────────────────────────────

# Returns 0 if _dir is a git repo with at least one remote, 1 otherwise.
# NOTE: Do NOT use 'path' as a local variable name — in zsh, $path is the
# special array form of $PATH, and shadowing it breaks command lookup.
_is_git_with_remote() {
  local _dir="$1"
  git -C "$_dir" rev-parse --git-dir >/dev/null 2>&1 || return 1
  git -C "$_dir" remote | grep -q . || return 1
}

# Outputs all tracking branches and their ahead/behind status
# Format: "branch|upstream|[ahead N, behind M]"
_get_tracking_branch_statuses() {
  local _dir="$1"
  git -C "$_dir" for-each-ref \
    --format='%(refname:short)|%(upstream:short)|%(upstream:track)' \
    refs/heads | awk -F'|' '$2 != ""'
}

# Derives a short hash key for a path (used as status file name)
_path_key() {
  printf '%s' "$1" | shasum -a 256 | cut -c1-16
}

# Computes the status summary and writes it to $tmpdir/<key>
# Status format (8-char wide): "↑N↓M    ", "✓       ", "·       ", etc.
_write_status_file() {
  local _dir="$1" tmpdir="$2"
  local key
  key=$(_path_key "$_dir")

  if ! _is_git_with_remote "$_dir"; then
    printf '·       ' > "${tmpdir}/${key}"
    return 0
  fi

  local total_ahead=0 total_behind=0
  local branch upstream track ahead behind

  while IFS='|' read -r branch upstream track; do
    # Skip [gone] upstreams
    [[ "$track" == *gone* ]] && continue
    ahead=0; behind=0
    [[ "$track" =~ 'ahead ([0-9]+)' ]] && ahead="${match[1]}"
    [[ "$track" =~ 'behind ([0-9]+)' ]] && behind="${match[1]}"
    (( total_ahead  += ahead  ))
    (( total_behind += behind ))
  done < <(_get_tracking_branch_statuses "$_dir")

  local s=""
  (( total_ahead  > 0 )) && s+="↑${total_ahead}"
  (( total_behind > 0 )) && s+="↓${total_behind}"
  [[ -z "$s" ]] && s="✓"

  # Pad to 8 chars for alignment
  printf '%-8s' "$s" > "${tmpdir}/${key}"
}

# Fetch a single repo and write its status file (runs in background)
_fetch_and_write_status() {
  local _dir="$1" tmpdir="$2"
  git -C "$_dir" fetch --all -q 2>/dev/null
  _write_status_file "$_dir" "$tmpdir"
}

# Parallel-fetch all git repos and populate status files in tmpdir
_fetch_all_repos() {
  local tmpdir="$1"
  shift
  local -a dirs=("$@")
  local -a pids=()

  for dir in "${dirs[@]}"; do
    if _is_git_with_remote "$dir"; then
      ( _fetch_and_write_status "$dir" "$tmpdir" ) &
      pids+=($!)
    else
      # Write · immediately for non-git dirs (no background needed)
      local key; key=$(_path_key "$dir")
      printf '·       ' > "${tmpdir}/${key}"
    fi
  done

  for pid in "${pids[@]}"; do
    wait "$pid"
  done
  return 0
}

# ── fzf Display Formatting ───────────────────────────────────────────────────
# Input:  one path per line (stdin)
# Output: "STATUS \t PADDED_NAME \t PATH \t DISPLAY_PARENT" per line
_format_with_status() {
  local tmpdir="${_STATUS_TMPDIR:-}"
  local -a statuses=() names=() rawpaths=() parents=()

  local key _status
  while IFS= read -r p; do
    key=$(_path_key "$p")
    if [[ -n "$tmpdir" && -f "${tmpdir}/${key}" ]]; then
      _status=$(cat "${tmpdir}/${key}")
    else
      _status='·       '
    fi
    statuses+=("$_status")
    names+=("${p:t}")
    rawpaths+=("$p")
    parents+=("${${p:h}/$HOME/~}")
  done

  local maxlen=0
  local n
  for n in "${names[@]}"; do
    if (( ${#n} > maxlen )); then
      maxlen=${#n}
    fi
  done

  local i
  for (( i = 1; i <= ${#names}; i++ )); do
    printf "%s\t%-${maxlen}s\t%s\t%s\n" \
      "${statuses[$i]}" "${names[$i]}" "${rawpaths[$i]}" "${parents[$i]}"
  done
  return 0
}

# ── Pull / Push Operations ───────────────────────────────────────────────────

_do_pull() {
  local _dir="$1"
  local name="${_dir:t}"
  local current_branch
  current_branch=$(git -C "$_dir" symbolic-ref --short HEAD 2>/dev/null)

  printf '\n'
  printf "  ${C[bd]}${C[cy]}%s${C[rs]}  ${C[dim]}pull${C[rs]}\n\n" "$name"

  local any=false
  local branch upstream track behind

  while IFS='|' read -r branch upstream track; do
    [[ "$track" == *gone* ]] && continue
    behind=0
    [[ "$track" =~ 'behind ([0-9]+)' ]] && behind="${match[1]}"
    (( behind == 0 )) && continue

    any=true
    if [[ "$branch" == "$current_branch" ]]; then
      if git -C "$_dir" pull --ff-only origin "$branch" >/dev/null 2>&1; then
        printf "  ${C[gr]}✓${C[rs]} pulled       %s\n" "$branch"
      else
        printf "  ${C[yl]}⚠${C[rs]} pull failed  %s (resolve conflicts manually)\n" "$branch"
      fi
    else
      # Non-current branch: fast-forward only via fetch refspec
      if git -C "$_dir" fetch origin "${branch}:${branch}" >/dev/null 2>&1; then
        printf "  ${C[gr]}✓${C[rs]} fast-fwd     %s\n" "$branch"
      else
        printf "  ${C[yl]}⚠${C[rs]} skipped      %s (not fast-forward)\n" "$branch"
      fi
    fi
  done < <(_get_tracking_branch_statuses "$_dir")

  if ! $any; then
    printf "  ${C[dim]}nothing to pull — all branches up to date${C[rs]}\n"
  fi

  printf '\n'

  # Refresh status file after pull (using cached remote refs, no network)
  if [[ -n "${_STATUS_TMPDIR:-}" ]]; then
    _write_status_file "$_dir" "$_STATUS_TMPDIR"
  fi
  return 0
}

_do_push() {
  local _dir="$1"
  local name="${_dir:t}"

  printf '\n'
  printf "  ${C[bd]}${C[cy]}%s${C[rs]}  ${C[dim]}push${C[rs]}\n\n" "$name"

  local any=false
  local branch upstream track ahead

  while IFS='|' read -r branch upstream track; do
    [[ "$track" == *gone* ]] && continue
    ahead=0
    [[ "$track" =~ 'ahead ([0-9]+)' ]] && ahead="${match[1]}"
    (( ahead == 0 )) && continue

    any=true
    if git -C "$_dir" push origin "$branch" >/dev/null 2>&1; then
      printf "  ${C[gr]}✓${C[rs]} pushed  %s\n" "$branch"
    else
      printf "  ${C[yl]}⚠${C[rs]} failed  %s\n" "$branch"
    fi
  done < <(_get_tracking_branch_statuses "$_dir")

  if ! $any; then
    printf "  ${C[dim]}nothing to push — no branches ahead of remote${C[rs]}\n"
  fi

  printf '\n'

  if [[ -n "${_STATUS_TMPDIR:-}" ]]; then
    _write_status_file "$_dir" "$_STATUS_TMPDIR"
  fi
  return 0
}

# ── Launch ───────────────────────────────────────────────────────────────────
_launch() {
  local _dir="$1"
  local name="${_dir:t}"
  local display="${_dir/$HOME/~}"
  local cursor_ok=false ghostty_ok=false ghostty_err="not installed"

  # Cursor IDE — CLI first, fall back to .app
  if command -v cursor &>/dev/null; then
    cursor "$_dir" >/dev/null 2>&1 &
    cursor_ok=true
  elif [[ -d "/Applications/Cursor.app" ]]; then
    /usr/bin/open -na "Cursor" --args "$_dir" && cursor_ok=true
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
    _child=$(/bin/ls -1A "$_dir" 2>/dev/null | /usr/bin/head -1)
    service_path="${_dir}/${_child}"
    ${_OSASCRIPT:-/usr/bin/osascript} 2>/dev/null <<OSASCRIPT && ghostty_ok=true
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
    printf "  ${C[bd]}p-launch${C[rs]} — local repository manager\n\n"
    printf "  ${C[cy]}Usage:${C[rs]}\n"
    printf "    p-launch               open repository manager\n"
    printf "    p-launch --config      set project directories\n"
    printf "    p-launch --uninstall   remove all installed files\n"
    printf "    p-launch --help        show this help\n\n"
    printf "  ${C[cy]}Keybindings (in picker):${C[rs]}\n"
    printf "    ↵          launch project in Cursor + Ghostty\n"
    printf "    ctrl-p     pull all behind branches of selected repo\n"
    printf "    ctrl-u     push all ahead branches of selected repo\n"
    printf "    ctrl-r     refresh git status (re-fetch all)\n"
    printf "    ctrl-/     toggle file preview\n"
    printf "    esc        cancel\n\n"
    printf "  ${C[cy]}Status column:${C[rs]}\n"
    printf "    ✓       all tracking branches synced\n"
    printf "    ↑N      N commits ahead of remote (push available)\n"
    printf "    ↓N      N commits behind remote (pull available)\n"
    printf "    ↑N↓M    diverged\n"
    printf "    ·       not a git repo or no tracking branches\n\n"
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

  # Internal commands invoked from fzf bindings
  if [[ "$1" == "--_pull" ]]; then
    _do_pull "$2"
    return
  fi

  if [[ "$1" == "--_push" ]]; then
    _do_push "$2"
    return
  fi

  # Re-format without fetching (called by fzf reload after pull/push)
  # Uses _STATUS_TMPDIR env var set by the parent process
  if [[ "$1" == "--_format-no-fetch" ]]; then
    local projects
    projects=$(_collect) || exit 0
    # Recompute status files from cached remote refs (no network)
    local -a dirs=()
    while IFS= read -r p; do dirs+=("$p"); done <<< "$projects"
    for dir in "${dirs[@]}"; do
      _write_status_file "$dir" "${_STATUS_TMPDIR}"
    done
    _format_with_status <<< "$projects"
    return
  fi

  _check_deps

  local projects
  projects=$(_collect) || {
    printf "${C[yl]}no projects found${C[rs]} — check PROJECT_DIRS in ~/.config/p-launch/config.zsh\n"
    exit 0
  }

  # Parallel fetch all repos and populate status files
  _STATUS_TMPDIR=$(mktemp -d)
  trap 'rm -rf "${_STATUS_TMPDIR}"' EXIT

  printf "  ${C[dim]}Fetching repository status...${C[rs]}" >&2

  local -a dirs=()
  while IFS= read -r p; do dirs+=("$p"); done <<< "$projects"
  _fetch_all_repos "$_STATUS_TMPDIR" "${dirs[@]}"

  # Clear the "Fetching..." line
  printf "\r\033[K" >&2

  export _STATUS_TMPDIR

  # Build the reload command (embeds _STATUS_TMPDIR at launch time)
  local reload_cmd="env _STATUS_TMPDIR=${_STATUS_TMPDIR} p-launch --_format-no-fetch"

  local selected
  selected=$(
    _format_with_status <<< "$projects" | \
    fzf --ansi \
        --delimiter=$'\t' \
        --with-nth='1,2,4' \
        --nth='2,4' \
        --prompt='  › ' \
        --header=$'  p-launch  ·  ↵ launch  ·  ctrl-p pull  ·  ctrl-u push  ·  ctrl-r refresh  ·  ctrl-/ preview' \
        --height=50% \
        --layout=reverse \
        --border=rounded \
        --color='header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold' \
        --preview='ls -1 {3} 2>/dev/null' \
        --preview-window='right:30%:wrap:hidden' \
        --bind="ctrl-p:execute(p-launch --_pull {3})+reload(${reload_cmd})" \
        --bind="ctrl-u:execute(p-launch --_push {3})+reload(${reload_cmd})" \
        --bind="ctrl-r:reload(${reload_cmd})" \
        --bind='ctrl-/:toggle-preview'
  )

  [[ -z "$selected" ]] && exit 0

  local proj_path
  proj_path=$(printf '%s' "$selected" | cut -f3)
  _launch "$proj_path"
}

[[ -z "${_P_LAUNCH_TEST:-}" ]] && main "$@"
