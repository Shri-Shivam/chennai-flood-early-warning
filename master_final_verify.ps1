$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " SIH26071 MASTER FINAL VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$failed = $false

Write-Host "`n[1] BRANCH" -ForegroundColor Cyan
$branch = git branch --show-current
Write-Host "Branch: $branch"

if ($branch -ne "stage7-reconstruction") {
    Write-Host "FAIL: Wrong branch" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS" -ForegroundColor Green
}

Write-Host "`n[2] REMOTE SYNC" -ForegroundColor Cyan
git fetch origin

$ahead = [int](git rev-list --count "origin/stage7-reconstruction..HEAD")
$behind = [int](git rev-list --count "HEAD..origin/stage7-reconstruction")

Write-Host "Ahead:  $ahead"
Write-Host "Behind: $behind"

if (($ahead -ne 0) -or ($behind -ne 0)) {
    Write-Host "FAIL: Branch is not synchronized" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS" -ForegroundColor Green
}

Write-Host "`n[3] TRACKED CHANGES" -ForegroundColor Cyan
$changes = git diff --name-only

if ($changes) {
    Write-Host "FAIL: Tracked changes exist:" -ForegroundColor Red
    $changes
    $failed = $true
} else {
    Write-Host "PASS: No tracked changes" -ForegroundColor Green
}

Write-Host "`n[4] STAGED CHANGES" -ForegroundColor Cyan
$staged = git diff --cached --name-only

if ($staged) {
    Write-Host "FAIL: Staged changes exist:" -ForegroundColor Red
    $staged
    $failed = $true
} else {
    Write-Host "PASS: Nothing staged" -ForegroundColor Green
}

Write-Host "`n[5] UNTRACKED FILES" -ForegroundColor Cyan
$untracked = git ls-files --others --exclude-standard

if ($untracked) {
    Write-Host "NOTICE: Local untracked files exist." -ForegroundColor Yellow
    $untracked
    Write-Host "These are NOT part of the PR." -ForegroundColor Yellow
} else {
    Write-Host "PASS: No untracked files" -ForegroundColor Green
}

Write-Host "`n[6] LARGE FILES" -ForegroundColor Cyan

git check-ignore -v "data\processed\stage7_ai1_ai2_predictions.csv"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Stage 7 predictions are not ignored" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: Stage 7 predictions ignored" -ForegroundColor Green
}

git check-ignore -v "data\processed\stage8_end_to_end_predictions.csv"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Stage 8 predictions are not ignored" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: Stage 8 predictions ignored" -ForegroundColor Green
}

Write-Host "`n[7] CREDENTIAL CHECK" -ForegroundColor Cyan
$credentials = git ls-files | Select-String "\.env$|\.dodsrc$|credentials|secret|token"

if ($credentials) {
    Write-Host "FAIL: Possible credentials tracked" -ForegroundColor Red
    $credentials
    $failed = $true
} else {
    Write-Host "PASS: No credentials tracked" -ForegroundColor Green
}

Write-Host "`n[8] PYTEST" -ForegroundColor Cyan
python -m pytest tests -q

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Tests failed" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: Tests passed" -ForegroundColor Green
}

Write-Host "`n[9] COMPILE" -ForegroundColor Cyan
python -m compileall src tests

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Compilation failed" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: Compilation successful" -ForegroundColor Green
}

Write-Host "`n[10] DIFF CHECK" -ForegroundColor Cyan
git diff --check

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Diff check failed" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: Diff check clean" -ForegroundColor Green
}

Write-Host "`n[11] HEAD" -ForegroundColor Cyan
git log -1 --oneline

$localHead = git rev-parse HEAD
$remoteHead = git rev-parse origin/stage7-reconstruction

Write-Host "Local:  $localHead"
Write-Host "Remote: $remoteHead"

if ($localHead -ne $remoteHead) {
    Write-Host "FAIL: HEAD mismatch" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "PASS: HEAD matches remote" -ForegroundColor Green
}

Write-Host "`n[12] FINAL STATUS" -ForegroundColor Cyan
git status -sb

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

if ($failed) {
    Write-Host "FINAL VERIFICATION FAILED" -ForegroundColor Red
    Write-Host "DO NOT MERGE PR #1" -ForegroundColor Red
    exit 1
} else {
    Write-Host "FINAL VERIFICATION PASSED" -ForegroundColor Green
    Write-Host "PR #1 IS READY FOR FINAL REVIEW" -ForegroundColor Green
}

Write-Host "============================================" -ForegroundColor Cyan