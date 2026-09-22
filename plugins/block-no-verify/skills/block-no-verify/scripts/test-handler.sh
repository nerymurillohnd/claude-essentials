#!/usr/bin/env bash
# Behavioral test suite for the block-no-verify handler.
#
# Usage: test-handler.sh [HANDLER_PATH]
#   HANDLER_PATH defaults to the template next to this skill. The installer
#   passes the installed copy, so the suite proves what actually runs.
#   BNV_TEST_BASH selects the bash binary that runs the handler (default: bash),
#   e.g. BNV_TEST_BASH=/bin/bash to exercise macOS bash 3.2.
#
# Exit 0 when every case passes, 1 otherwise. Needs bash and jq.
#
# Test inputs are literal shell commands handed to the handler as data: any $,
# backtick or double quote in them is escaped, so nothing expands here.

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
handler=${1:-"${here}/../assets/block-no-verify.sh"}
runner=${BNV_TEST_BASH:-bash}
pass=0
fail=0
section=""

if [[ ! -f ${handler} ]]; then
  printf 'test-handler: handler not found: %s\n' "${handler}" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  printf 'test-handler: jq is required\n' >&2
  exit 1
fi

run_raw() { # stdin payload -> ALLOW | DENY | ERROR:<rc>
  local out rc decision=""
  out=$("${runner}" "${handler}" 2>/dev/null)
  rc=$?
  if ((rc == 2)); then
    decision=$(printf '%s' "${out}" | jq -r '.hookSpecificOutput.permissionDecision' 2>/dev/null) || decision=""
  fi
  if ((rc == 0)) && [[ -z ${out} ]]; then
    printf 'ALLOW'
  elif ((rc == 2)) && [[ ${decision} == deny ]]; then
    printf 'DENY'
  else
    printf 'ERROR:%s' "${rc}"
  fi
}

