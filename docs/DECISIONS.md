# Development notes

A few choices in this project are intentional and worth keeping in mind when changing the code.

## Keep the companion separate from the game

Coordinate updates come from either copied text or a user-selected patch of screen pixels for OCR. The app should not read game memory, inject into the renderer, alter files, or send input to The Isle.

## Prefer boring, local state

Settings, calibration, custom markers, and breadcrumbs live locally. There is no account system or telemetry, and normal use should work offline.

## UI copy should sound like a player wrote it

The interface should be clear without sounding overly formal. Short labels are best in toolbars; dialogs can use plain, practical wording that explains what the player should do next.

## Mini Map editing must be hard to trigger accidentally

The overlay should default to click-through during play. Editing mode exists for zooming, panning, resizing, and toggling follow mode, then it should get out of the way again.

## Keep map tuning grouped

The settings dialog intentionally exposes broad controls such as zone intensity and marker opacity instead of every raw layer value. The raw values still exist in settings, but the user-facing controls should stay simple.

## Bad readings are ignored, not trusted

Clipboard and OCR readings pass through one duplicate/outlier filter (`core/position_filter.py`).
A sudden jump is held back until a second nearby reading confirms it, so one misread cannot
move the pin, but respawns and teleports still work. The filter is pure Python with no I/O.

## Optional embedded web map

The Live Web Map window is an ordinary embedded browser that the user opens and signs in to
themselves. It is opt-in, https-only, never feeds the position filter, and does not read or
automate the page. The rest of the app stays offline by default.
