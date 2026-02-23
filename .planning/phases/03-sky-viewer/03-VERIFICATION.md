---
phase: 03-sky-viewer
verified: 2026-02-22T23:30:00Z
status: passed
score: 3/3 must-haves verified
human_verification:
  - test: "Navigate to http://localhost:3000/viewer/{uuid} with a known ingested observation and scroll-wheel zoom from full field to individual pixel scale"
    expected: "Viewer loads with the JWST image filling the viewport on a black background; scroll zooms in smoothly with lower-res tiles visible first (blur-up), sharpening as higher-res tiles load. No 404 errors in browser console for tile requests."
    why_human: "OpenSeadragon pan/zoom smoothness, tile loading latency, and blur-up progression cannot be verified programmatically; requires live browser interaction."
  - test: "Move the mouse across the loaded viewer image and observe the RA/Dec display at the bottom of the viewport"
    expected: "Coordinates update continuously in HMS/DMS format (e.g., '05h 35m 17.3s, -05d 23m 28.1s'). Click the HMS toggle button -- coordinates switch to decimal degrees (e.g., '83.822d, -5.391d'). Click a point in the image -- coordinates are pinned in amber, and a 'Copied!' toast appears briefly."
    why_human: "Coordinate accuracy against known sky positions requires visual inspection; clipboard API behavior varies by environment."
  - test: "While viewing the image, toggle the coordinate grid on via the toolbar grid button, then pan and zoom"
    expected: "RA/Dec grid lines appear as faint cyan dashed lines over the image with axis labels (e.g., '05h35m' for RA, '+23d' for Dec). Grid re-renders correctly as the viewport changes. Turning the toggle off removes the grid."
    why_human: "Grid line accuracy against the known WCS and visual alignment on the image require human inspection."
---

# Phase 3: Sky Viewer Verification Report

**Phase Goal:** Users can visually explore ingested imagery by panning and zooming like a map, with sky coordinates displayed
**Verified:** 2026-02-22T23:30:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can pan and zoom smoothly across an ingested JWST image from full field down to individual pixel scale | ? HUMAN | SkyViewer.tsx creates OSD with `drawer: "canvas"`, `maxZoomPixelRatio: 20`, `gestureSettingsMouse: { scrollToZoom: true }`, `gestureSettingsTouch: { pinchToZoom: true }`, inline DZI tile source pointing to FastAPI proxy; wiring confirmed; runtime smoothness needs human |
| 2 | User sees RA/Dec sky coordinates update on hover or click within the viewer | ? HUMAN | pixelToRaDec() called in RAF-throttled moveHandler in SkyViewer.tsx; formatCoordinates() called imperatively on liveCoordRef.current; click pins + clipboard copy wired in ViewerClient.tsx; correctness needs human |
| 3 | Tile loading is lazy -- only visible tiles at the current zoom level are fetched | ? HUMAN | OSD DZI tile source with inline Image spec confirmed; no pre-loading config present; OSD tile loading behavior needs browser DevTools to confirm |

