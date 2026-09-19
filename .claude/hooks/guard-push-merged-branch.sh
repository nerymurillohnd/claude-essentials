#!/usr/bin/env bash
# PreToolUse hook (Bash): before Claude runs `git push`, denies pushing a branch
# that was published before (it has an upstream or a remote-tracking ref) but no
# longer exists on the remote. That is almost always a branch GitHub deleted when
# its PR merged, and the push would recreate it with commits `main` never gets.
# New branches (never published) and deletions pass. Read-only; one
# `git ls-remote` per pushed branch. Fails open when the remote can't be reached,
# so it is a guardrail, not a control. See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
command_text="$(jq -r '.tool_input.command // empty' <<<"${input}")"
[[ "${command_text}" == *push* ]] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="${root:-${PWD}}"
git -C "${root}" rev-parse --git-dir >/dev/null 2>&1 || exit 0

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

current="$(git -C "${root}" symbolic-ref --quiet --short HEAD 2>/dev/null)" || current=""

# check_branch <remote> <local-branch> <remote-branch>
check_branch() {
  local remote=$1 local_branch=$2 dst=$3 published="" rc=0
  [[ -n ${dst} ]] || return 0
  if [[ -n ${local_branch} ]] && git -C "${root}" config --get "branch.${local_branch}.merge" >/dev/null 2>&1; then
    published=1
  elif git -C "${root}" show-ref --verify --quiet "refs/remotes/${remote}/${dst}"; then
    published=1
  fi
  [[ -n ${published} ]] || return 0
  GIT_TERMINAL_PROMPT=0 git -C "${root}" ls-remote --exit-code --heads "${remote}" "refs/heads/${dst}" \
    >/dev/null 2>&1 || rc=$?
  # 2 = the remote answered and the branch is not there; anything else (0 found,
  # 128 unreachable) lets the push through.
  if [[ ${rc} -eq 2 ]]; then
    deny "Refusing to push '${dst}' to '${remote}': this branch was published before but no longer exists on the remote, which usually means its PR was merged and the branch deleted. Pushing would recreate it with commits that main never receives. Start a new branch from the updated main instead: git switch main && git pull --ff-only && git switch -c <new-branch> && git cherry-pick <commits>."
  fi
}

# One command line can chain several commands; look at each `git … push` segment.
nl=$'\n'
segments=${command_text//&&/${nl}}
segments=${segments//||/${nl}}
segments=${segments//;/${nl}}
segments=${segments//|/${nl}}
while IFS= read -r segment; do
  read -r -a words <<<"${segment}" || true
  [[ ${#words[@]} -gt 0 ]] || continue
  # Find `git`, skip its global options (-C <dir>, -c <k=v>, --no-pager, ...), expect `push`.
  i=0
  while [[ ${i} -lt ${#words[@]} && ${words[i]} != git ]]; do i=$((i + 1)); done
  [[ ${i} -lt ${#words[@]} ]] || continue
  i=$((i + 1))
  while [[ ${i} -lt ${#words[@]} && ${words[i]} == -* ]]; do
    case ${words[i]} in
    -C | -c | --git-dir | --work-tree | --namespace) i=$((i + 1)) ;;
    *) ;;
    esac
    i=$((i + 1))
  done
  [[ ${i} -lt ${#words[@]} && ${words[i]} == push ]] || continue
  i=$((i + 1))

  positionals=()
  skip=""
  while [[ ${i} -lt ${#words[@]} ]]; do
    word=${words[i]}
    case ${word} in
    -d | --delete | --tags | --all | --branches | --mirror | --prune) skip=1 ;;
    -o | --push-option | --receive-pack | --exec | --repo) i=$((i + 1)) ;;
    --) ;;
    -*) ;;
    *) positionals+=("${word}") ;;
    esac
    i=$((i + 1))
  done
  [[ -z ${skip} ]] || continue

  if [[ ${#positionals[@]} -gt 0 ]]; then
    remote=${positionals[0]}
  else
    remote="$(git -C "${root}" config --get "branch.${current}.remote" 2>/dev/null)" || remote=origin
  fi

  if [[ ${#positionals[@]} -le 1 ]]; then
    [[ -n ${current} ]] || continue
    merge="$(git -C "${root}" config --get "branch.${current}.merge" 2>/dev/null)" || merge=""
    dst=${merge#refs/heads/}
    check_branch "${remote}" "${current}" "${dst:-${current}}"
    continue
  fi

  for refspec in "${positionals[@]:1}"; do
    refspec=${refspec#+}
    if [[ ${refspec} == *:* ]]; then
      src=${refspec%%:*}
      dst=${refspec#*:}
      [[ -n ${src} ]] || continue # `:branch` deletes it
    else
      src=${refspec}
      dst=${refspec}
    fi
    [[ ${src} == HEAD ]] && src=${current}
    [[ ${dst} == HEAD ]] && dst=${current}
    [[ ${src} == refs/tags/* || ${dst} == refs/tags/* ]] && continue
    src=${src#refs/heads/}
    dst=${dst#refs/heads/}
    [[ ${dst} == refs/* ]] && continue
    git -C "${root}" show-ref --verify --quiet "refs/heads/${src}" || src=""
    check_branch "${remote}" "${src}" "${dst}"
  done
done <<<"${segments}"

exit 0
