from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[2]

STUDY_AREA = (
    BASE_DIR
    / "data"
    / "processed"
    / "chennai_cmr_study_area.geojson"
)

LABEL_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "flood_labels"
    / "flood_labels_20211110_1800.geojson"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "flood_labels"
    / "flood_labels_20211108_2300_map.png"
)


print("Loading study area...")
study = gpd.read_file(STUDY_AREA)

print("Loading flood labels...")
labels = gpd.read_file(LABEL_FILE)

print("\nLabel data:")
print(labels[["label", "label_meaning", "area_km2"]])

fig, ax = plt.subplots(figsize=(12, 10))

# Study area boundary
study.boundary.plot(
    ax=ax,
    linewidth=1
)

# Plot each class separately
class_0 = labels[labels["label"] == 0]
class_1 = labels[labels["label"] == 1]
class_2 = labels[labels["label"] == 2]

class_0.plot(
    ax=ax,
    alpha=0.15,
    label="Class 0 - No inundation evidence"
)

class_2.plot(
    ax=ax,
    alpha=0.45,
    label="Class 2 - Uncertain"
)

class_1.plot(
    ax=ax,
    alpha=0.8,
    label="Class 1 - Observed inundation"
)

ax.set_title(
    "Observed Inundation - Chennai - 10 Nov 2021 18:00"
)

# Zoom into the observed inundation area
if not class_1.empty:
    minx, miny, maxx, maxy = class_1.total_bounds

    padding_x = (maxx - minx) * 0.15
    padding_y = (maxy - miny) * 0.15

    ax.set_xlim(minx - padding_x, maxx + padding_x)
    ax.set_ylim(miny - padding_y, maxy + padding_y)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

ax.legend()

plt.tight_layout()

plt.savefig(
    OUTPUT_FILE,
    dpi=200,
    bbox_inches="tight"
)

plt.show()

print("\nMap saved to:")
print(OUTPUT_FILE)