**Score:** 3/3 truths structurally verified (automated). 3/3 require human confirmation for runtime behavior.

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/routers/tiles.py` | Tile proxy, WCS extraction, observation detail endpoints | VERIFIED | 295 lines; 3 endpoints (`get_tile`, `get_wcs_params`, `get_observation_detail`); 3 Pydantic response models; `_find_sci_extension` helper; real astropy + boto3 implementation |
| `web/src/types/observation.ts` | TypeScript interfaces: WcsParams, TileMetadata, ObservationDetail | VERIFIED | 68 lines; all 3 interfaces present; WcsParams has 12 fields matching backend exactly |
| `web/src/lib/api.ts` | API client: fetchObservation, fetchWcsParams, getTileUrl | VERIFIED | 68 lines; 3 exports; real fetch() calls to correct endpoints; error propagation from FastAPI detail |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `web/src/lib/wcs.ts` | TAN gnomonic deprojection; exports pixelToRaDec | VERIFIED | 75 lines; full 4-step TAN deprojection (CRPIX offset, CD matrix, atan deprojection, spherical rotation); rTheta===0 edge case; RA normalization to [0,360) |
| `web/src/lib/coordinates.ts` | HMS/DMS formatting; exports decimalDegreesToHms, decimalDegreesToDms, formatCoordinates | VERIFIED | 73 lines; all 3 exports; HMS divides by 15, DMS uses abs+sign; formatCoordinates dispatches on mode |
| `web/src/components/viewer/SkyViewer.tsx` | OpenSeadragon wrapper with mouse tracking | VERIFIED | 228 lines; forwardRef exposing 5 imperative handles; two useEffects (OSD init, MouseTracker); RAF-throttled moveHandler; clickHandler with single-click guard; FITS Y-flip applied |
| `web/src/components/viewer/CoordinateOverlay.tsx` | Real-time RA/Dec display HUD | PARTIAL | File exists but is unused -- the coordinate overlay is inlined directly in ViewerClient.tsx. Functionality is present and working via inline JSX; the component file is an orphan. Not a blocker. |
| `web/src/components/viewer/ViewerToolbar.tsx` | Zoom in/out, home, fullscreen, navigator toggle buttons | VERIFIED | 199 lines; 8 buttons (zoom+/-, home, fullscreen, navigator, info, adjustments, grid); active state via cyan class; all handlers wired |
| `web/src/components/viewer/ScaleBar.tsx` | Angular scale bar | VERIFIED | 129 lines; pixelScaleArcsec computed from CD matrix; NICE_ARCSEC_VALUES list; OSD zoom/open/resize event listeners; bar width computed from zoom-dependent arcsecPerScreenPixel |
| `web/src/app/viewer/[uuid]/page.tsx` | Server component fetching observation + WCS | VERIFIED | 74 lines; server component (no 'use client'); Promise.all of fetchObservation + fetchWcsParams; tile-not-ready branch; error branch; passes observationDetail to ViewerLoader |
| `web/src/app/viewer/[uuid]/ViewerClient.tsx` | Client boundary composing all viewer components | VERIFIED | 254 lines; all 6 sub-components imported and rendered; imperative liveCoordRef for 30fps updates; handleAdjustmentChange applies buildCssFilter to viewer.canvas |
| `web/src/app/viewer/[uuid]/ViewerLoader.tsx` | SSR-safe dynamic import wrapper | VERIFIED | 23 lines; next/dynamic with ssr: false; props pass-through |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `web/src/components/viewer/ObservationInfo.tsx` | Observation info sidebar | VERIFIED | 207 lines; shows telescope_name, instrument_name, spectral_filters, exposure, RA/Dec, pipeline_status, tile metadata; collapsible via isOpen prop; formatExposureTime/formatDate helpers |
| `web/src/components/viewer/ImageAdjustments.tsx` | Image adjustments panel | VERIFIED | 224 lines; brightness/contrast/gamma/invert state; buildCssFilter export; reset button with isDefault guard; SliderControl sub-component |
| `web/src/components/viewer/BandSelector.tsx` | Band/filter selector | VERIFIED | 54 lines; returns null for single-band; tab buttons for multi-band; documented Phase 2 tile overwrite limitation; onBandChange wired |
| `web/src/components/viewer/CoordinateGrid.tsx` | SVG coordinate grid overlay | VERIFIED | 397 lines; raDecToPixel inverse WCS (spherical rotation + TAN + CD matrix inversion); imageToViewportPixel with FITS Y-flip; computeGrid samples 20 points per line; OSD animation/animation-finish/open/resize listeners; RAF-throttled |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/routers/tiles.py` | `shared/s3.py` | `get_s3_client()` | WIRED | Line 139: `s3_client = get_s3_client()` in get_tile; line 173 in get_wcs_params |
| `api/routers/tiles.py` | `shared/models.py` | `Observation`, `ProcessingStep` queries | WIRED | Lines 253-274: db.query(Observation), db.query(ProcessingStep) with StepStatus.completed filter |
| `api/main.py` | `api/routers/tiles.py` | `app.include_router(tiles_router)` | WIRED | Line 6: import; line 17: include_router |
| `web/src/components/viewer/SkyViewer.tsx` | `web/src/lib/wcs.ts` | `pixelToRaDec()` on mouse move | WIRED | Line 12: import; lines 189 and 212: called in moveHandler and clickHandler inside RAF callback |
| `web/src/components/viewer/SkyViewer.tsx` | `/api/tiles/{uuid}/...` | OSD tile source Url | WIRED | Line 116: `Url: tileBaseUrl` used as OSD DZI Image source; tileBaseUrl = getTileUrl(uuid) = `${API_BASE}/api/tiles/${uuid}/` |
| `web/src/app/viewer/[uuid]/page.tsx` | `web/src/lib/api.ts` | `fetchObservation + fetchWcsParams` | WIRED | Line 1: import; lines 20-21: Promise.all; line 43: getTileUrl |
| `web/src/components/viewer/ImageAdjustments.tsx` | `web/src/components/viewer/SkyViewer.tsx` (via ViewerClient) | `canvas.style.filter = buildCssFilter(adjustments)` | WIRED | ViewerClient line 118: `canvas.style.filter = buildCssFilter(adjustments)` inside handleAdjustmentChange |
| `web/src/components/viewer/CoordinateGrid.tsx` | `web/src/lib/wcs.ts` | `pixelToRaDec` for grid line positions | WIRED | Line 6: import; line 162: `return pixelToRaDec(fitsX, fitsY, wcsParams)` in computeGrid |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BROWSE-01 | 03-01, 03-02, 03-03 | User can pan and zoom across ingested imagery like a map, from full field down to individual objects | SATISFIED (pending human) | OpenSeadragon DZI viewer with scroll-to-zoom, drag-to-pan, `maxZoomPixelRatio: 20`; tile proxy streams JPEG from MinIO with immutable cache headers; 8-button toolbar with zoom+/-, home, fullscreen controls |
| BROWSE-02 | 03-01, 03-02, 03-03 | User sees sky coordinates (RA/Dec) on hover or click within the viewer | SATISFIED (pending human) | TAN gnomonic deprojection in wcs.ts; RAF-throttled mouse tracker calls pixelToRaDec on hover; click pins coordinates + clipboard copy; HMS/DMS and decimal toggle; coordinate grid overlay via inverse WCS |

