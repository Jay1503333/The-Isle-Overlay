# Refreshing map data after a game update

Map data is plain local files; the app never downloads anything. The current
snapshot is Gateway v0.21.772 (see `assets/map/SOURCE.md`).

| What | File(s) |
| --- | --- |
| Base map image | `assets/map/gateway.webp` |
| Water overlay | `assets/map/gateway_water.webp` (same pixel size as the base map) |
| World <-> pixel calibration | `assets/map/calibration.json` |
| POIs and zones | `data/*.json` (`locations`, `migrations`, `sanctuaries`, `water`, `updrafts`, `food`, `ai`, `gastrolith`, `salt_licks`, `spawns`, `patrol_zones`) |

## Steps

1. **Back up** `assets/map` and `data` (or use git).
2. **Replace the images** with the new export at the same coordinate frame. Keep the file names.
   If the new image has different pixel dimensions, update `pixel_bounds.max_x` / `max_y`
   in `calibration.json` to the new width/height. Do not change `world_bounds`,
   `swap_axes`, `invert_x` or `invert_y` unless the game's world size really changed.
3. **Update the layer JSON** in `data/`. Each file is `{"format_version":1, "source":{...}, "items":[...]}`.
   Points use `"position": [x, y]`, zones use `"polygon": [[x, y], ...]`, in world coordinates
   (Unreal cm, the same numbers Copy Location gives you). Update each file's `source.map_version`
   and `source.retrieved`.
4. **Validate**:

   ```text
   python tools/check_map_data.py
   ```

   It checks that the images exist and are the same size, that calibration matches the base
   image, that every layer parses, that every coordinate lies inside the world bounds, and
   that calibration round-trips. Add `--write-manifest` to record file hashes in
   `assets/map/MANIFEST.json` for your own records.
5. **Check alignment visually**: run the app, copy a known in-game location (for example a
   landmark you can stand next to) and confirm the pin lands on it.
6. **Update `assets/map/SOURCE.md`** with the new version and date.
7. **Rebuild the app** (`build_windows.bat`) or, for an already-built folder, copy the
   files into the build's `assets\map` and `data` folders. The *Reload map data* button in
   the Layers panel reloads `data/*.json` without restarting; the base image is read at start-up.

Note: `tests/test_bundled_snapshot.py` pins the SHA-256 of the bundled base image on purpose.
After an intentional refresh, update the hash it expects.
