---
phase: 03-sky-viewer
plan: 03
subsystem: ui
tags: [react, openseadragon, wcs, css-filters, svg-overlay, coordinate-grid, image-adjustments, tailwind]

# Dependency graph
requires:
  - phase: 03-sky-viewer
    plan: 02
    provides: "OpenSeadragon viewer, ViewerClient client boundary (app/viewer/[uuid]/ViewerClient.tsx), ViewerToolbar, ScaleBar, coordinate overlay, SkyViewer component with forwardRef handle"
  - phase: 03-sky-viewer
    plan: 01
    provides: "Tile proxy endpoint, WCS extraction endpoint, observation detail endpoint, TypeScript interfaces, API client"
provides:
  - "Observation info sidebar showing telescope, instrument, filters, exposure time, tile metadata"
  - "Image adjustments panel with brightness/contrast/gamma/invert sliders and CSS filter application"
  - "Band selector tabs for multi-band observations (UI ready, awaiting tile isolation)"
  - "SVG coordinate grid overlay with RA/Dec lines computed via inverse WCS TAN deprojection"
  - "8-button toolbar (zoom in/out, home, fullscreen, navigator, info, adjustments, grid)"
  - "ViewerLoader SSR wrapper using next/dynamic with ssr: false"
affects: [06-search-browse]

# Tech tracking
tech-stack:
  added: []
  patterns: [css-filter-for-image-adjustments, inverse-wcs-tan-deprojection, svg-overlay-on-osd, raf-throttled-grid-recomputation, dynamic-import-ssr-false-wrapper]

key-files:
  created:
    - web/src/components/viewer/ObservationInfo.tsx
    - web/src/components/viewer/ImageAdjustments.tsx
    - web/src/components/viewer/BandSelector.tsx
    - web/src/components/viewer/CoordinateGrid.tsx
    - web/src/app/viewer/[uuid]/ViewerLoader.tsx
  modified:
    - web/src/components/viewer/ViewerToolbar.tsx
    - web/src/components/viewer/SkyViewer.tsx
    - web/src/app/viewer/[uuid]/ViewerClient.tsx
    - web/src/app/viewer/[uuid]/page.tsx

key-decisions:
  - "CSS filter for image adjustments (brightness/contrast/invert) applied to OSD canvas element via canvas.style.filter -- avoids WebGL or per-pixel manipulation"
  - "Gamma approximation via brightness factor: gammaFactor = pow(0.5, 1/gamma - 1), combined with brightness slider -- not a true per-pixel power-law but acceptable for Phase 3"
  - "Inverse WCS TAN deprojection (raDecToPixel) implemented in CoordinateGrid for RA/Dec -> pixel conversion, using CD matrix inversion and gnomonic projection math"
  - "ViewerLoader as SSR wrapper: next/dynamic with ssr: false to prevent OpenSeadragon from running during server-side rendering"
  - "OSD 6.x drawer set to 'canvas' (canvas2d) instead of default WebGL to avoid texture creation failures in some environments"
  - "Band selector UI built with documented limitation: Phase 2 overwrites tiles per FITS file, so band switching reloads same tiles until tile isolation is added"

patterns-established:
  - "CSS filter pattern: ImageAdjustments component manages local state, calls onAdjustmentChange callback, parent applies buildCssFilter() output to viewer.canvas.style.filter"
  - "SVG overlay pattern: CoordinateGrid renders absolutely-positioned SVG element over OSD canvas, listens to animation/animation-finish/open/resize events, RAF-throttles grid recomputation"
  - "Inverse WCS pattern: raDecToPixel() performs spherical rotation -> TAN projection -> CD matrix inversion -> CRPIX offset, used for computing grid line positions"
  - "SSR-safe OSD pattern: ViewerLoader (dynamic import, ssr: false) wraps ViewerClient to prevent OpenSeadragon from accessing DOM during server-side rendering"

requirements-completed: [BROWSE-01, BROWSE-02]

# Metrics
duration: 8min
completed: 2026-02-22
---

# Phase 3 Plan 03: Viewer Panels & Verification Summary

**Observation info sidebar, image adjustments (brightness/contrast/gamma/invert via CSS filter), SVG coordinate grid overlay with inverse WCS TAN deprojection, and band selector tabs -- completing the full sky viewer experience**