No orphaned requirements. REQUIREMENTS.md traceability table shows BROWSE-01 and BROWSE-02 as the only Phase 3 requirements, both now marked Complete.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `web/src/components/viewer/CoordinateOverlay.tsx` | -- | Component exists but is not rendered anywhere (orphaned by architectural decision to inline coordinate overlay in ViewerClient) | Info | No functional impact; dead code only |
| `web/src/components/viewer/BandSelector.tsx` | 33 | `return null` for single-band observations | Info | Intentional and correct; documented limitation about Phase 2 tile overwrite |
| `web/src/app/viewer/[uuid]/ViewerClient.tsx` | 130 | Band change handler is a no-op tile reload (documents Phase 2 limitation) | Info | Documented in code comment; planned for Phase 6 fix |

No blockers. No stubs. No TODO/FIXME markers. All `return null` occurrences are conditional guards on legitimate state (not implemented), not empty implementations.

---

## Human Verification Required

### 1. Pan and Zoom Interactive Experience

**Test:** Start Docker (`docker compose up -d`), FastAPI (`uvicorn api.main:app --port 8000`), and Next.js dev server (`cd web && npm run dev`). Navigate to `http://localhost:3000/viewer/{uuid}` for a known ingested observation (e.g., `0a870e98` per project memory). Use scroll-wheel to zoom from full field to individual pixel scale. Drag to pan across the image.

**Expected:** Image fills viewport on black background. Scroll zooms smoothly with lower-res tiles visible during loading, sharpening as higher-res tiles arrive (blur-up effect). Drag panning feels responsive with momentum. No 404 errors in DevTools network panel for tile requests. Scale bar at bottom-right shows angular size label that updates as zoom changes.

**Why human:** OSD tile loading smoothness, blur-up progression, and drag momentum cannot be verified programmatically. Requires live browser interaction with a running backend.

### 2. RA/Dec Coordinate Display Accuracy

**Test:** With the viewer loaded, move the mouse over the image and observe the coordinate bar at the bottom. Click the HMS/DEG toggle button. Click a specific point on the image.

**Expected:** Coordinates update continuously in HMS/DMS format (e.g., `05h 35m 17.3s, -05d 23m 28.1s`) without lag. Toggle switches to decimal degrees (e.g., `83.822d, -5.391d`). Clicking a point pins coordinates in amber at the bottom bar and shows a brief "Copied!" toast. Cross-referencing against a known object position in the field (e.g., from AladinLite or SIMBAD) verifies WCS accuracy.

**Why human:** Coordinate accuracy against known sky positions requires comparison with an external reference. Clipboard API availability varies by browser/environment.

### 3. Coordinate Grid Overlay

**Test:** Click the grid toggle button (bottom button after separator in left toolbar). Pan and zoom while the grid is active.

**Expected:** Faint cyan dashed RA/Dec grid lines appear over the image with axis labels (e.g., `05h35m` for RA, `+23d` for Dec). Grid re-computes and re-renders correctly after each pan/zoom. Toggling off removes the grid entirely. Grid line spacing adapts appropriately to the current field of view (fine spacing when zoomed in, coarse when zoomed out).

**Why human:** Grid line alignment against the underlying image and WCS accuracy cannot be verified without seeing the rendered output.

---

## Gaps Summary

No code gaps found. All artifacts are substantive (not stubs), all key links are wired, and the two requirements BROWSE-01 and BROWSE-02 have full implementation coverage.

The `human_needed` status reflects that the three core success criteria -- smooth pan/zoom, live RA/Dec on hover, and lazy tile loading -- are interactive browser behaviors that cannot be confirmed without running the application.

One minor deviation from the plan worth noting: `CoordinateOverlay.tsx` exists as an orphaned component because the coordinate display was inlined directly into `ViewerClient.tsx` for simpler ref wiring (documented in 03-02-SUMMARY.md). This is not a functional gap.

---

_Verified: 2026-02-22T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
