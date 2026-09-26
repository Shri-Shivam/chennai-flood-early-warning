# AUDIT_REPORT.md — SIH26071 Repository Audit

Date: 2026-09-14
Scope: `stage7-reconstruction` branch at commit `593ede0` (compared against `main` at `82a7123`).
Auditor note: this audit was performed from a sandboxed clone with no GitHub API
or push-credential access. GitHub-side PR metadata (review state, CI status)
could not be independently verified and is marked as such below.

## 1. Repository state

- Current branch: `stage7-reconstruction`
- HEAD: `593ede0` ("Ignore local Earthdata credentials")
- Parent chain: `593ede0` → `9f32a41` (genuine Stage 8 reconstruction) → `1d69108` (Stage 6 validation) → ... → `72702b9` (Stage 7 reconstruction) → `03bf8e2`/`ebd447e` (Stage 8 quarantine, 2026-09-12) → `82a7123` (main, the original unverified "restore" commit)
- Remote tracking: local sandbox clone is in sync with `origin/stage7-reconstruction` as of this audit (previous sandbox-local commit from the prior session turn was superseded by the real pushed commit and discarded via `git reset --hard`, which rewrote nothing published)
- PR #1 state: **NOT INDEPENDENTLY VERIFIED** — no GitHub API/web access available in this environment to confirm review status, CI checks, or mergeability

## 2. What is VERIFIED (this session, real commands, real data)

- 36/36 tests pass across `tests/test_temporal_leakage.py` (10), `tests/test_stage7_integration.py` (9), `tests/test_stage7_temporal_alignment.py` (3, one fixed this session), `tests/test_end_to_end_temporal_integrity.py` (14).
- `python -m compileall src tests`: clean, no errors.
- `git diff --check`: clean.
- No secrets, credentials, `.env`, or `.dodsrc` content anywhere in the tracked tree (`593ede0` proactively gitignores `.dodsrc`).
- No file over ~800KB in the tracked tree; the two known large prediction dumps (Stage 7's ~127MB, Stage 8's ~94MB) are correctly gitignored and absent from the repository.
- No hardcoded historical/fabricated reference numbers found anywhere in live `.py` source (scanned specifically for the known-fabricated Stage 7 numbers from commit `82a7123`).
- Spatial centroid/distance calculations in `src/features/build_spatial_features.py` and `src/dem/calculate_drainage_distance.py` **correctly reproject to `EPSG:32644` before computing centroids/distances**, then convert to `EPSG:4326` only for storage. This was a specific concern raised for this audit; verified NOT a bug.
- Stage 6/7/8 leakage controls (temporal cutoffs, threshold isolation, class-2 exclusion, exact-timestamp AI#1 merging, frozen-model reuse in Stage 8) all independently tested and passing, per the 36 tests above.
- Stage 8's quarantine gap (7 files duplicated outside `archive/` — found and fixed in the prior session) remains fixed; re-checked this session, confirmed no live-path duplication has recurred.

## 3. What is UNCERTAIN (cannot be resolved from this environment)

- Whether GitHub's PR #1 UI actually reflects this branch's current HEAD, whether any CI is configured/passing, and whether any review comments exist.
- Whether the exact package/library versions used to produce the currently-committed Stage 6/7/8 metrics match the project's documented spec (Python 3.14.2 / pandas 3.0.5 / sklearn 1.9.0) — this session's sandbox uses slightly different versions, and metric discrepancies consistent with that have been observed and reported (not resolved) throughout this project's history.
- Whether "PR #1" scope matches exactly what `RECOVERY.md` and `PROJECT_PROGRESS.md` claim, since PR content couldn't be fetched.

## 4. What was BROKEN (found and fixed this session)

- `tests/test_stage7_temporal_alignment.py::test_stage7_source_has_no_future_rain_feature` used a naive whole-file substring search for `"future_6h_rain"`, which false-positived on legitimate docstring/comment text and the `forbidden` leakage-guard set itself (lines that *mention* the column specifically in order to exclude it). Fixed to check the actual `LEARNED_EXPERIMENTS` feature-set definitions instead, consistent with the stronger equivalent check already in `tests/test_stage7_integration.py`. This was a test-quality defect, not a real leakage bug — confirmed by direct inspection of every occurrence of the string in the source file.

## 5. What is DUPLICATED

- `tests/test_stage7_temporal_alignment.py` (3 tests, minimal) and `tests/test_stage7_integration.py` (9 tests, comprehensive) overlap in purpose but are not identical — the former predates the latter and does lighter-weight file-existence + the now-fixed feature check. Recommend keeping both (redundancy in tests is not harmful) but noting the overlap; consolidating is a low-priority cleanup, not a defect.

## 6. What should REMAIN

- All current Stage 6/7/8 source, tests, and committed outputs — genuinely executed, independently verified this session and in prior sessions.
- The `archive/unverified_recovery_2026-09-09/` and `archive/unverified_recovery_2026-09-12/` quarantine directories — full forensic record, must not be deleted.

## 7. What should be QUARANTINED

- Nothing new found this session. The known quarantine gap from the prior session (7 duplicated Stage 8 files outside `archive/`) was already fixed and remains fixed.

## 8. What should be FIXED (beyond what was fixed this session)

- None found as blocking. See Section 9 for priority-ranked next steps (non-blocking).

## 9. Priority ranking for next work

1. **Independent execution on the actual target environment** (Python 3.14.2/pandas 3.0.5/sklearn 1.9.0) to resolve the persistent, never-fully-confirmed metric-discrepancy hypothesis (environment version differences). This is higher priority than any new feature — it's a reproducibility gap in already-claimed-verified work.
2. **More independent flood events**, if reproducibly obtainable from authoritative sources (NRSC/NDEM/IMD), since the 2-episode limitation is the single biggest scientific constraint on every downstream claim in this project. Not attempted this session — requires new external data acquisition, which is out of scope for an audit-and-fix pass and was not requested.
3. Everything else (Stage 5/ERA5-Land masking, exposure module, warning-level calibration, dashboard) is explicitly gated behind the above two items being resolved or explicitly accepted as permanent limitations, per this project's own stated priority order (scientific correctness > temporal/spatial integrity > reproducibility > validation > ... > presentation polish).
