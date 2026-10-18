# Changelog

## 1.1.0

### Distribution
- Reproducible Windows build (`tools/build_exe.py`, `build_windows.bat`) producing a
  single-folder `TheIsleCompanion` with Windows version metadata, an icon,
  `HOW_TO_RUN.txt`, `MAP_DATA.md`, `CHANGELOG.md` and `VERSION.txt`, plus a ready-to-share zip.
- GitHub Actions workflow builds the Windows zip on every tag / manual run.
- App no longer crashes at start-up if its folder is read-only (logging falls back safely).

### Map
- Water overlay now defaults to 35% opacity so the terrain underneath stays visible (the solid cyan hid land in marsh areas).

### Live web map (optional)
- New "Live Web Map" toolbar button opens a server's own web map (default https://playorigin.gg/map,
  change `web_map_url` in settings; https only) in an always-on-top window with an opacity slider,
  Reload, drag-to-move, resize, and click-through lock (Edit Web Map unlocks it).
- Easy to resize: drag any edge or corner; drag the top bar to move; page zoom - / + buttons; compact
  default size. "Map only" (on by default) hides the site's menus so just the map fills the window
  (cosmetic, local, only on /map pages, can be switched off).
- You sign in on the site yourself; the sign-in is kept in `config/web_profile`. Nothing loads until you open
  the window. The Companion does not read the page, touch the game or send any input to it.

### Tracking
- Duplicate coordinates are ignored.
- Outlier rejection: a single bad copy / OCR misread can no longer teleport the pin.
  Two agreeing far-away readings (respawn, teleport) are accepted. Readings outside
  the Gateway map are rejected. Applies to both clipboard and OCR.
- Always-visible tracking indicator: ACTIVE / STALE / WAITING, source (Clipboard or OCR) and age.
- First-run "Getting started" guide: bind Copy Location, use Borderless Windowed, OCR setup.

### Mini Map
- Circular mini map is now the default for new installs.
- New heading arrow showing direction of travel (from the last two positions).
- Mini map now starts as a close-up (about 1.5 km across) centered on you at the first position fix, instead of showing the whole island. A zoom you choose afterwards is kept.
- Independent opacity for map content and for buttons/labels.

### Maps and data
- `tools/check_map_data.py` validates image/calibration/layer data after a refresh;
  `docs/MAP_DATA.md` documents the refresh procedure. Calibration is unchanged.

### Tests
- New tests: position filter, tracking status, parser edge cases, heading arrow,
  opacity, first-run guide, click-through toggle.
