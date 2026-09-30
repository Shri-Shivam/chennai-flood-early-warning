$ErrorActionPreference = "Stop"

$Repo = "Shri-Shivam/chennai-flood-early-warning"
$Branch = "stage7-reconstruction"
$PR = 1

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " SIH26071 - FINAL PR VERIFICATION" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Repository
Write-Host ""
Write-Host "[1] Checking repository..." -ForegroundColor Cyan

$Root = git rev-parse --show-toplevel 2>$null

if (-not $Root) {
    Write-Host "[FAIL] Not inside a Git repository." -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Git repository detected." -ForegroundColor Green

# 2. Branch
$CurrentBranch = git branch --show-current

Write-Host ""
Write-Host "[2] Current branch: $CurrentBranch"

if ($CurrentBranch -ne $Branch) {
    Write-Host "[FAIL] Expected branch: $Branch" -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Correct branch." -ForegroundColor Green

# 3. Remote
Write-Host ""
Write-Host "[3] Checking GitHub remote..." -ForegroundColor Cyan

$Remote = git remote get-url origin

Write-Host "Remote: $Remote"

if ($Remote -notmatch "Shri-Shivam/chennai-flood-early-warning") {
    Write-Host "[FAIL] Wrong GitHub repository." -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Correct GitHub repository." -ForegroundColor Green

# 4. Fetch
Write-Host ""
Write-Host "[4] Fetching GitHub..." -ForegroundColor Cyan

git fetch origin --prune

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] git fetch failed." -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] GitHub state fetched." -ForegroundColor Green

# 5. Local vs remote
Write-Host ""
Write-Host "[5] Checking branch synchronization..." -ForegroundColor Cyan

$LocalSHA = (git rev-parse HEAD).Trim()
$RemoteSHA = (git rev-parse "origin/$Branch").Trim()

Write-Host "Local :  $($LocalSHA.Substring(0,7))"
Write-Host "Remote:  $($RemoteSHA.Substring(0,7))"

if ($LocalSHA -ne $RemoteSHA) {
    Write-Host "[FAIL] Local and remote are different." -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Local and GitHub are synchronized." -ForegroundColor Green

# 6. Unpushed commits
Write-Host ""
Write-Host "[6] Checking for unpushed commits..." -ForegroundColor Cyan

$Unpushed = @(git log --oneline "origin/$Branch..HEAD")

if ($Unpushed.Count -gt 0) {
    Write-Host "[FAIL] Unpushed commits exist:" -ForegroundColor Red
    $Unpushed | ForEach-Object {
        Write-Host "  $_"
    }
    exit 1
}

Write-Host "[PASS] No unpushed commits." -ForegroundColor Green

# 7. Worktree
Write-Host ""
Write-Host "[7] Checking worktree..." -ForegroundColor Cyan

$Status = @(git status --porcelain)

$Tracked = @(
    $Status | Where-Object {
        $_ -notmatch "^\?\?"
    }
)

if ($Tracked.Count -gt 0) {
    Write-Host "[FAIL] Tracked/staged changes detected:" -ForegroundColor Red
    $Tracked | ForEach-Object {
        Write-Host "  $_"
    }
    exit 1
}

Write-Host "[PASS] No tracked or staged changes." -ForegroundColor Green

$Untracked = @(
    $Status | Where-Object {
        $_ -match "^\?\?"
    }
)

if ($Untracked.Count -gt 0) {
    Write-Host "[INFO] Untracked files exist. They will NOT be touched." -ForegroundColor Yellow

    $Untracked | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkYellow
    }
}

# 8. GitHub CLI
Write-Host ""
Write-Host "[8] Checking GitHub CLI..." -ForegroundColor Cyan

$GH = Get-Command gh -ErrorAction SilentlyContinue

if (-not $GH) {
    Write-Host "[FAIL] GitHub CLI (gh) is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install GitHub CLI, then run: gh auth login"
    exit 1
}

Write-Host "[PASS] GitHub CLI detected." -ForegroundColor Green

# 9. GitHub authentication
Write-Host ""
Write-Host "[9] Checking GitHub authentication..." -ForegroundColor Cyan

gh auth status

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] GitHub CLI is not authenticated." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run:"
    Write-Host "gh auth login"
    exit 1
}

Write-Host "[PASS] GitHub authentication OK." -ForegroundColor Green

# 10. PR information
Write-Host ""
Write-Host "[10] Checking PR #$PR..." -ForegroundColor Cyan

$PRRaw = gh pr view $PR `
    --repo $Repo `
    --json number,state,isDraft,mergeable,headRefName,baseRefName,headRefOid,url,title

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Could not read PR #$PR." -ForegroundColor Red
    exit 1
}

$PRInfo = $PRRaw | ConvertFrom-Json

Write-Host ""
Write-Host "PR number : #$($PRInfo.number)"
Write-Host "Title     : $($PRInfo.title)"
Write-Host "State     : $($PRInfo.state)"
Write-Host "Draft     : $($PRInfo.isDraft)"
Write-Host "Base      : $($PRInfo.baseRefName)"
Write-Host "Head      : $($PRInfo.headRefName)"
Write-Host "PR SHA    : $($PRInfo.headRefOid.Substring(0,7))"
Write-Host "Mergeable : $($PRInfo.mergeable)"
Write-Host "URL       : $($PRInfo.url)"

# 11. Safety checks
Write-Host ""
Write-Host "[11] Validating PR..." -ForegroundColor Cyan

if ($PRInfo.state -ne "OPEN") {
    Write-Host "[FAIL] PR is not open." -ForegroundColor Red
    exit 1
}

if ($PRInfo.headRefName -ne $Branch) {
    Write-Host "[FAIL] PR head is not $Branch." -ForegroundColor Red
    exit 1
}

if ($PRInfo.baseRefName -ne "main") {
    Write-Host "[FAIL] PR base is not main." -ForegroundColor Red
    exit 1
}

if ($PRInfo.headRefOid -ne $LocalSHA) {
    Write-Host "[FAIL] PR does not point to current commit." -ForegroundColor Red
    Write-Host "Local: $LocalSHA"
    Write-Host "PR   : $($PRInfo.headRefOid)"
    exit 1
}

Write-Host "[PASS] PR points to current commit." -ForegroundColor Green

# 12. Final summary
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host " ALL VERIFICATION CHECKS PASSED" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

Write-Host ""
Write-Host "Commit : $($LocalSHA.Substring(0,7))"
Write-Host "Branch : $Branch"
Write-Host "PR     : #$PR"
Write-Host "Status : $($PRInfo.state)"
Write-Host ""
Write-Host "PR URL:"
Write-Host $PRInfo.url -ForegroundColor Cyan

Write-Host ""
Write-Host "IMPORTANT: PR was NOT merged." -ForegroundColor Yellow
Write-Host "IMPORTANT: No files were staged, committed, deleted, or cleaned." -ForegroundColor Yellow