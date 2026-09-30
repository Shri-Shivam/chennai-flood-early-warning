import pandas as pd

# =========================================================
# LOAD DATASET
# =========================================================

file_path = "data/processed/rainfall_ml_dataset.csv"

df = pd.read_csv(file_path, parse_dates=["time"])

print("=" * 65)
print("RAINFALL ML DATASET INSPECTION")
print("=" * 65)

# =========================================================
# BASIC INFORMATION
# =========================================================

print("\nDataset shape:")
print(f"Rows    : {len(df)}")
print(f"Columns : {len(df.columns)}")

print("\nTime range:")
print(f"Start: {df['time'].min()}")
print(f"End  : {df['time'].max()}")

# =========================================================
# MISSING VALUES
# =========================================================

print("\nMissing values:")
print("-" * 40)

missing = df.isnull().sum()

print(missing[missing > 0])

if missing.sum() == 0:
    print("No missing values.")

# =========================================================
# TARGET
# =========================================================

print("\nTarget distribution:")
print("-" * 40)

print(df["target"].value_counts())

print("\nTarget percentage:")

print(
    (df["target"].value_counts(normalize=True) * 100)
    .round(3)
)

# =========================================================
# FUTURE RAINFALL CHECK
# =========================================================

print("\nFuture 6-hour rainfall:")
print("-" * 40)

print(
    df["future_6h_rain"]
    .describe()
)

# =========================================================
# POSITIVE EXAMPLES
# =========================================================

positive = df[df["target"] == 1]

print("\nPositive examples:")
print("-" * 40)

print(
    positive[
        [
            "time",
            "future_6h_rain",
            "rain_3h",
            "rain_6h",
            "rain_12h",
            "rain_24h",
            "surface_pressure",
            "relative_humidity_2m"
        ]
    ].head(10).to_string(index=False)
)

# =========================================================
# FEATURE CORRELATION WITH TARGET
# =========================================================

print("\nFeature correlation with target:")
print("-" * 40)

numeric_df = df.select_dtypes(include="number")

correlation = (
    numeric_df.corr()["target"]
    .drop("target")
    .abs()
    .sort_values(ascending=False)
)

print(correlation)

# =========================================================
# FINAL CHECK
# =========================================================

print("\n" + "=" * 65)
print("DATASET INSPECTION COMPLETE")
print("=" * 65)