## Performance

- **Duration:** ~8 min (across two execution sessions, including human verification)
- **Started:** 2026-02-22T23:00:00Z
- **Completed:** 2026-02-22T23:08:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Observation info sidebar showing all provenance metadata: observation ID, telescope, instrument, filters, exposure time, pointing RA/Dec, pipeline status, and tile metadata (dimensions, tile count, zoom levels)
- Image adjustments panel with range sliders for brightness (0.5-2.0), contrast (0.5-2.0), gamma (0.1-3.0), invert toggle, and reset button -- applied as CSS filter on OSD canvas via `buildCssFilter()` function
- SVG coordinate grid overlay computing RA/Dec grid lines via inverse WCS TAN gnomonic deprojection (`raDecToPixel`), with adaptive "nice" spacing based on field of view, re-rendered on pan/zoom via RAF-throttled OSD event handlers
- Band selector tab UI for multi-band observations (renders only when `spectralFilters.length > 1`), with documented limitation about Phase 2 tile overwriting
- Extended ViewerToolbar from 5 to 8 buttons (added info, adjustments, grid toggles with active state highlighting in cyan)
- ViewerLoader SSR wrapper using `next/dynamic` with `ssr: false` to prevent OpenSeadragon from attempting DOM access during server-side rendering
- Human-verified: zoom, grid, brightness (0.95), contrast (1.75), gamma (0.35) settings produce clear imagery with visible stars against dark background
- Added "Deep Sky" preset (brightness 0.95, contrast 1.75, gamma 0.35) as one-click preset button alongside "Default", with active preset highlighted in cyan

## Task Commits

Each task was committed atomically:

1. **Task 1: Create observation info sidebar, image adjustments, band selector, and coordinate grid overlay** - `85d38fb` (feat) + `9121f61` (fix: ViewerLoader SSR wrapper, tile URL, drawer config)
2. **Task 2: Verify complete sky viewer experience** - checkpoint:human-verify, APPROVED
3. **Post-verification: Deep Sky preset** - `3f30ba6` (feat: add Deep Sky preset to image adjustments panel)

## Files Created/Modified

- `web/src/components/viewer/ObservationInfo.tsx` -- Collapsible right sidebar panel. Props: `observation: ObservationDetail`, `isOpen: boolean`, `onToggle: () => void`. Renders via sub-components: `InfoSection` (titled section with children), `InfoRow` (label-value flex row with optional monospace), `TileInfoSection` (dimensions, tile count, zoom levels from `TileMetadata`). Helpers: `formatExposureTime(seconds)` (seconds/min/hr display), `formatDate(isoString)` (locale-formatted date), `formatRaDec(ra, dec)` (4-decimal-place coordinates). Styled with `bg-zinc-900/90 backdrop-blur-sm`, 288px width, absolute right positioning.

- `web/src/components/viewer/ImageAdjustments.tsx` -- Collapsible left-side panel with range sliders. Exports: `ImageAdjustmentValues` interface (`brightness`, `contrast`, `gamma`, `invert`), default `ImageAdjustments` component, and `buildCssFilter(adjustments)` helper. State managed via `useState<ImageAdjustmentValues>` with `DEFAULTS` constant. `updateAdjustment(key, value)` calls `onAdjustmentChange` callback which parent uses to set `viewer.canvas.style.filter = buildCssFilter(adjustments)`. `SliderControl` sub-component renders `<input type="range">` with value display. Gamma approximation: `gammaFactor = pow(0.5, 1/gamma - 1)` multiplied by brightness for effective midtone shift.

- `web/src/components/viewer/BandSelector.tsx` -- Tab buttons for multi-band observations. Props: `spectralFilters: string[] | null`, `currentBand: number`, `onBandChange: (index: number) => void`. Returns `null` when `!spectralFilters || spectralFilters.length <= 1`. Active tab styled `bg-cyan-700/80 text-cyan-100`, inactive `text-zinc-400 hover:bg-zinc-700`. Documented limitation: Phase 2 overwrites tiles per FITS file, so band switching currently reloads same tiles.

