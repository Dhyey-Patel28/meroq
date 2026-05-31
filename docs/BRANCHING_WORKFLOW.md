# Branching and PR workflow

Meroq now treats `main` as the stable branch. New work should happen on a feature branch, then be merged through a pull request.

## Recommended flow

```powershell
cd $HOME\Desktop\meroq
git checkout main
git pull
git checkout -b feature/progressive-watchlist
```

Apply the update, then test:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_tests.py

cd frontend
npm install
npm audit
npm run typecheck
```

Commit and push the branch:

```powershell
cd $HOME\Desktop\meroq
git status
git add -A
git commit -m "feat: add progressive watchlist scanning"
git push -u origin feature/progressive-watchlist
```

Create and merge a PR with GitHub CLI:

```powershell
gh pr create --fill --base main --head feature/progressive-watchlist
gh pr merge --squash --delete-branch
```

Use squash merge going forward if you want GitHub's main commit history to show one clean commit per upgrade instead of every local fix-up commit.

## Safety checks

Before committing, confirm `git status` does not list:

```text
.env
.venv/
frontend/node_modules/
frontend/.next/
data/*.sqlite
data/*.db
```

If those appear, stop and verify `.gitignore` before committing.
