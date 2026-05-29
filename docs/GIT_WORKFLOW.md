# Git Workflow

This project did not start with a Git repo, so Stage 4.2 is the recommended first clean checkpoint.

## Recommended First Commit Strategy

You have two reasonable options.

### Option A: One clean initial commit

Use this if you want a simple clean history.

```powershell
git init
git add .
git commit -m "Initial Meroq dashboard through Stage 4.2"
```

### Option B: Commit in waves

Use this if you want a more meaningful history even though the repo is being created now.

```powershell
git init

git add README.md CHANGELOG.md docs .gitignore .streamlit requirements.txt
git commit -m "Add project documentation and setup files"

git add src scripts
git commit -m "Add Meroq data, modeling, backtesting, and risk modules"

git add app.py
git commit -m "Add Streamlit app with Stage 4.2 UX and risk simulation"
```

Option B is recommended because it creates a readable history.

## Connect to GitHub

Create an empty GitHub repo named:

```text
meroq
```

Do not initialize it with a README because the project already has one.

Then run:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/meroq.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Daily Workflow After This

Check changes:

```powershell
git status
```

Stage files:

```powershell
git add .
```

Commit:

```powershell
git commit -m "Describe what changed"
```

Push:

```powershell
git push
```

## Suggested Branches Later

For Stage 5 sentiment:

```powershell
git checkout -b feature/stage-5-sentiment
```

After the feature is stable:

```powershell
git checkout main
git merge feature/stage-5-sentiment
git push
```

## What Should Not Be Committed

These are generated/local files and should stay out of Git:

- `.venv/`
- `data/*.sqlite`
- `data/*.db`
- `__pycache__/`
- `*.pyc`
- `.env`
- `.streamlit/secrets.toml`
- trained model artifacts unless intentionally versioned
