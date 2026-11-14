# Roadmap

## Current release

- [x] Detailed architecture diagrams and sidecars
- [x] Static architecture dashboard
- [x] Searchable service catalog and filters
- [x] Inspector, zoom, responsive layout, and themes
- [x] Local asset provenance and checksum validation
- [x] Deterministic fixture-based rendering

## Phase 2: Board dashboard and drafted diagrams

- Outcome: the atlas reads as an ops dashboard, and flowcharts are hand-placed, gutter-routed static SVG instead of auto-layout output.
- Dependencies and risks: no remote fonts, so Roboto is vendored; drafted geometry must stay clean as diagrams change, so the geometry check runs in the gate; redaction must hold, so output is scanned for private markers.
- Exit criteria: SPEC phase 2 acceptance criteria pass; the owner approves the proof diagram before the remaining flowcharts are converted.
- Validation: `PATH="$PWD/.venv/bin:$PATH" bin/validate`, a second render with an empty diff, and Chromium screenshots at 1440 px and 390 px in light and dark.

## Next

- [ ] Add automated Chromium checks to the local validation gate.
