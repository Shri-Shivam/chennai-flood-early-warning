import rasterio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
dem_path = PROJECT_ROOT / "data" / "raw" / "chennai_cop30.tif"

with rasterio.open(dem_path) as src:
    print("DEM opened successfully!")
    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)
    print("Bands:", src.count)

    data = src.read(1, masked=True)

    print("Minimum elevation:", float(data.min()))
    print("Maximum elevation:", float(data.max()))
    print("Mean elevation:", float(data.mean()))