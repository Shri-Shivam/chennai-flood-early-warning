"""
SIH26071 - STAGE 2
Read-only audit of the inundation-risk ML dataset.

This script:
- does NOT train AI #2
- does NOT modify inundation_risk_ml_dataset.csv
- does NOT modify AI #1
- does NOT delete files
- does NOT silently repair methodological problems
"""

from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = REPO_ROOT / "data/processed/inundation_risk_ml_dataset.csv"
RAINFALL_PATH = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
AUDIT_CSV_PATH = REPO_ROOT / "data/processed/inundation_risk_dataset_audit.csv"
AUDIT_TXT_PATH = REPO_ROOT / "data/processed/inundation_risk_dataset_audit.txt"

EXPECTED_ROWS = 353130
EXPECTED_CELLS = 70626
EXPECTED_TIMESTAMPS = 5
EXPECTED_EPISODES = 2
EXPECTED_COLUMNS = 30

EXPECTED_EPISODE_MAP = {
    pd.Timestamp("2021-11-08 23:00:00"): "Episode_1",
    pd.Timestamp("2021-11-10 11:00:00"): "Episode_1",
    pd.Timestamp("2021-11-10 18:00:00"): "Episode_1",
    pd.Timestamp("2021-11-12 00:00:00"): "Episode_1",
    pd.Timestamp("2021-11-28 06:00:00"): "Episode_2",
}

EXPECTED_LABEL_COUNTS = {
    pd.Timestamp("2021-11-08 23:00:00"): {0: 69715, 1: 49, 2: 862},
    pd.Timestamp("2021-11-10 11:00:00"): {0: 69670, 1: 335, 2: 621},
    pd.Timestamp("2021-11-10 18:00:00"): {0: 69708, 1: 477, 2: 441},
    pd.Timestamp("2021-11-12 00:00:00"): {0: 69727, 1: 103, 2: 796},
    pd.Timestamp("2021-11-28 06:00:00"): {0: 69724, 1: 40, 2: 862},
}

EXPECTED_OVERALL_LABELS = {0: 348544, 1: 1004, 2: 3582}

BASELINE_FEATURES = [
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",
    "elevation",
    "slope_degrees",
    "distance_to_drainage",
]

FORBIDDEN_MODEL_INPUTS = [
    "target",
    "future_6h_rain",
    "cell_id",
    "timestamp",
    "episode_id",
    "centroid_lon",
    "centroid_lat",
    "label",
    "label_meaning",
]

LEAKAGE_NAME_PATTERNS = [
    "future",
    "target",
    "pred",
    "xgboost",
    "ai1",
    "ai_1",
    "rainfall_pred",
    "probability",
    "inundation_pred",
]


class Audit:
    def __init__(self):
        self.lines = []
        self.findings = []
        self.fail_issues = []

    def add(self, text=""):
        self.lines.append(text)
        print(text)

    def heading(self, title):
        self.add("")
        self.add("=" * 72)
        self.add(title)
        self.add("=" * 72)

    def record(self, section, check, expected, actual, status, notes=""):
        self.findings.append(
            {
                "section": section,
                "check": check,
                "expected": expected,
                "actual": actual,
                "status": status,
                "notes": notes,
            }
        )
        marker = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else status
        self.add(f"[{marker}] {check}")
        self.add(f"      expected: {expected}")
        self.add(f"      actual:   {actual}")
        if notes:
            self.add(f"      notes:    {notes}")
        if status == "FAIL":
            self.fail_issues.append(f"{section}: {check} | expected={expected} | actual={actual} | {notes}".strip())

    def info(self, section, check, value, notes=""):
        self.findings.append(
            {
                "section": section,
                "check": check,
                "expected": "",
                "actual": value,
                "status": "INFO",
                "notes": notes,
            }
        )
        self.add(f"[INFO] {check}: {value}")
        if notes:
            self.add(f"      notes:    {notes}")