- `web/src/components/viewer/CoordinateGrid.tsx` -- SVG overlay for RA/Dec grid lines. Props: `viewer: OpenSeadragon.Viewer | null`, `wcsParams: WcsParams`, `visible: boolean`. Key functions:
  - `raDecToPixel(raDeg, decDeg)` -- inverse WCS TAN deprojection: spherical rotation (sin/cos deltaRa, sinDec0/cosDec0) -> gnomonic projection (xi/eta via denom check for behind-tangent-plane) -> CD matrix inversion (2x2 determinant) -> CRPIX offset. Returns image pixel coords.
  - `imageToViewportPixel(fitsX, fitsY)` -- FITS Y-flip (`naxis2 - fitsY`) -> OSD `imageToViewportCoordinates` -> `viewportToViewerElementCoordinates`. Returns screen pixel coords.
  - `computeGrid()` -- gets viewport corner RA/Dec, computes FOV extent, selects grid spacing from `NICE_GRID_ARCSEC` (1" to 10deg) targeting `TARGET_GRID_LINES=5`, samples 20 points per line, builds SVG path data (`M/L` commands) and labels.
  - Grid re-rendered on OSD `animation`, `animation-finish`, `open`, `resize` events via RAF-throttled handler.
  - Label formatting: `formatRaLabel(raDeg, spacingArcsec)` (HH:MM:SS adaptive), `formatDecLabel(decDeg, spacingArcsec)` (DD:MM:SS adaptive).

- `web/src/app/viewer/[uuid]/ViewerLoader.tsx` -- SSR-safe dynamic import wrapper. Uses `dynamic(() => import("./ViewerClient"), { ssr: false })` to prevent OpenSeadragon from accessing window/document during Next.js server rendering. Props pass-through: `observationUuid`, `wcsParams`, `tileMetadata`, `tileBaseUrl`, `observationDetail`.

- `web/src/components/viewer/ViewerToolbar.tsx` -- Extended from 5 to 8 buttons. Added props: `onToggleInfo`, `onToggleAdjustments`, `onToggleGrid`, `isInfoOpen`, `isAdjustmentsOpen`, `isGridVisible`. Active state uses `activeButtonClass` (cyan background) vs `buttonClass` (zinc). Separator `<div>` between navigation and panel toggle buttons.

- `web/src/components/viewer/SkyViewer.tsx` -- Modified: tile source `Url` now uses `tileBaseUrl` prop directly (previously appended 'tiles/'). Added `drawer: "canvas"` config to force canvas2d renderer instead of OSD 6.x default WebGL (avoids "Error creating texture" in some environments). Added `onViewerReady` callback firing after viewer creation. Added `defaultZoomLevel: 0` with 0.8x initial zoom on `open` event for breathing room.

- `web/src/app/viewer/[uuid]/ViewerClient.tsx` -- Integrated all new components. New state: `isInfoOpen`, `isAdjustmentsOpen`, `isGridVisible`, `currentBand` (all `useState(false)` / `useState(0)`). New callbacks: `handleAdjustmentChange(adjustments)` applies CSS filter via `viewer.canvas.style.filter = buildCssFilter(adjustments)`, `handleBandChange(index)` sets `currentBand` (no-op tile reload, documented). Renders: CoordinateGrid (z-10), ViewerToolbar (z-10, 8 buttons), ImageAdjustments (z-20, left side), BandSelector (z-20, top-right), ObservationInfo (z-20, right sidebar), ScaleBar, coordinate overlay bar.

- `web/src/app/viewer/[uuid]/page.tsx` -- Updated: imports `ViewerLoader` instead of direct `ViewerClient`. Passes `observationDetail` prop to ViewerLoader for info sidebar consumption. Removed direct 'use client' component import in favor of SSR-safe dynamic import.

## Architecture & Data Flow

**Call graph (Plan 03 additions in bold):**
```
ViewerPage (server component, /viewer/[uuid]/page.tsx)
  |
  +-- fetchObservation(uuid) --> ObservationDetail
  +-- fetchWcsParams(uuid)   --> WcsParams
  +-- getTileUrl(uuid)       --> string
  |
  +-- <ViewerLoader> (SSR-safe dynamic import wrapper)
        |
        +-- <ViewerClient> (client boundary, owns all interactive state)
              |
              +-- <SkyViewer ref={skyViewerRef}>
              |     OSD viewer with canvas2d drawer, inline DZI tile source
              |     MouseTracker: moveHandler -> RAF -> pixelToRaDec -> liveCoordRef.textContent
              |     clickHandler -> pixelToRaDec -> setPinnedCoordinate + clipboard
              |
              +-- <CoordinateGrid viewer={viewer} wcsParams={wcsParams} visible={isGridVisible}>
              |     raDecToPixel(): RA/Dec -> spherical rotation -> TAN projection -> CD^-1 -> pixel
              |     imageToViewportPixel(): FITS pixel -> Y-flip -> OSD viewport -> screen coords
              |     computeGrid(): viewport corners -> RA/Dec -> pick spacing -> sample lines -> SVG paths
              |     Listeners: animation, animation-finish, open, resize (RAF-throttled)
              |
              +-- <ViewerToolbar 8 buttons: zoom+/-, home, fullscreen, navigator, info, adjustments, grid>
              |     skyViewerRef.current.zoomIn/zoomOut/goHome/toggleFullscreen/toggleNavigator
              |     setIsInfoOpen/setIsAdjustmentsOpen/setIsGridVisible toggles
              |
              +-- <ImageAdjustments onAdjustmentChange={handleAdjustmentChange}>
              |     adjustments state -> onAdjustmentChange -> buildCssFilter()
              |     -> viewer.canvas.style.filter = "brightness(X) contrast(Y) [invert(1)]"
              |
              +-- <BandSelector spectralFilters={...} currentBand={0} onBandChange={...}>
              |     Renders tabs if spectralFilters.length > 1
              |     onBandChange -> setCurrentBand (no tile URL change in Phase 3)
              |
              +-- <ObservationInfo observation={observationDetail} isOpen={isInfoOpen}>
              |     InfoSection/InfoRow sub-components
              |     Shows: obs ID, telescope, instrument, filters, exposure, RA/Dec, tile metadata
              |
              +-- <ScaleBar viewer={viewer} wcsParams={wcsParams}>
              +-- Coordinate overlay bar (bottom, inline JSX)
```

**CSS filter data flow:**
```
ImageAdjustments (local state: brightness=0.95, contrast=1.75, gamma=0.35, invert=false)
  --> onAdjustmentChange(adjustments)
  --> ViewerClient.handleAdjustmentChange(adjustments)
  --> buildCssFilter(adjustments)
      --> gammaFactor = pow(0.5, 1/0.35 - 1) = pow(0.5, 1.857) = 0.276
      --> effectiveBrightness = 0.95 * 0.276 = 0.262
      --> "brightness(0.262) contrast(1.750)"
  --> viewer.canvas.style.filter = "brightness(0.262) contrast(1.750)"
```

**Coordinate grid data flow:**
```
OSD animation event
  --> RAF handler -> computeGrid()
  --> viewport corners -> viewerElementToViewportCoordinates -> viewportToImageCoordinates
  --> FITS Y-flip -> pixelToRaDec() -> corner RA/Dec values
  --> FOV arcsec = max(decFov, raFov) * 3600
  --> pick gridSpacingArcsec from NICE_GRID_ARCSEC where fov/spacing >= 5
  --> for each constant-Dec line: sample 20 RA values -> raDecToPixel -> imageToViewportPixel -> SVG path
  --> for each constant-RA line: sample 20 Dec values -> raDecToPixel -> imageToViewportPixel -> SVG path
  --> setGridLines(lines) -> SVG render
```

## Decisions Made

- **CSS filter for image adjustments:** Applied directly to `viewer.canvas.style.filter` rather than WebGL shaders or per-pixel canvas manipulation. Simple, zero-dependency approach that works with the canvas2d drawer.
- **Gamma approximation:** True gamma requires per-pixel `pow(pixel, 1/gamma)`. CSS filter lacks a gamma function, so we approximate via `gammaFactor = pow(0.5, 1/gamma - 1)` which shifts midtones similarly. Documented as an approximation; a WebGL approach could be added in a future phase.
- **Canvas2d drawer:** OSD 6.x defaults to WebGL which occasionally fails with "Error creating texture" and produces blank screens. Forcing `drawer: "canvas"` avoids this at the cost of slightly lower rendering performance (imperceptible for typical astronomical image sizes).
- **ViewerLoader SSR wrapper:** OpenSeadragon accesses `window` and `document` at import time. Using `next/dynamic({ ssr: false })` in a separate ViewerLoader component prevents SSR failures without adding `typeof window !== 'undefined'` checks throughout the viewer code.
- **Band selector as UI-only for Phase 3:** The band selector tabs are fully functional UI but switching bands currently reloads the same tiles due to Phase 2's single-prefix tile storage. This was an intentional plan decision -- the UI is ready for when tile isolation is added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created ViewerLoader SSR wrapper for OpenSeadragon**
- **Found during:** Task 1 (viewer integration)
- **Issue:** OpenSeadragon accesses `window` and `document` at import time, causing Next.js server-side rendering to fail. The original page.tsx imported ViewerClient directly, which transitively imported OpenSeadragon.
- **Fix:** Created `ViewerLoader.tsx` using `next/dynamic(() => import("./ViewerClient"), { ssr: false })` as a thin SSR-safe wrapper. Updated `page.tsx` to import ViewerLoader instead of ViewerClient.
- **Files modified:** `web/src/app/viewer/[uuid]/ViewerLoader.tsx` (new), `web/src/app/viewer/[uuid]/page.tsx` (updated import)
- **Verification:** `npm run build` succeeds without SSR errors
- **Committed in:** `9121f61` (fix commit)

**2. [Rule 1 - Bug] Fixed OSD 6.x WebGL drawer causing blank screen**
- **Found during:** Task 1 (viewer testing)
- **Issue:** OSD 6.x defaults to WebGL drawer which fails in some environments with "Error creating texture", causing a blank viewer until user interaction forces a re-draw.
- **Fix:** Added `drawer: "canvas"` config to SkyViewer.tsx to force canvas2d rendering.
- **Files modified:** `web/src/components/viewer/SkyViewer.tsx`
- **Verification:** Viewer loads and renders tiles immediately without interaction
- **Committed in:** `9121f61` (fix commit)

**3. [Rule 1 - Bug] Fixed tile URL construction**
- **Found during:** Task 1 (tile loading)
- **Issue:** SkyViewer was appending 'tiles/' to `tileBaseUrl` but `tileBaseUrl` already included the correct path from `getTileUrl()`. Double-appending caused 404 tile requests.
- **Fix:** Changed SkyViewer to use `tileBaseUrl` directly as the DZI `Url` value without appending 'tiles/'.
- **Files modified:** `web/src/components/viewer/SkyViewer.tsx`
- **Verification:** Tiles load successfully from correct URLs
- **Committed in:** `9121f61` (fix commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correct viewer operation. No scope creep.

## Issues Encountered

None beyond the auto-fixed issues documented above.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness
- Phase 3 (Sky Viewer) is complete: deep-zoom viewer with coordinate overlay, image adjustments, observation metadata, and coordinate grid
- Phase 4 (Segmentation) can proceed: SAM-based object detection on the tiled imagery stored in MinIO
- Phase 6 (Search & Browse) will extend the viewer with object overlays, search results, and the band selector will become functional when tile isolation is added
- All viewer components follow the established patterns: forwardRef/imperative handle for SkyViewer, RAF-throttled event handlers, CSS filter composition, SVG overlay positioning

## Self-Check: PASSED

- [x] web/src/components/viewer/ObservationInfo.tsx exists
- [x] web/src/components/viewer/ImageAdjustments.tsx exists
- [x] web/src/components/viewer/BandSelector.tsx exists
- [x] web/src/components/viewer/CoordinateGrid.tsx exists
- [x] web/src/app/viewer/[uuid]/ViewerLoader.tsx exists
- [x] 03-03-SUMMARY.md exists
- [x] Commit 85d38fb found (Task 1 feat)
- [x] Commit 9121f61 found (Task 1 fix)
- [x] Commit 3f30ba6 found (Deep Sky preset)

---
*Phase: 03-sky-viewer*
*Completed: 2026-02-22*
