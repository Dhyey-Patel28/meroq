param(
  [Parameter(Mandatory=$true)][string]$Branch,
  [Parameter(Mandatory=$true)][string]$CommitMessage,
  [string]$PrTitle = "",
  [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

function Run($cmd) {
  Write-Host ">> $cmd"
  Invoke-Expression $cmd
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw "GitHub CLI 'gh' is required. Install it and run 'gh auth login'."
}

$current = (git branch --show-current).Trim()
if ($current -eq "main") {
  Run "git checkout -b $Branch"
} elseif ($current -ne $Branch) {
  throw "Current branch is '$current'. Switch to '$Branch' or main before running this script."
}

Run "python scripts/run_tests.py"

if (-not $SkipFrontend -and (Test-Path "frontend/package.json")) {
  Push-Location frontend
  try {
    Run "npm install"
    Run "npm audit"
    Run "npm run typecheck"
  } finally {
    Pop-Location
  }
}

Run "git add -A"
$staged = git diff --cached --name-only
if ($staged -match "^\.env$|^\.venv/|^frontend/node_modules/|^frontend/\.next/|^data/.*\.(sqlite|db)") {
  throw "Refusing to commit local secrets, environments, build outputs, or database files."
}

Run "git commit -m `"$CommitMessage`""
Run "git push -u origin $Branch"

if ([string]::IsNullOrWhiteSpace($PrTitle)) {
  $PrTitle = $CommitMessage
}

Run "gh pr create --fill --title `"$PrTitle`" --base main --head $Branch"
Run "gh pr merge --squash --delete-branch"
Run "git checkout main"
Run "git pull"