def fmt_ts(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def describe_numeric(series):
    s = pd.to_numeric(series, errors="coerce")
    return {
        "count": int(s.notna().sum()),
        "min": float(s.min()) if s.notna().any() else np.nan,
        "p25": float(s.quantile(0.25)) if s.notna().any() else np.nan,
        "median": float(s.median()) if s.notna().any() else np.nan,
        "p75": float(s.quantile(0.75)) if s.notna().any() else np.nan,
        "max": float(s.max()) if s.notna().any() else np.nan,
        "mean": float(s.mean()) if s.notna().any() else np.nan,
        "std": float(s.std()) if s.notna().any() else np.nan,
    }


def main():
    audit = Audit()
    audit.heading("SIH26071 STAGE 2 - INUNDATION RISK DATASET AUDIT")
    audit.add("Read-only audit. No training. No file deletions. No silent repairs.")

    # ------------------------------------------------------------------
    # A. BASIC STRUCTURE
    # ------------------------------------------------------------------
    audit.heading("A. BASIC STRUCTURE")

    if not DATASET_PATH.exists():
        audit.record(
            "A",
            "dataset file exists",
            str(DATASET_PATH),
            "MISSING",
            "FAIL",
        )
        write_outputs(audit)
        return

    audit.record("A", "dataset file exists", str(DATASET_PATH), "FOUND", "PASS")

    df = pd.read_csv(DATASET_PATH)

    if "timestamp" in df.columns:
        raw_ts = df["timestamp"].astype(str)
        unique_raw = sorted(raw_ts.unique().tolist())
        raw_counts = raw_ts.value_counts()
        raw_count_text = " | ".join(f"{k} (n={int(raw_counts[k])})" for k in unique_raw)
        audit.info("A", "raw unique timestamp strings in CSV", raw_count_text)
        missing_clock = [s for s in unique_raw if len(s) <= 10]
        audit.record(
            "A",
            "timestamp strings include full date and time",
            "all timestamps stored as YYYY-MM-DD HH:MM:SS",
            "all full datetimes" if not missing_clock else "date-only strings present: " + ", ".join(missing_clock),
            "FAIL" if missing_clock else "PASS",
            "CSV was not modified. Date-only values are parsed as 00:00:00 for audit comparisons.",
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")

    audit.record(
        "A",
        "shape (rows, cols)",
        f"({EXPECTED_ROWS}, {EXPECTED_COLUMNS})",
        str(tuple(df.shape)),
        "PASS" if df.shape == (EXPECTED_ROWS, EXPECTED_COLUMNS) else "FAIL",
    )
    audit.info("A", "columns", ", ".join(map(str, df.columns.tolist())))
    audit.add("dtypes:")
    for col, dtype in df.dtypes.items():
        audit.add(f"  - {col}: {dtype}")
        audit.findings.append(
            {
                "section": "A",
                "check": f"dtype:{col}",
                "expected": "",
                "actual": str(dtype),
                "status": "INFO",
                "notes": "",
            }
        )

    if "timestamp" in df.columns:
        ts_min = df["timestamp"].min()
        ts_max = df["timestamp"].max()
        audit.info("A", "timestamp range", f"{fmt_ts(ts_min)} to {fmt_ts(ts_max)}")
        n_ts = int(df["timestamp"].nunique())
    else:
        audit.record("A", "timestamp column", "present", "MISSING", "FAIL")
        n_ts = 0

    n_cells = int(df["cell_id"].nunique()) if "cell_id" in df.columns else 0
    n_ep = int(df["episode_id"].nunique()) if "episode_id" in df.columns else 0

    audit.record("A", "unique cells", str(EXPECTED_CELLS), str(n_cells), "PASS" if n_cells == EXPECTED_CELLS else "FAIL")
    audit.record("A", "unique timestamps", str(EXPECTED_TIMESTAMPS), str(n_ts), "PASS" if n_ts == EXPECTED_TIMESTAMPS else "FAIL")
    audit.record("A", "unique episodes", str(EXPECTED_EPISODES), str(n_ep), "PASS" if n_ep == EXPECTED_EPISODES else "FAIL")

    # ------------------------------------------------------------------
    # B. DUPLICATES
    # ------------------------------------------------------------------
    audit.heading("B. DUPLICATES")

    n_dup_cell = int(df["cell_id"].duplicated().sum()) if "cell_id" in df.columns else -1
    n_dup_ts = int(df["timestamp"].duplicated().sum()) if "timestamp" in df.columns else -1

    audit.info(
        "B",
        "duplicate cell_id row-count (repeated values)",
        str(n_dup_cell),
        "Expected: each cell repeats across timestamps (not a uniqueness failure by itself).",
    )
    audit.info(
        "B",
        "duplicate timestamp row-count (repeated values)",
        str(n_dup_ts),
        "Expected: each timestamp repeats across cells (not a uniqueness failure by itself).",
    )

    if {"cell_id", "timestamp"}.issubset(df.columns):
        dup_ct = int(df.duplicated(subset=["cell_id", "timestamp"]).sum())
        n_pairs = int(df.groupby(["cell_id", "timestamp"]).ngroups)
        expected_pairs = EXPECTED_CELLS * EXPECTED_TIMESTAMPS
        audit.record(
            "B",
            "duplicate cell_id + timestamp",
            "0 duplicates; 70626 cells x 5 timestamps = 353130 unique pairs",
            f"{dup_ct} duplicate rows; {n_pairs} unique pairs",
            "PASS" if dup_ct == 0 and n_pairs == expected_pairs else "FAIL",
        )
    else:
        audit.record("B", "duplicate cell_id + timestamp", "checkable", "missing cell_id or timestamp", "FAIL")

    if {"cell_id", "timestamp", "episode_id"}.issubset(df.columns):
        dup_cte = int(df.duplicated(subset=["cell_id", "timestamp", "episode_id"]).sum())
        audit.record(
            "B",
            "duplicate cell_id + timestamp + episode_id",
            "0",
            str(dup_cte),
            "PASS" if dup_cte == 0 else "FAIL",
        )

    audit.record(
        "B",
        "expected panel size",
        "70626 cells x 5 timestamps = 353130 rows",
        str(len(df)),
        "PASS" if len(df) == EXPECTED_ROWS else "FAIL",
    )

    # ------------------------------------------------------------------
    # C. EPISODE CONSISTENCY
    # ------------------------------------------------------------------
    audit.heading("C. EPISODE CONSISTENCY")

    if {"timestamp", "episode_id"}.issubset(df.columns):
        actual_map = (
            df[["timestamp", "episode_id"]]
            .drop_duplicates()
            .sort_values("timestamp")
        )
        audit.add("Observed timestamp -> episode_id:")
        for _, row in actual_map.iterrows():
            audit.add(f"  {fmt_ts(row['timestamp'])} -> {row['episode_id']}")

        actual_dict = {
            pd.Timestamp(row["timestamp"]): str(row["episode_id"])
            for _, row in actual_map.iterrows()
        }

        extra_ts = set(actual_dict) - set(EXPECTED_EPISODE_MAP)
        missing_ts = set(EXPECTED_EPISODE_MAP) - set(actual_dict)
        mismatched = {
            ts: (EXPECTED_EPISODE_MAP[ts], actual_dict[ts])
            for ts in (set(EXPECTED_EPISODE_MAP) & set(actual_dict))
            if EXPECTED_EPISODE_MAP[ts] != actual_dict[ts]
        }

        if extra_ts or missing_ts or mismatched:
            notes = []
            if missing_ts:
                notes.append("missing: " + ", ".join(fmt_ts(t) for t in sorted(missing_ts)))
            if extra_ts:
                notes.append("unexpected: " + ", ".join(fmt_ts(t) for t in sorted(extra_ts)))
            if mismatched:
                notes.append(
                    "mismatched: "
                    + "; ".join(
                        f"{fmt_ts(t)} expected {exp} got {got}"
                        for t, (exp, got) in sorted(mismatched.items())
                    )
                )
            audit.record(
                "C",
                "episode assignment vs defined Episode_1 / Episode_2",
                str({fmt_ts(k): v for k, v in EXPECTED_EPISODE_MAP.items()}),
                str({fmt_ts(k): v for k, v in actual_dict.items()}),
                "FAIL",
                " | ".join(notes),
            )
        else:
            audit.record(
                "C",
                "episode assignment vs defined Episode_1 / Episode_2",
                "Episode_1: 2021-11-08 23:00, 2021-11-10 11:00, 2021-11-10 18:00, 2021-11-12 00:00; Episode_2: 2021-11-28 06:00",
                "exact match",
                "PASS",
            )

        ep1_ts = sorted(df.loc[df["episode_id"] == "Episode_1", "timestamp"].unique())
        ep2_ts = sorted(df.loc[df["episode_id"] == "Episode_2", "timestamp"].unique())
        audit.info("C", "Episode_1 timestamps", ", ".join(fmt_ts(t) for t in ep1_ts))
        audit.info("C", "Episode_2 timestamps", ", ".join(fmt_ts(t) for t in ep2_ts))
    else:
        audit.record("C", "episode columns", "timestamp and episode_id", "missing", "FAIL")

    # ------------------------------------------------------------------
    # D. LABEL AUDIT
    # ------------------------------------------------------------------
    audit.heading("D. LABEL AUDIT")

    if "label" not in df.columns or "timestamp" not in df.columns:
        audit.record("D", "label and timestamp columns", "present", "missing", "FAIL")
    else:
        labels_found = sorted(pd.unique(df["label"]))
        audit.info("D", "label values found", str(labels_found))
        if set(pd.to_numeric(df["label"], errors="coerce").dropna().astype(int).unique()) - {0, 1, 2}:
            audit.record("D", "label set", "{0,1,2}", str(set(labels_found)), "FAIL")
        else:
            audit.record("D", "label set", "{0,1,2}", str(set(int(x) for x in labels_found)), "PASS")

        audit.add("Per-timestamp class counts (do not change expected values; flag mismatches):")
        for ts in sorted(df["timestamp"].unique()):
            sub = df.loc[df["timestamp"] == ts]
            counts = sub["label"].value_counts().to_dict()
            c0 = int(counts.get(0, 0))
            c1 = int(counts.get(1, 0))
            c2 = int(counts.get(2, 0))
            total = len(sub)
            pct0 = 100.0 * c0 / total if total else np.nan
            pct1 = 100.0 * c1 / total if total else np.nan
            pct2 = 100.0 * c2 / total if total else np.nan
            audit.add(f"  {fmt_ts(ts)}")
            audit.add(f"    class0={c0} ({pct0:.4f}%)  class1={c1} ({pct1:.4f}%)  class2={c2} ({pct2:.4f}%)  total={total}")

            ts_key = pd.Timestamp(ts)
            if ts_key in EXPECTED_LABEL_COUNTS:
                exp = EXPECTED_LABEL_COUNTS[ts_key]
                ok = c0 == exp[0] and c1 == exp[1] and c2 == exp[2] and total == EXPECTED_CELLS
                audit.record(
                    "D",
                    f"label counts {fmt_ts(ts)}",
                    f"class0={exp[0]} class1={exp[1]} class2={exp[2]} total={EXPECTED_CELLS}",
                    f"class0={c0} class1={c1} class2={c2} total={total}",
                    "PASS" if ok else "FAIL",
                )
            else:
                audit.record(
                    "D",
                    f"label counts {fmt_ts(ts)}",
                    "one of the five defined timestamps",
                    "unexpected timestamp",
                    "FAIL",
                )

        overall = df["label"].value_counts().to_dict()
        o0 = int(overall.get(0, 0))
        o1 = int(overall.get(1, 0))
        o2 = int(overall.get(2, 0))
        audit.add(f"Overall: class0={o0} class1={o1} class2={o2} total={len(df)}")
        ok_overall = (
            o0 == EXPECTED_OVERALL_LABELS[0]
            and o1 == EXPECTED_OVERALL_LABELS[1]
            and o2 == EXPECTED_OVERALL_LABELS[2]
        )
        audit.record(
            "D",
            "overall label counts",
            f"class0={EXPECTED_OVERALL_LABELS[0]} class1={EXPECTED_OVERALL_LABELS[1]} class2={EXPECTED_OVERALL_LABELS[2]}",
            f"class0={o0} class1={o1} class2={o2}",
            "PASS" if ok_overall else "FAIL",
        )
        audit.add("Class 2 is uncertain and must not be treated as class 0.")

    # ------------------------------------------------------------------
    # E. MISSING VALUES
    # ------------------------------------------------------------------
    audit.heading("E. MISSING VALUES")

    problem_cols = []
    for col in df.columns:
        na_count = int(df[col].isna().sum())
        null_count = int(df[col].isnull().sum())
        inf_count = 0
        if pd.api.types.is_numeric_dtype(df[col]):
            inf_count = int(np.isinf(pd.to_numeric(df[col], errors="coerce")).sum())
        status = "PASS" if (na_count == 0 and null_count == 0 and inf_count == 0) else "FAIL"
        if status == "FAIL":
            problem_cols.append(col)
        audit.record(
            "E",
            f"missing/null/inf:{col}",
            "0 NaN, 0 null, 0 inf",
            f"NaN={na_count}, null={null_count}, inf={inf_count}",
            status,
        )

    if problem_cols:
        audit.add("Problematic columns: " + ", ".join(problem_cols))
    else:
        audit.add("No missing, null, or infinite values found in any column.")

    # ------------------------------------------------------------------
    # F. WEATHER TIMESTAMP ALIGNMENT
    # ------------------------------------------------------------------
    audit.heading("F. WEATHER TIMESTAMP ALIGNMENT")
    audit.add("Exact timestamp match only. Nearest-timestamp matching is not used.")

    if not RAINFALL_PATH.exists():
        audit.record("F", "rainfall_ml_dataset.csv exists", str(RAINFALL_PATH), "MISSING", "FAIL")
    elif "timestamp" not in df.columns:
        audit.record("F", "inundation timestamps", "present", "missing timestamp column", "FAIL")
    else:
        rain = pd.read_csv(RAINFALL_PATH, parse_dates=["time"])
        rain_times = set(pd.to_datetime(rain["time"]))
        ds_times = set(pd.to_datetime(df["timestamp"].unique()))

        exact = sorted(ds_times & rain_times)
        missing = sorted(ds_times - rain_times)
        unexpected = sorted(ds_times - set(EXPECTED_EPISODE_MAP.keys()))

        audit.add("Exact matches in rainfall_ml_dataset.csv:")
        for t in exact:
            audit.add(f"  MATCH {fmt_ts(t)}")
        audit.record(
            "F",
            "exact rainfall timestamp matches",
            "all 5 inundation timestamps present exactly",
            f"{len(exact)} exact matches: " + ", ".join(fmt_ts(t) for t in exact),
            "PASS" if len(missing) == 0 and len(exact) == n_ts else "FAIL",
        )
        audit.record(
            "F",
            "missing rainfall timestamp matches",
            "none",
            "none" if not missing else ", ".join(fmt_ts(t) for t in missing),
            "PASS" if not missing else "FAIL",
        )
        audit.record(
            "F",
            "unexpected inundation timestamps",
            "none beyond the five defined events",
            "none" if not unexpected else ", ".join(fmt_ts(t) for t in unexpected),
            "PASS" if not unexpected else "FAIL",
        )

    # ------------------------------------------------------------------
    # G. SPATIAL FEATURE AUDIT
    # ------------------------------------------------------------------
    audit.heading("G. SPATIAL FEATURE AUDIT")
    audit.add("Outliers are reported, not removed.")

    spatial_cols = ["elevation", "slope_degrees", "distance_to_drainage"]
    for col in spatial_cols:
        if col not in df.columns:
            audit.record("G", f"{col} present", "present", "MISSING", "FAIL")
            continue
        na = int(df[col].isna().sum())
        stats = describe_numeric(df[col])
        audit.record(
            "G",
            f"{col} missing values",
            "0",
            str(na),
            "PASS" if na == 0 else "FAIL",
        )
        audit.info(
            "G",
            f"{col} numeric range",
            (
                f"min={stats['min']:.6g} p25={stats['p25']:.6g} median={stats['median']:.6g} "
                f"p75={stats['p75']:.6g} max={stats['max']:.6g} mean={stats['mean']:.6g} std={stats['std']:.6g}"
            ),
        )

    geom_cols = [c for c in df.columns if str(c).lower() in {"geometry", "geom", "wkt", "wkb"}]
    if geom_cols:
        audit.info("G", "geometry retained in dataset", ", ".join(geom_cols))
        try:
            import geopandas as gpd
            from shapely import wkt as shapely_wkt

            gcol = geom_cols[0]
            sample = df[gcol]
            invalid = 0
            unparseable = 0
            for val in sample:
                if pd.isna(val):
                    invalid += 1
                    continue
                try:
                    geom = shapely_wkt.loads(val) if isinstance(val, str) else val
                    if geom is None or geom.is_empty or not geom.is_valid:
                        invalid += 1
                except Exception:
                    unparseable += 1
            audit.record(
                "G",
                "geometry validity",
                "all valid",
                f"invalid={invalid}, unparseable={unparseable}",
                "PASS" if invalid == 0 and unparseable == 0 else "FAIL",
            )
            del gpd
        except Exception as exc:
            audit.info("G", "geometry validity check", f"could not complete: {exc}")
    else:
        audit.info(
            "G",
            "geometry retained in dataset",
            "NO geometry column in CSV",
            "Spatial geometry is not retained in inundation_risk_ml_dataset.csv; centroids are present.",
        )

    # ------------------------------------------------------------------
    # H. MODEL FEATURE AUDIT
    # ------------------------------------------------------------------
    audit.heading("H. MODEL FEATURE AUDIT")

    missing_feats = [c for c in BASELINE_FEATURES if c not in df.columns]
    extra_note = ""
    if missing_feats:
        extra_note = "missing: " + ", ".join(missing_feats)
    audit.record(
        "H",
        "baseline AI #2 features exist exactly",
        ", ".join(BASELINE_FEATURES),
        "all present" if not missing_feats else extra_note,
        "PASS" if not missing_feats else "FAIL",
    )

    audit.add("Columns that MUST NOT be used as AI #2 model inputs:")
    for col in FORBIDDEN_MODEL_INPUTS:
        present = col in df.columns
        audit.add(f"  - {col}: {'PRESENT (do not use as input)' if present else 'not in this dataset (still forbidden if added later)'}")
        audit.findings.append(
            {
                "section": "H",
                "check": f"forbidden_input:{col}",
                "expected": "must not be used as model input",
                "actual": "present" if present else "absent",
                "status": "INFO",
                "notes": "identifier, target-related, centroid, or future-derived",
            }
        )

    future_like = [c for c in df.columns if "future" in str(c).lower()]
    audit.info("H", "future-derived columns present", "none" if not future_like else ", ".join(future_like))

    # ------------------------------------------------------------------
    # I. CLASS 2 AUDIT
    # ------------------------------------------------------------------
    audit.heading("I. CLASS 2 AUDIT")
    audit.add("Descriptive only. Class 2 is not treated as class 0. No model is trained.")

    if "label" in df.columns:
        for ts in sorted(df["timestamp"].unique()) if "timestamp" in df.columns else []:
            sub = df.loc[df["timestamp"] == ts]
            n2 = int((sub["label"] == 2).sum())
            pct = 100.0 * n2 / len(sub) if len(sub) else np.nan
            audit.info("I", f"class 2 {fmt_ts(ts)}", f"count={n2} percent={pct:.4f}%")

        n2_all = int((df["label"] == 2).sum())
        audit.info("I", "class 2 overall", f"count={n2_all} percent={100.0 * n2_all / len(df):.4f}%")

        present_feats = [c for c in BASELINE_FEATURES if c in df.columns]
        if present_feats:
            audit.add("Baseline feature distributions by label (descriptive):")
            for feat in present_feats:
                audit.add(f"  Feature: {feat}")
                for cls in [0, 1, 2]:
                    stats = describe_numeric(df.loc[df["label"] == cls, feat])
                    audit.add(
                        f"    class {cls}: n={stats['count']} min={stats['min']:.6g} "
                        f"median={stats['median']:.6g} mean={stats['mean']:.6g} max={stats['max']:.6g}"
                    )
                    audit.findings.append(
                        {
                            "section": "I",
                            "check": f"class{cls}_{feat}_distribution",
                            "expected": "descriptive only",
                            "actual": (
                                f"n={stats['count']} min={stats['min']} median={stats['median']} "
                                f"mean={stats['mean']} max={stats['max']}"
                            ),
                            "status": "INFO",
                            "notes": "class 2 compared descriptively with class 0 and class 1; no model trained",
                        }
                    )

            audit.add("Class 2 vs class 0 / class 1 (median comparison of baseline features):")
            for feat in present_feats:
                med = {
                    cls: float(pd.to_numeric(df.loc[df["label"] == cls, feat], errors="coerce").median())
                    for cls in [0, 1, 2]
                }
                audit.add(
                    f"  {feat}: class0_median={med[0]:.6g} class1_median={med[1]:.6g} class2_median={med[2]:.6g}"
                )
    else:
        audit.record("I", "label column for class 2 audit", "present", "MISSING", "FAIL")

    # ------------------------------------------------------------------
    # J. SPATIAL / EPISODE STRUCTURE
    # ------------------------------------------------------------------
    audit.heading("J. SPATIAL/EPISODE STRUCTURE")

    if {"cell_id", "timestamp"}.issubset(df.columns):
        cells_per_ts = df.groupby("timestamp")["cell_id"].nunique()
        audit.add("Unique cells per timestamp:")
        for ts, n in cells_per_ts.items():
            audit.add(f"  {fmt_ts(ts)}: {n}")
            audit.record(
                "J",
                f"unique cells at {fmt_ts(ts)}",
                str(EXPECTED_CELLS),
                str(int(n)),
                "PASS" if int(n) == EXPECTED_CELLS else "FAIL",
            )

        cell_sets = [set(g["cell_id"]) for _, g in df.groupby("timestamp")]
        same_across = all(s == cell_sets[0] for s in cell_sets) if cell_sets else False
        audit.record(
            "J",
            "same spatial cells appear across timestamps",
            "identical cell_id set at every timestamp",
            "yes" if same_across else "no",
            "PASS" if same_across else "FAIL",
        )

        if "episode_id" in df.columns:
            audit.add("Unique cells per episode:")
            for ep, g in df.groupby("episode_id"):
                n = int(g["cell_id"].nunique())
                n_ts = int(g["timestamp"].nunique())
                audit.info("J", f"cells in {ep}", f"{n} unique cells across {n_ts} timestamp(s)")
                audit.record(
                    "J",
                    f"cell panel completeness in {ep}",
                    str(EXPECTED_CELLS),
                    str(n),
                    "PASS" if n == EXPECTED_CELLS else "FAIL",
                )

        if "label" in df.columns:
            audit.add("Class 1 spatial counts per timestamp:")
            for ts, g in df.groupby("timestamp"):
                n1 = int((g["label"] == 1).sum())
                n1_cells = int(g.loc[g["label"] == 1, "cell_id"].nunique())
                audit.info("J", f"class 1 at {fmt_ts(ts)}", f"rows={n1} unique_cells={n1_cells}")

        audit.add("Spatial cells are highly correlated with neighbors; do not use random cell-level splits.")
        audit.add("Final validation must be episode-aware and spatially blocked.")
        audit.add("Only two independently verified episodes exist; generalization remains exploratory.")

    # ------------------------------------------------------------------
    # K. DATA LEAKAGE AUDIT
    # ------------------------------------------------------------------
    audit.heading("K. DATA LEAKAGE AUDIT")
    audit.add("Report only. Nothing is deleted.")

    cols_lower = {c: str(c).lower() for c in df.columns}

    future_cols = [c for c, low in cols_lower.items() if "future" in low]
    target_cols = [c for c, low in cols_lower.items() if low == "target" or low.startswith("target_")]
    ai1_cols = [
        c
        for c, low in cols_lower.items()
        if any(p in low for p in ["pred", "xgboost", "ai1", "ai_1", "probability", "score"])
    ]
    post_event = [c for c, low in cols_lower.items() if any(p in low for p in ["post_event", "after_event", "inundation_depth", "flood_depth", "arrival_time"])]
    calendar_cols = [c for c in ["hour", "month", "day_of_year"] if c in df.columns]

    audit.record(
        "K",
        "future rainfall columns in inundation dataset",
        "absent (do not use future rainfall)",
        "none" if not future_cols else ", ".join(future_cols),
        "PASS" if not future_cols else "FAIL",
        "future_* columns would be leakage if used as AI #2 inputs",
    )
    audit.record(
        "K",
        "AI #1 rainfall target column leaked into inundation dataset",
        "absent",
        "none" if not target_cols else ", ".join(target_cols),
        "PASS" if not target_cols else "FAIL",
        "rainfall_ml_dataset.csv contains target/future_6h_rain; those must not be joined in yet",
    )
    audit.record(
        "K",
        "accidental AI #1 prediction columns",
        "absent",
        "none" if not ai1_cols else ", ".join(ai1_cols),
        "PASS" if not ai1_cols else "FAIL",
        "Do not add AI #1 predictions as a feature yet",
    )
    audit.record(
        "K",
        "post-event / depth / arrival variables",
        "absent",
        "none" if not post_event else ", ".join(post_event),
        "PASS" if not post_event else "FAIL",
    )

    # Inundation label is the AI #2 outcome, not an input.
    if "label" in df.columns:
        audit.info(
            "K",
            "inundation label column",
            "present as 'label' / 'label_meaning'",
            "This is the AI #2 outcome. It must not be used as a model input. Class 2 must not be recoded as 0.",
        )

    if calendar_cols:
        audit.info(
            "K",
            "timestamp-derived calendar columns",
            ", ".join(calendar_cols),
            "Derived from timestamp, not from the inundation target. Not baseline AI #2 features. Do not treat as target leakage.",
        )

    dup_info = []
    if {"rain_1h", "rain_lag_1h"}.issubset(df.columns):
        eq = bool((df["rain_1h"] == df["rain_lag_1h"]).all())
        dup_info.append(f"rain_1h identical to rain_lag_1h: {eq}")
    if {"precipitation"}.issubset(df.columns) and "rain_1h" in df.columns:
        eqp = bool((df["precipitation"] == df["rain_1h"]).all())
        dup_info.append(f"precipitation identical to rain_1h: {eqp}")
    if dup_info:
        audit.info("K", "duplicated rainfall information", "; ".join(dup_info), "Reported only; columns were not dropped.")

    weather_broadcast = []
    if {"timestamp"}.issubset(df.columns):
        weather_like = [
            c
            for c in df.columns
            if c
            in {
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "wind_speed_10m",
                "precipitation",
                "rain_lag_1h",
                "rain_lag_3h",
                "rain_lag_6h",
                "rain_1h",
                "rain_3h",
                "rain_6h",
                "rain_12h",
                "rain_24h",
                "pressure_change_3h",
                "pressure_change_6h",
                "humidity_change_3h",
                "humidity_change_6h",
                "hour",
                "month",
                "day_of_year",
            }
        ]
        for col in weather_like:
            nunique_per_ts = df.groupby("timestamp")[col].nunique(dropna=False)
            if (nunique_per_ts <= 1).all():
                weather_broadcast.append(col)
        audit.info(
            "K",
            "weather features constant within timestamp (city-level broadcast)",
            ", ".join(weather_broadcast) if weather_broadcast else "none detected",
            "Not target leakage. Rainfall/weather is not cell-specific in this dataset.",
        )

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    audit.heading("STAGE 2 AUDIT SUMMARY")
    n_fail = len(audit.fail_issues)
    n_pass = sum(1 for f in audit.findings if f["status"] == "PASS")
    n_info = sum(1 for f in audit.findings if f["status"] == "INFO")
    audit.add(f"PASS checks: {n_pass}")
    audit.add(f"FAIL checks: {n_fail}")
    audit.add(f"INFO rows:   {n_info}")

    audit.add("")
    audit.add("STAGE 2 AUDIT COMPLETE")
    if n_fail == 0:
        audit.add("STATUS: PASS")
    else:
        audit.add("STATUS: FAIL")
        audit.add("Exact issues:")
        for i, issue in enumerate(audit.fail_issues, 1):
            audit.add(f"  {i}. {issue}")

    write_outputs(audit)


def write_outputs(audit: Audit):
    AUDIT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit.findings).to_csv(AUDIT_CSV_PATH, index=False)
    AUDIT_TXT_PATH.write_text("\n".join(audit.lines) + "\n", encoding="utf-8")
    print("")
    print(f"Saved: {AUDIT_CSV_PATH}")
    print(f"Saved: {AUDIT_TXT_PATH}")


if __name__ == "__main__":
    main()
