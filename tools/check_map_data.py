"""Validate map images, calibration and layer data after a refresh.

Usage:  python tools/check_map_data.py [--write-manifest]
Exit code 0 = everything consistent, 1 = problems found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.coordinate_transform import load_calibration  # noqa: E402
from core.data_loader import LAYER_FILES  # noqa: E402


def _image_size(path: Path) -> tuple[int, int]:
    from PySide6.QtGui import QImageReader

    size = QImageReader(str(path)).size()
    return size.width(), size.height()


def _points(item: dict) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if isinstance(item.get("position"), (list, tuple)) and len(item["position"]) >= 2:
        pts.append((float(item["position"][0]), float(item["position"][1])))
    for key in ("polygon", "points"):
        for pair in item.get(key, []) or []:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                pts.append((float(pair[0]), float(pair[1])))
    for pair_list in item.get("polygons", []) or []:
        for pair in pair_list:
            pts.append((float(pair[0]), float(pair[1])))
    return pts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    problems: list[str] = []
    maps = ROOT / "assets" / "map"
    base, water = maps / "gateway.webp", maps / "gateway_water.webp"

    for path in (base, water, maps / "calibration.json"):
        if not path.exists():
            problems.append(f"missing {path.relative_to(ROOT)}")
    if problems:
        print("\n".join(problems))
        return 1

    cal = load_calibration(maps / "calibration.json")
    base_size, water_size = _image_size(base), _image_size(water)
    print(f"base map  : {base_size[0]} x {base_size[1]}")
    print(f"water map : {water_size[0]} x {water_size[1]}")
    if base_size != water_size:
        problems.append("water overlay size differs from base map")
    if (round(cal.pixel_max_x), round(cal.pixel_max_y)) != base_size:
        problems.append(
            f"calibration pixel_bounds max is ({cal.pixel_max_x:g}, {cal.pixel_max_y:g}) "
            f"but the base map is {base_size[0]} x {base_size[1]}"
        )

    lo_x, hi_x = sorted((cal.world_min_x, cal.world_max_x))
    lo_y, hi_y = sorted((cal.world_min_y, cal.world_max_y))
    for name, filename in LAYER_FILES.items():
        if name == "custom_markers":
            continue
        path = ROOT / "data" / filename
        if not path.exists():
            problems.append(f"missing data/{filename}")
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            items = value.get("items", value) if isinstance(value, dict) else value
            assert isinstance(items, list)
        except Exception as exc:  # noqa: BLE001 - report any parse problem
            problems.append(f"data/{filename}: cannot parse ({exc})")
            continue
        outside = 0
        for item in items:
            try:
                for x, y in _points(item):
                    if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
                        outside += 1
            except (TypeError, ValueError):
                problems.append(f"data/{filename}: item with bad coordinates: {str(item)[:60]}")
        version = (value.get("source", {}) if isinstance(value, dict) else {}).get("map_version", "?")
        print(f"{filename:<18} {len(items):>4} items  map_version={version}")
        if outside:
            problems.append(f"data/{filename}: {outside} coordinates outside world bounds")

    # Calibration must round-trip so pins land where the game says.
    for x, y in ((0.0, 0.0), (lo_x + 1000, lo_y + 1000), (hi_x - 1000, hi_y - 1000)):
        px, py = cal.world_to_pixel(x, y)
        bx, by = cal.pixel_to_world(px, py)
        if abs(bx - x) > 1 or abs(by - y) > 1:
            problems.append(f"calibration does not round-trip at ({x:g}, {y:g})")

    if args.write_manifest:
        manifest = {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [base, water, maps / "calibration.json", *sorted((ROOT / "data").glob("*.json"))]
        }
        (maps / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("wrote assets/map/MANIFEST.json")

    if problems:
        print("\nPROBLEMS:")
        print("\n".join(f" - {p}" for p in problems))
        return 1
    print("\nOK: map data is consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