record() { # expected got label
  if [[ $1 == "$2" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL [%s] expected %s got %s :: %s\n' "${section}" "$1" "$2" "$3"
  fi
}

want() { # want ALLOW|DENY <command> [tool]
  local got
  got=$(jq -nc --arg c "$2" --arg t "${3:-Bash}" '{hook_event_name:"PreToolUse",tool_name:$t,tool_input:{command:$c}}' | run_raw)
  record "$1" "${got}" "$2"
}

want_raw() { # want_raw ALLOW|DENY <raw stdin> <label>
  local got
  got=$(printf '%s' "$2" | run_raw)
  record "$1" "${got}" "$3"
}

want_cwd() { # want_cwd ALLOW|DENY <cwd> <command>
  local got
  got=$(jq -nc --arg c "$3" --arg d "$2" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$d,tool_input:{command:$c}}' | run_raw)
  record "$1" "${got}" "$3 (cwd $2)"
}

section="direct flags"
want DENY 'git commit -m "x" --no-verify'
want DENY 'git commit --no-verify -m "x"'
want DENY 'git push --no-verify origin main'
want DENY 'git merge --no-verify feature'
want DENY 'git rebase --no-verify main'
want DENY 'git am --no-verify < patch.mbox'
want DENY 'git pull --no-verify'
want DENY 'git commit --no-gpg-sign -m "x"'
want DENY 'git merge --no-gpg-sign feature'
want DENY 'git cherry-pick --no-gpg-sign abc123'
want DENY 'git tag --no-sign v1.0.0 -m "release"'
want DENY 'git commit -m x --no-verify=true'

section="abbreviations git accepts"
want DENY 'git commit --no-verif -m x'
want DENY 'git commit --no-veri -m x'
want DENY 'git commit --no-v -m x'
want DENY 'git commit --no-gpg -m x'
want DENY 'git tag --no-si v1 -m x'
want ALLOW 'git commit --no-edit'
want ALLOW 'git tag --no-column'

section="short -n"
want DENY 'git commit -n -m "x"'
want DENY 'git commit -anm "wip"'
want DENY 'git commit -nm "wip"'
want DENY 'git commit -vn'
want DENY 'git am -n patch.mbox'
want ALLOW 'git commit -am "fix -n handling"'
want ALLOW 'git commit -m -n'
want ALLOW 'git commit -mn'
want ALLOW 'git push -n origin main'
want ALLOW 'git merge -n feature'
want ALLOW 'git rebase -n main'
want ALLOW 'git cherry-pick -n abc123'
want ALLOW 'git revert -n HEAD'
want ALLOW 'git log -n 5'
want ALLOW 'git commit -F msg.txt -S'
section="short -n after a value option"
want DENY 'git commit -C HEAD -n'

section="messages never trigger"
want ALLOW 'git commit -m "docs: explain --no-verify"'
want ALLOW "git commit -m 'refuse -c commit.gpgsign=false and HUSKY=0'"
want ALLOW 'git commit -m"mention --no-gpg-sign"'
want ALLOW 'git commit --message="skip --no-verify" --signoff'
want ALLOW 'git commit --message "skip --no-verify"'
want ALLOW 'git commit -F - <<EOF
feat: block --no-verify and git commit -n
EOF'
want ALLOW "git commit -F - <<'EOF'
HUSKY=0 git commit --no-verify
EOF"
want ALLOW 'git commit -m "say \"--no-verify\" loudly"'
want ALLOW "git commit -m \"\$(printf \"%s\" \"fix: allow -n in docs\")\""
want ALLOW 'echo "git commit --no-verify" > notes.txt'
want ALLOW 'grep -rn -- "--no-verify" docs/'
want ALLOW 'git log --grep="--no-verify"'
want ALLOW 'git commit -m x -- --no-verify'

section="chains and lists"
want DENY 'git add . && git commit -m "x" --no-verify'
want DENY 'ls; git commit --no-verify -m x'
want DENY 'false || git commit --no-verify -m x'
want DENY 'git status | git commit --no-verify -m x'
want DENY 'git add .
git commit --no-verify -m x'
want DENY 'sleep 1 & git commit --no-verify -m x'
want DENY '(cd repo && git commit --no-verify -m x)'
want DENY '{ git commit --no-verify -m x; }'
want DENY 'if true; then git commit --no-verify -m x; fi'
want DENY 'git commit --no-verify -m x 2>&1 | tail -5'
want ALLOW 'git add . && git commit -m "x" && git push'

section="wrappers and paths"
for w in sudo env nice nohup 'timeout 5' 'timeout -s KILL 5' xargs command builtin noglob watch time exec 'nice -n 10' 'sudo -u root' 'env -i' 'stdbuf -oL' 'doas' 'caffeinate -i' 'flock /tmp/lock'; do
  want DENY "${w} git commit --no-verify -m x"
done
want DENY '/usr/bin/git commit --no-verify -m x'
want DENY '/opt/homebrew/bin/git commit -n -m x'
want DENY 'GIT commit --no-verify -m x'
want DENY 'Git commit -n -m x'
want DENY 'g\it commit --no-verify -m x'
want DENY "g''it commit --no-verify -m x"
want DENY "\$'\\x67it' commit --no-verify -m x"
want DENY '/usr/libexec/git-core/git-commit --no-verify -m x'
want DENY 'find . -name x -exec git commit --no-verify -m x \;'
want DENY 'sudo env GIT_AUTHOR_NAME=x nice git commit --no-verify -m x'
want ALLOW 'sudo git log'
want ALLOW 'timeout 5 git status'
want ALLOW 'env FOO=bar git status'
want ALLOW 'cd git && ls'
want ALLOW 'gitk --all'
want ALLOW 'github-release --no-verify'

section="global options"
want DENY 'git -C repo commit --no-verify -m x'
want DENY 'git --git-dir=.git --work-tree=. commit -n -m x'
want DENY 'git -p --no-pager commit --no-verify -m x'
want DENY 'git -C "my repo" commit --no-verify -m x'
want ALLOW 'git -C repo status'
want ALLOW 'git --no-pager log --oneline -n 3'

section="config overrides"
want DENY 'git -c commit.gpgsign=false commit -m x'
want DENY 'git -c commit.gpgSign=FALSE commit -m x'
for v in no off 0 00 NO Off '' 0k; do
  want DENY "git -c commit.gpgsign=${v} commit -m x"
done
want DENY 'git -c tag.gpgsign=false tag -a v1 -m x'
want DENY 'git -c core.hooksPath=/dev/null commit -m x'
want DENY 'git -c core.hooksPath= commit -m x'
want DENY 'git -c core.hookspath=/tmp/empty commit -m x'
want DENY "git -c 'core.hooksPath=/dev/null' commit -m x"
want DENY 'git -ccore.hooksPath=/dev/null commit -m x'
want DENY 'git --config commit.gpgsign=false commit -m x'
want DENY 'git --config=commit.gpgsign=false commit -m x'
want DENY 'git --config-env=core.hooksPath=EMPTY commit -m x'
want DENY 'git --config-env commit.gpgsign=NOPE commit -m x'
want DENY 'git -c gpg.program=true commit -m x'
want DENY 'git -c gpg.ssh.program=/tmp/fake commit -m x'
want DENY 'git -c include.path=/tmp/evil.cfg commit -m x'
want DENY 'git -c alias.ci="commit --no-verify" ci -m x'
want DENY "git -c alias.ci='!git commit -n' ci -m x"
want ALLOW 'git -c commit.gpgsign=true commit -m x'
want ALLOW 'git -c commit.gpgsign commit -m x'
want ALLOW 'git -c color.ui=always status'
# git rejects values that are not booleans, so anything not clearly true is denied.
want DENY 'git -c commit.gpgsign=funky commit -m x'
want ALLOW 'git -c alias.st=status st'
want ALLOW 'git -c user.name=bot commit -m x'

section="persistent git config"
want DENY 'git config core.hooksPath /dev/null'
want DENY 'git config --local core.hooksPath ""'
want DENY 'git config set core.hooksPath /tmp/none'
want DENY 'git config --global commit.gpgsign false'
want DENY 'git config --bool commit.gpgsign no'
want DENY 'git config --type=bool tag.gpgsign off'
want DENY 'git config --unset core.hooksPath'
want DENY 'git config unset commit.gpgsign'
want DENY 'git config --unset-all core.hookspath'
want DENY 'git config --remove-section core'
want DENY 'git config rename-section commit old'
want DENY 'git config alias.ci "commit --no-verify"'
want DENY 'git config gpg.program /usr/bin/true'
want ALLOW 'git config core.hooksPath'
want ALLOW 'git config --get core.hooksPath'
want ALLOW 'git config get commit.gpgsign'
want ALLOW 'git config --list'
want ALLOW 'git config commit.gpgsign true'
want ALLOW 'git config user.email dev@example.com'
want ALLOW 'git config --unset user.signingkey.backup'

section="environment bypasses"
want DENY 'HUSKY=0 git commit -m x'
want DENY 'env HUSKY=0 git commit -m x'
want DENY 'sudo HUSKY=0 git commit -m x'
want DENY 'export HUSKY=0; git commit -m x'
want DENY 'export HUSKY=0 && git commit -m x'
want DENY 'HUSKY=0; git commit -m x'
want DENY 'declare -x HUSKY=0; git commit -m x'
want DENY 'HUSKY_SKIP_HOOKS=1 git commit -m x'
want DENY 'SKIP=eslint git commit -m x'
want DENY 'SKIP=ruff,mypy git commit -m x'
want DENY 'PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m x'
want DENY 'LEFTHOOK=0 git commit -m x'
want DENY 'LEFTHOOK=false git commit -m x'
want DENY 'LEFTHOOK_EXCLUDE=lint git commit -m x'
want DENY 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m x'
want DENY 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false git commit -m x'
want DENY "GIT_CONFIG_PARAMETERS=\"'core.hooksPath'='/dev/null'\" git commit -m x"
want DENY 'GIT_CONFIG_GLOBAL=/dev/null git commit -m x'
want DENY 'GIT_CONFIG_NOSYSTEM=1 git commit -m x'
want DENY 'HOME=/tmp git commit -m x'
want DENY 'XDG_CONFIG_HOME=/tmp git commit -m x'
want ALLOW 'HUSKY=1 git commit -m x'
want ALLOW 'LEFTHOOK=1 git commit -m x'
want ALLOW 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=user.name GIT_CONFIG_VALUE_0=bot git commit -m x'
want ALLOW 'GIT_AUTHOR_NAME=bot git commit -m x'
want ALLOW 'HUSKY=0 npm install'
want ALLOW 'export SKIP=1; npm test'

section="nested shells"
want DENY 'bash -c "git commit --no-verify -m x"'
want DENY "sh -c 'git commit -n -m x'"
want DENY 'bash -lc "git commit --no-verify -m x"'
want DENY 'bash -o pipefail -c "git commit --no-verify -m x"'
want DENY 'zsh -c "HUSKY=0 git commit -m x"'
want DENY 'HUSKY=0 bash -c "git commit -m x"'
want DENY "sudo sh -c 'cd repo && git commit --no-verify -m x'"
want DENY 'bash -c "bash -c \"git commit --no-verify -m x\""'
want DENY 'eval "git commit --no-verify -m x"'
want DENY 'env -S "git commit --no-verify -m x"'
want DENY 'watch "git commit --no-verify -m x"'
want DENY 'su -c "git commit --no-verify -m x"'
want DENY 'bash <<EOF
git commit --no-verify -m x
EOF'
want DENY 'bash <<< "git commit --no-verify -m x"'
want DENY 'echo "git commit --no-verify -m x" | bash'
want DENY 'pwsh -Command "git commit --no-verify -m x"'
want ALLOW 'bash -c "git status"'
want ALLOW 'sh -c "echo hi"'
want ALLOW 'bash ./scripts/release.sh'
want ALLOW 'echo "git status" | bash'

section="substitutions"
want DENY "echo \$(git commit --no-verify -m x)"
want DENY "out=\`git commit -n -m x\`"
want DENY 'cat <(git commit --no-verify -m x)'
want DENY "cd \"\$(git rev-parse --show-toplevel)\" && git commit --no-verify -m x"
want ALLOW "cd \"\$(git rev-parse --show-toplevel)\" && git status"
want ALLOW "echo \"\$(git log -1 --format=%s)\""

section="git string-command entry points"
want DENY 'git rebase -x "git commit --amend --no-verify" main'
want DENY 'git rebase --exec="git commit --amend -n" main'
want DENY "git submodule foreach 'git commit --no-verify -m x'"
want ALLOW 'git rebase -x "npm test" main'
want ALLOW 'git submodule foreach git status'

section="opaque constructs"
want DENY "F=--no-verify; \$GIT commit \$F -m x"
want DENY "git\${IFS}commit\${IFS}--no-verify"
want DENY 'echo --no-verify | xargs git commit -m x'
want ALLOW "FLAG=--quiet; git commit \$FLAG -m x"
want ALLOW 'git ls-files | xargs -n1 git log -1 --format=%h --'

section="powershell"
want DENY 'git commit --no-verify -m "x"' PowerShell
want DENY 'git commit -n -m "x"' PowerShell
want DENY '& git commit --no-verify -m x' PowerShell
want DENY '& "C:\Program Files\Git\cmd\git.exe" commit --no-verify -m x' PowerShell
want DENY 'git.exe -c core.hooksPath=NUL commit -m x' PowerShell
want DENY "\$env:HUSKY = \"0\"; git commit -m x" PowerShell
want DENY "\$env:HUSKY=\"0\"; git commit -m x" PowerShell
want DENY 'Set-Location repo; git commit --no-verify -m x' PowerShell
want DENY 'powershell -c "git commit --no-verify -m x"' PowerShell
want DENY 'bash -c "git commit --no-verify -m x"' PowerShell
want ALLOW "git commit -m 'it''s --no-verify in text'" PowerShell
want ALLOW "git commit -m \"tick \`\"--no-verify\`\" text\"" PowerShell
want ALLOW "\$msg = @\"
explain --no-verify
\"@
git commit -m \$msg" PowerShell
want ALLOW 'git status; git log -n 3' PowerShell
want ALLOW '<# git commit --no-verify #> git status' PowerShell

section="push with force and other modes"
want DENY 'git push --force --no-verify origin main'
want DENY 'git push -f --no-verify origin main'
want DENY 'git push --no-verify --force-with-lease origin HEAD'
want DENY 'git push -uf origin HEAD --no-verify'
want DENY 'git push --mirror --no-verify backup'
want DENY 'git push --no-veri --force origin main'
want DENY 'git push --tags --no-verify'
want DENY 'HUSKY=0 git push --force origin main'
want DENY 'git -c core.hooksPath=/dev/null push -f origin main'
want DENY 'SKIP=pre-push git push origin main'
want ALLOW 'git push --force-with-lease origin HEAD'
want ALLOW 'git push -f origin main'
want ALLOW 'git push -n --force origin main'

section="commit messages built with heredocs (Claude Code's own form)"
want ALLOW "git commit -m \"\$(cat <<'EOF'
fix: don't skip hooks; it's \`critical\`
EOF
)\""
want ALLOW "gh pr create --title x --body \"\$(cat <<'EOF'
## Summary
Blocks --no-verify and HUSKY=0; don't bypass hooks.
EOF
)\""
want ALLOW "git commit -m \"\$(cat <<'EOF'
docs: explain --no-verify and core.hooksPath
EOF
)\" && git push"
want DENY "git commit --no-verify -m \"\$(cat <<'EOF'
fix: don't
EOF
)\""
want ALLOW "cat > notes.md <<EOF
Ran \$(date) without --no-verify
EOF"
want DENY "cat > notes.md <<EOF
\$(git commit --no-verify -m x)
EOF"

section="expansions that build flags (red-team regressions)"
want DENY "git commit \$(echo --no-verify) -m x"
want DENY "git commit \`echo --no-verify\` -m x"
want DENY "F=--no-verify; git commit \$F -m x"
want DENY 'set -- --no-verify; git commit "$@" -m x'
want DENY 'git commit --no-{verify,} -m x'
want DENY 'git commit --{no-verify,} -m x'
want DENY '=git commit --no-verify -m x'
want DENY "\$'\\u0067it' commit --no-verify -m x"
want DENY 'git -c commit.gpgsign=0x0 commit -m x'
want DENY "git -c 'commit.gpgsign= 0' commit -m x"
want DENY 'git -c tag.forceSignAnnotated=false tag -a v1 -m x'
want DENY 'git commit-tree HEAD^{tree} -p HEAD -m x'
want DENY "GIT_EDITOR='git commit -n -m x' git rebase -i HEAD~1"
want DENY "EDITOR='sh -c \"git commit --no-verify -m x\"' git commit"
want DENY "git -c core.editor='git commit --no-verify -m x' commit"
want DENY "git -c core.sshCommand='sh -c \"git commit -n -m x\"' push"
want DENY 'SKIP_SIMPLE_GIT_HOOKS=1 git commit -m x'
want DENY 'OVERCOMMIT_DISABLE=1 git commit -m x'
want ALLOW "git commit -m \"\$(date +%F) release\""
want ALLOW "git commit -m \"\$MSG\""
want ALLOW "MSG=\"about --no-verify\"; git commit -m \"\$MSG\""
want ALLOW 'GIT_EDITOR=true git rebase --continue'
want ALLOW "\$EDITOR notes.txt; git commit -m \"docs: explain --no-verify\""
want ALLOW 'HOME=/tmp/x git status'
want ALLOW 'git -c commit.gpgsign=on commit -m x'
want ALLOW 'git -c commit.gpgsign=0x1 commit -m x'

section="persistent hooks setup stays allowed"
want ALLOW 'git config core.hooksPath .githooks'
want ALLOW 'git config core.hooksPath .husky/_'
want ALLOW 'git config --global include.path ~/.gitconfig.local'
want DENY 'git config core.hooksPath ../elsewhere'
want DENY 'git config core.hooksPath ~/empty'
want DENY 'git config core.hooksPath NUL'
want DENY 'git -c include.path=~/.gitconfig.local commit -m x'

section="hook files and hook managers"
want DENY 'rm .git/hooks/pre-commit'
want DENY 'rm -f .husky/pre-commit'
want DENY 'rm -rf .husky'
want DENY 'chmod -x .git/hooks/pre-push'
want DENY 'chmod 644 .husky/pre-commit'
want DENY 'chmod a-x .git/hooks/commit-msg'
want DENY 'mv .git/hooks .git/hooks.off'
want DENY 'mv .pre-commit-config.yaml /tmp/'
want DENY 'rm lefthook.yml'
want DENY 'pre-commit uninstall'
want DENY 'lefthook uninstall'
want DENY 'npx husky uninstall'
want ALLOW 'chmod +x .husky/pre-commit'
want ALLOW 'chmod 755 .git/hooks/pre-commit'
want ALLOW 'chmod -R +x .husky'
want ALLOW 'cp scripts/pre-commit .git/hooks/pre-commit'
want ALLOW 'mv /tmp/pre-commit .git/hooks/pre-commit'
want ALLOW 'pre-commit install'
want ALLOW 'pre-commit run --all-files'
want ALLOW 'lefthook run pre-commit'
want ALLOW 'cat .husky/pre-commit'

section="aliases from the repository's configuration"
alias_repo=$(mktemp -d)
git -C "${alias_repo}" init -q
git -C "${alias_repo}" config alias.ci commit
git -C "${alias_repo}" config alias.sh '!git commit --no-verify'
want_cwd DENY "${alias_repo}" 'git ci -n -m x'
want_cwd DENY "${alias_repo}" 'git ci -anm x'
want_cwd DENY "${alias_repo}" 'git sh'
want_cwd ALLOW "${alias_repo}" 'git ci -m x'
want_cwd ALLOW "${alias_repo}" 'git lfs ls-files -n'
rm -rf "${alias_repo}"

section="large inputs stay correct (and must finish well inside the hook timeout)"
big_body=$(yes "line of text; don't stop, it's fine with --no-verify in prose" | head -700)
want ALLOW "git commit -F - <<'EOF'
${big_body}
EOF"
want ALLOW "git commit -m \"\$(cat <<'EOF'
${big_body}
EOF
)\""
want DENY "git commit --no-verify -m \"\$(cat <<'EOF'
${big_body}
EOF
)\""
big_files=$(yes 'file.txt' | head -3000 | tr '\n' ' ')
want ALLOW "git add ${big_files} && git commit -m x"
want DENY "git add ${big_files} && git commit --no-verify -m x"

section="without jq (only the command decides, never cwd or transcript paths)"
nojq=$(mktemp -d)
for tool in bash tr; do
  tool_path=$(command -v "${tool}") || tool_path=""
  ln -s "${tool_path}" "${nojq}/${tool}"
done
nojq_verdict() { # nojq_verdict <command> <cwd>
  local payload out rc
  payload=$(jq -nc --arg c "$1" --arg d "$2" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$d,transcript_path:($d + "/t.jsonl"),tool_input:{command:$c}}')
  out=$(printf '%s' "${payload}" | PATH="${nojq}" "${runner}" "${handler}" 2>/dev/null)
  rc=$?
  if ((rc == 0)) && [[ -z ${out} ]]; then printf 'ALLOW'; elif ((rc == 2)); then printf 'DENY'; else printf 'ERROR:%s' "${rc}"; fi
}
want_nojq() { # want_nojq ALLOW|DENY <command> <cwd>
  local got
  got=$(nojq_verdict "$2" "$3") || got=ERROR
  record "$1" "${got}" "no jq: $2 (cwd $3)"
}
want_nojq ALLOW 'ls -la' /Users/me/github/app
want_nojq ALLOW 'npm test' /home/me/git/project
want_nojq DENY 'git commit -m x' /tmp/app
want_nojq DENY 'echo "x"; GIT status' /tmp/app
other=ALLOW
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"/x/github/y"}}' | PATH="${nojq}" "${runner}" "${handler}" >/dev/null 2>&1 || other=DENY
record ALLOW "${other}" "no jq: other tools pass"
rm -rf "${nojq}"

section="fail closed"
want_raw DENY 'not json' 'invalid JSON'
want_raw DENY '' 'empty stdin'
want_raw DENY '[1,2]' 'non-object payload'
want DENY 'git commit -m "unterminated'
want DENY "git commit -m 'unterminated"
want DENY "git commit -m \$(echo x"
want DENY 'echo `git commit -n'

section="pass through"
want_raw ALLOW '{"tool_name":"Bash"}' 'no tool_input'
want_raw ALLOW '{"tool_name":"Bash","tool_input":{"command":42}}' 'non-string command'
want_raw ALLOW '{"tool_name":"Write","tool_input":{"file_path":"x","content":"git commit --no-verify"}}' 'other tool'
want_raw ALLOW '{"tool_name":"Read","tool_input":{"command":"git commit --no-verify"}}' 'non-shell tool with a command field'
want ALLOW 'npm test'
want ALLOW 'ls -la # git commit --no-verify'

version=$("${runner}" -c "printf %s \"\${BASH_VERSION}\"") || version=unknown
printf '\n%d passed, %d failed (handler: %s, bash: %s)\n' "${pass}" "${fail}" "${handler}" "${version}"
if ((fail)); then
  echo FAIL
  exit 1
fi
echo PASS
