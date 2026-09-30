# Graph Report - chennai-flood-early-warning  (2026-09-25)

## Corpus Check
- 107 files · ~58,318 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .csv 20, (none) 2, .joblib 2)

## Summary
- 659 nodes · 1098 edges · 142 communities (18 shown, 124 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 126
- Community 127
- Community 129
- Community 131
- Community 133
- Community 134
- Community 135
- Community 136
- Community 138
- Community 139
- Community 140

## God Nodes (most connected - your core abstractions)
1. `load_registered()` - 20 edges
2. `collect_oof_scores()` - 15 edges
3. `assess_risk()` - 15 edges
4. `predict_end_to_end()` - 13 edges
5. `SchemaValidationError` - 13 edges
6. `run_loeo_experiment()` - 13 edges
7. `fetch_weather()` - 12 edges
8. `canonicalize_time_coordinate()` - 11 edges
9. `log()` - 11 edges
10. `log()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_missing_required_feature_rejected_not_silently_filled()` --uses--> `SchemaValidationError`  [INFERRED]
  tests/test_inference.py → src/inference/model_loader.py
- `test_alert_thresholds_are_monotonically_increasing()` --calls--> `Settings`  [EXTRACTED]
  tests/test_config.py → src/config.py
- `test_default_settings_load()` --calls--> `Settings`  [EXTRACTED]
  tests/test_config.py → src/config.py
- `test_env_var_overrides_default()` --calls--> `Settings`  [EXTRACTED]
  tests/test_config.py → src/config.py
- `test_no_credential_fields_exist()` --uses--> `Settings`  [INFERRED]
  tests/test_config.py → src/config.py

## Import Cycles
- None detected.

## Communities (142 total, 124 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (43): numpy, os, pandas, pyproj, scipy_spatial, sklearn_metrics, sklearn_model_selection, # IMPORTANT: (+35 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (46): BaseModel, fastapi, field_validator, get, post, alerts(), _cells_to_dicts(), health() (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (38): dataclasses, pydantic, pydantic_settings, SIH26071 - centralized configuration. Single source of truth for paths,…, SIH26071 - Model loading layer. Separates model I/O and schema validation from…, Alert, generate_alert(), SIH26071 - alert / action engine. Maps a risk_class (from… (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (42): json, LogisticRegression, sklearn_linear_model, sklearn_preprocessing, assign_spatial_blocks(), class_counts(), collect_oof_scores(), evaluate_on_test() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (26): SIH26071 - STAGE 8 Evaluation module for End-to-End Retrospective Backtesting., SIH26071 - STAGE 8 End-to-End Retrospective Backtesting Engine., TestEndToEndTemporalIntegrity, dotenv, geopandas, matplotlib_pyplot, osmnx, pathlib (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (31): Exception, logging, patch, requests, ChennaiPoint, fetch_weather(), IngestionError, _parse_response() (+23 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (17): BaseSettings, importlib, Path, Settings, sys, SIH26071 - tests for centralized configuration., Config must never hold secrets -- verified by field-name inspection, not just a…, test_alert_thresholds_are_monotonically_increasing() (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (30): datetime, analyze_sample(), authenticate(), build_required_half_hour_set(), check_environment(), compare_with_openmeteo(), download_sample(), extract_valid_values() (+22 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (10): fastapi_testclient, clear_cache(), Testing/debug helper -- not used by the API in normal operation., _clear_cache(), fixture, SIH26071 - API endpoint tests. Uses FastAPI's TestClient (in-process, no…, _clear_cache(), fixture (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (23): DataArray, Dataset, math, main(), Audit Stage 5.4 native missing cells and fallback spatial support., main(), Resolve Stage 5.4 missing-cell relevance using existing CMR geometry., main() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (21): load_model(), load_registered(), _load_xgb_json(), LoadedModel, DataFrame, Path, Predict positive-class probability. Validates schema first, then selects…, For regressors (e.g. the Stage 6 rainfall-amount regressor). (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (12): ambiguous_python_import_677103912e4b, pred_df(), fixture, SIH26071 - Stage 8 end-to-end backtest integrity tests. These test the real…, Static check: run_end_to_end_backtest.py must never call any threshold-…, Independent recomputation of stage8_end_to_end_metrics.csv directly from the…, The model used to score an episode's cells must have been trained on the OTHER…, Every threshold used in Stage 8 must match a value already present in Stage 7's… (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (19): BaseGeometry, Series, shapely_geometry_base, shapely_ops, shapely_validation, dissolve_all(), find_timestamp_field(), km2() (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (12): pytest, re, _apply_feature_formulas(), SIH26071 - Stage 6 leakage tests. Tests 1-6 independently verify the feature-…, Reproduces the exact formulas from src/data/create_rainfall_features.py., The most important leakage test: proves future rainfall cannot alter predictors…, _synthetic_series(), test_1_lag_features_use_only_past_values() (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.35
Nodes (16): joblib, get_model_predictions(), hr(), load_full_dataset(), load_loeo_model(), log(), main(), DataFrame (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.26
Nodes (15): chronological_validation_split(), classification_metrics(), classifier(), csi(), fit_and_predict(), load_dataset(), main(), SIH26071 - Stage 6 Leakage-safe retrospective and walk-forward forecasting for… (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (6): Audit, describe_numeric(), fmt_ts(), main(), SIH26071 - STAGE 2 Read-only audit of the inundation-risk ML dataset. This…, write_outputs()

### Community 17 - "Community 17"
Cohesion: 0.36
Nodes (8): direction_for_episode(), frozen_threshold(), load_ai2_with_ai1(), load_frozen_classifier(), load_stage7_comparison(), main(), SIH26071 - Stage 8: end-to-end retrospective backtest. METHODOLOGICAL SCOPE --…, The leakage-safe direction for scoring `episode`'s cells is the row where…

## Knowledge Gaps
- **17 isolated node(s):** `Chennai Flood Early Warning System`, `Model Card`, `Requirements.txt - Pinned reproducibility environment`, `src/config.py - centralized settings`, `src/inference/model_loader.py - model I/O + schema validation` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 320 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **124 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LoadedModel` connect `Community 10` to `Community 2`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `SchemaValidationError` connect `Community 1` to `Community 2`, `Community 10`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **What connects `Chennai Flood Early Warning System`, `Model Card`, `Requirements.txt - Pinned reproducibility environment` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06019871420222092 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10122448979591837 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08019323671497584 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.10782241014799154 - nodes in this community are weakly interconnected._