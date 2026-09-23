#!/usr/bin/env bash
# Build the repo-hygiene eval fixture in the current (empty) directory: a repository in
# ./work with findings planted in every Git area, and its local bare remote ./origin.git.
# Publishes with fetch, never push. The planted tokens are fake.
set -euo pipefail

export GIT_AUTHOR_NAME=Dev GIT_AUTHOR_EMAIL=dev@example.com
export GIT_COMMITTER_NAME=Dev GIT_COMMITTER_EMAIL=dev@example.com
export GIT_CONFIG_NOSYSTEM=1

git init -q -b main work
git init -q --bare -b main origin.git
cd work
git config user.name Dev
git config user.email dev@example.com
git config commit.gpgsign false
git remote add origin ../origin.git
publish() { git -C ../origin.git fetch -q ../work "$@"; }

printf 'node_modules/\ndist/\n.env\n*.log\n' >.gitignore
echo v1 >app.txt
mkdir -p .github/workflows
printf 'on: push\njobs:\n  b:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: someorg/some-action@main\n' >.github/workflows/ci.yml
git add .
git commit -qm init
publish main:main

# G5/G6: merged, squashed, abandoned, unique branches; gone upstreams
git switch -qc feat/merged
echo m >>app.txt
git commit -qam merged
publish feat/merged:feat/merged
git switch -q main
git merge -q --no-ff feat/merged -m "merge feat/merged"
publish main:main
git switch -qc feat/squashed
echo s1 >s.txt
git add s.txt
git commit -qm s1
echo s2 >>s.txt
git commit -qam s2
publish feat/squashed:feat/squashed
git switch -q main
git merge -q --squash feat/squashed >/dev/null
git commit -qm "squash feat/squashed"
publish main:main
git switch -qc feat/abandoned
echo a >a.txt
git add a.txt
git commit -qm abandoned
publish feat/abandoned:feat/abandoned
git switch -q main
git fetch -q origin
git branch -q -u origin/feat/merged feat/merged
git branch -q -u origin/feat/squashed feat/squashed
git branch -qD feat/abandoned
git -C ../origin.git branch -qD feat/merged feat/squashed
git fetch -q --prune origin
git switch -qc wip/unique
echo u >u.txt
git add u.txt
git commit -qm unique
git switch -q main

# G16: commit lost to reset --hard
echo lost >lost.txt
git add lost.txt
git commit -qm "lost commit"
git reset -q --hard HEAD~1

# G14: secret and large blob in history
echo 'token=ghp_FAKEFAKEFAKEFAKEFAKE1234567890abcd' >config.ini
git add config.ini
git commit -qm "add config"
git rm -q config.ini
git commit -qm "remove config"
head -c 2097152 /dev/urandom >blob.dat
git add blob.dat
git commit -qm "big blob"
git rm -q blob.dat
git commit -qm "rm blob"
publish main:main

# G7: tags
git tag v0.1 HEAD~4
git tag -a v0.2 -m rel HEAD
publish refs/tags/v0.2:refs/tags/v0.2

# G15: replace ref, note, refs/original leftover, agent tree ref
git replace HEAD~1 HEAD~2
git notes add -m note HEAD
git update-ref refs/original/refs/heads/main HEAD~3
git update-ref refs/codex/snapshot-1 "HEAD^{tree}"

# G20: tracked noise
mkdir -p .vscode
echo '{}' >.vscode/settings.json
echo x >.DS_Store
git add -f .vscode/settings.json .DS_Store
git commit -qm "editor files"

# G3: hidden local change via assume-unchanged
git update-index --assume-unchanged app.txt
echo hidden >>app.txt

# G8: stashes (one dropped -> dangling)
echo dirty >>s.txt
git stash push -q -m "old experiment"
echo d2 >new.txt
head -c 3072000 /dev/zero >big.bin
git stash push -q -u -m "untracked stash with big file"
echo dropme >>s.txt
git stash push -q -m "dropped"
git stash drop -q 'stash@{0}'

# G9: live and prunable worktrees
git worktree add -q ../wt-gone -b wt/branch
rm -rf ../wt-gone
git worktree add -q ../wt-live -b wt/live

# G2: abandoned bisect, merge/patch leftovers
git bisect start -q HEAD HEAD~3 >/dev/null
git bisect reset -q >/dev/null 2>&1 || true
git bisect start HEAD HEAD~3 >/dev/null
echo conflict >app.txt.orig
echo rej >s.txt.rej
mkdir -p .git/rr-cache/0123abcd
echo x >.git/rr-cache/0123abcd/preimage

# G4/G10/G11/G18: ignored junk, env secret, nested repo, symlinks, footprints
mkdir -p node_modules/pkg dist
for i in $(seq 1 300); do echo x >"node_modules/pkg/f${i}.js"; done
echo build >dist/b.js
echo 'API_KEY=sk-live-SECRETVALUE123' >.env
echo log >debug.log
git init -q vendor/other
ln -s ../does-not-exist broken-link
ln -s /etc/hosts outside-link
touch .git/git-daemon-export-ok
mkdir -p .git/lost-found/other
echo orphan >.git/lost-found/other/0000000000000000000000000000000000000001

# G6/G11/G12: config
git config core.hooksPath .hooks-alt
git config alias.nuke '!git clean -fdx'
git config url.https://mirror.example.com/.insteadOf https://github.com/
git remote add backup https://user:pat_TOKEN123@example.com/r.git

echo scaffold-ok
