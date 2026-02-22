---
phase: 03-sky-viewer
plan: 02
subsystem: ui
tags: [openseadragon, wcs, coordinate-conversion, next.js, react, tailwind, deep-zoom]

# Dependency graph
requires:
  - phase: 03-sky-viewer
    plan: 01
    provides: "Tile proxy endpoint, WCS extraction endpoint, observation detail endpoint, TypeScript interfaces, API client functions"
  - phase: 02-data-ingestion-tiling
    provides: "DZI tiles in MinIO tiles bucket, FITS files in fits-raw bucket"
provides:
  - "OpenSeadragon deep-zoom viewer at /viewer/[uuid] with DZI tile loading from FastAPI proxy"
  - "Client-side WCS TAN gnomonic deprojection (pixelToRaDec) for real-time RA/Dec on hover"
  - "Coordinate formatting (HMS/DMS and decimal degrees) with toggle and clipboard copy"
  - "Viewer toolbar with zoom in/out, home, fullscreen, navigator toggle"
  - "Angular scale bar computing pixel scale from CD matrix, updating on zoom"
  - "Dark theme forced via html className='dark', dark-only CSS variables"
  - "API proxy rewrite in next.config.ts for dev-mode /api/* forwarding to FastAPI"
affects: [03-03-PLAN]

# Tech tracking
tech-stack:
  added: [openseadragon, "@types/openseadragon"]
  patterns: [imperative-dom-update-for-high-fps-coordinate-display, forwardRef-useImperativeHandle-for-viewer-controls, raf-throttled-mouse-tracking, dzi-inline-tile-source-config]

key-files:
  created:
    - web/src/lib/wcs.ts
    - web/src/lib/coordinates.ts
    - web/src/components/viewer/SkyViewer.tsx
    - web/src/components/viewer/CoordinateOverlay.tsx
    - web/src/components/viewer/ViewerToolbar.tsx
    - web/src/components/viewer/ScaleBar.tsx
    - web/src/app/viewer/[uuid]/page.tsx
    - web/src/app/viewer/[uuid]/ViewerClient.tsx
  modified:
    - web/package.json
    - web/src/app/layout.tsx
    - web/src/app/globals.css
    - web/src/app/page.tsx
    - web/next.config.ts

key-decisions:
  - "Imperative DOM mutation for coordinate display at 30fps instead of React state to avoid re-render overhead"
  - "OSD MouseTrackerEvent type extended locally (OsdMouseEvent) because @types/openseadragon lacks position/quick fields"
  - "ViewerClient.tsx as separate client boundary -- server component page.tsx fetches data, ViewerClient owns all interactive state"
  - "Coordinate overlay inline in ViewerClient rather than CoordinateOverlay component -- simpler wiring of imperative refs"
  - "Scale bar picks 'nice' angular values from predefined list for clean labels"

patterns-established:
  - "forwardRef + useImperativeHandle pattern: SkyViewer exposes zoomIn/zoomOut/goHome/toggleFullscreen/toggleNavigator via ref handle, called from ViewerToolbar callbacks"
  - "RAF-throttled mouse tracking: moveHandler gates coordinate updates behind requestAnimationFrame flag to cap at display refresh rate"
  - "Inline DZI tile source: OpenSeadragon configured with inline Image XML spec (Url, Format, Overlap, TileSize, Size) instead of .dzi file"
  - "Server/client split: page.tsx (server) fetches data via API client, passes to ViewerClient.tsx (client) which owns all DOM interaction"

requirements-completed: [BROWSE-01, BROWSE-02]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 3 Plan 02: Core Sky Viewer Summary

**OpenSeadragon deep-zoom viewer with real-time WCS coordinate overlay (TAN deprojection), toolbar controls, angular scale bar, and dark theme at /viewer/[uuid]**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T22:44:37Z
- **Completed:** 2026-02-22T22:49:52Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- OpenSeadragon viewer rendering DZI tiles from MinIO via FastAPI tile proxy with scroll-to-zoom, drag-to-pan, and blur-up loading (immediateRender)
- Real-time RA/Dec coordinate display on mouse hover via client-side TAN gnomonic deprojection (Calabretta & Greisen 2002), throttled to ~30fps with requestAnimationFrame
- Click-to-pin coordinates with clipboard copy and toast notification, HMS/DMS and decimal degree format toggle
- Vertical toolbar with zoom in (+1.5x), zoom out (0.67x), home (fit view), fullscreen toggle, and navigator mini-map toggle
- Angular scale bar computing pixel scale from WCS CD matrix, picking "nice" values (1/2/5/10/20/30 arcsec, 1/2/5/10/20/30 arcmin, etc.), updating on zoom events
- Dark theme forced globally via `className="dark"` on `<html>`, dark-only CSS variables (`--background: #0a0a0a`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install OpenSeadragon, create WCS + coordinate libraries, configure dark theme layout** - `abf672c` (feat)
2. **Task 2: Build OpenSeadragon viewer component, coordinate overlay, toolbar, and viewer page** - `eac9f9e` (feat)

## Files Created/Modified

- `web/src/lib/wcs.ts` -- Exports `pixelToRaDec(pixelX, pixelY, wcs): { ra, dec }`. Implements TAN gnomonic deprojection: pixel offset from CRPIX -> CD matrix transform to intermediate world coords (xi, eta in degrees) -> atan-based deprojection -> spherical rotation to celestial RA/Dec. Handles rTheta===0 edge case. Normalizes RA to [0,360). ~40 lines of pure math, imports only `WcsParams` type.

- `web/src/lib/coordinates.ts` -- Exports `decimalDegreesToHms(degrees)` (RA degrees -> "05h 35m 17.3s"), `decimalDegreesToDms(degrees)` (Dec degrees -> "+05d 23m 28.1s"), `formatCoordinates(ra, dec, mode)` (dispatches to HMS/DMS or decimal "83.822d, -5.391d"). No dependencies.

- `web/src/components/viewer/SkyViewer.tsx` -- OpenSeadragon wrapper. `forwardRef<SkyViewerHandle>` exposing `zoomIn()`, `zoomOut()`, `goHome()`, `toggleFullscreen()`, `toggleNavigator()` via `useImperativeHandle`. Two `useEffect` hooks: (1) create OSD viewer with inline DZI tile source config (`Url: ${tileBaseUrl}tiles/`, Format=jpg, TileSize=256, Overlap=1), (2) `OpenSeadragon.MouseTracker` with RAF-throttled `moveHandler` converting screen -> viewport -> image -> FITS (Y-flip) -> RA/Dec via `pixelToRaDec`, and `clickHandler` for pinning. Local `OsdMouseEvent` interface extends incomplete `@types/openseadragon` defs.

- `web/src/components/viewer/CoordinateOverlay.tsx` -- Standalone coordinate HUD component (not used directly; functionality inlined in ViewerClient for simpler ref wiring). Exports `CoordinateOverlayHandle` type and `updateLiveCoordinates()` helper.

- `web/src/components/viewer/ViewerToolbar.tsx` -- Vertical button strip, 5 buttons with inline SVG icons: zoom in (+), zoom out (-), home, fullscreen (expand corners), navigator (mini-map rectangles). Styled with `bg-zinc-800/80` semi-transparent dark backgrounds.

- `web/src/components/viewer/ScaleBar.tsx` -- Angular scale bar. Computes `pixelScaleArcsec = sqrt(cd1_1^2 + cd2_1^2) * 3600`. Listens to OSD `zoom`/`open`/`resize` events. Picks largest "nice" value from `NICE_ARCSEC_VALUES` (0.1 mas to 10 deg) that fits within 200px bar. Shows angular label + pixel count.

- `web/src/app/viewer/[uuid]/page.tsx` -- Server component. Fetches `observation` and `wcsParams` via `Promise.all([fetchObservation(uuid), fetchWcsParams(uuid)])`. Handles tile-not-ready (shows pipeline status) and observation-not-found (shows error). Passes all data to ViewerClient.

- `web/src/app/viewer/[uuid]/ViewerClient.tsx` -- Client boundary composing all viewer components. Owns `displayMode` state ("hms"|"decimal"), `pinnedCoordinate` state, `showCopyToast` state, and `viewer` (OSD instance) state. `handleCoordinateChange` imperatively sets `liveCoordRef.current.textContent` for 30fps updates. `handleCoordinateClick` pins coord + copies to clipboard. Renders: SkyViewer (full viewport) + ViewerToolbar (top-left) + ScaleBar (bottom-right) + coordinate overlay bar (bottom, absolute positioned).

- `web/src/app/layout.tsx` -- Added `className="dark"` to `<html>`, updated metadata title/description.
- `web/src/app/globals.css` -- Removed light theme defaults and prefers-color-scheme media query, set dark-only variables.
- `web/src/app/page.tsx` -- Replaced Next.js boilerplate with minimal project landing page.
- `web/next.config.ts` -- Added `rewrites()` proxying `/api/:path*` to `http://localhost:8000/api/:path*` for dev.
- `web/package.json` -- Added `openseadragon` (^6.0.0), `@types/openseadragon` (^5.0.2).

## Architecture & Data Flow

**Call graph:**
```
ViewerPage (server component, /viewer/[uuid]/page.tsx)
  |
  +-- fetchObservation(uuid) --> GET /api/tiles/{uuid} --> ObservationDetail
  +-- fetchWcsParams(uuid)   --> GET /api/tiles/{uuid}/wcs --> WcsParams
  +-- getTileUrl(uuid)       --> string (tile base URL)
  |
  +-- <ViewerClient> (client component)
        |
        +-- <SkyViewer ref={skyViewerRef}>
        |     |
        |     +-- useEffect[init]: OpenSeadragon({ tileSources: { Image: { Url: tileBaseUrl + 'tiles/' } } })
        |     |     Tiles loaded lazily: /api/tiles/{uuid}/tiles/{level}/{col}_{row}.jpg
        |     |     --> next.config.ts rewrite --> http://localhost:8000/api/tiles/...
        |     |     --> FastAPI StreamingResponse from MinIO
        |     |
        |     +-- useEffect[tracking]: new MouseTracker({ moveHandler, clickHandler })
        |           moveHandler:
        |             event.position --> viewport.pointFromPixel() --> viewport.viewportToImageCoordinates()
        |             --> FITS Y-flip (naxis2 - imageY) --> pixelToRaDec(fitsX, fitsY, wcsParams)
        |             --> liveCoordRef.current.textContent = formatCoordinates(ra, dec, mode)
        |           clickHandler:
        |             same coord chain --> setPinnedCoordinate({ ra, dec })
        |             --> navigator.clipboard.writeText()
        |
        +-- <ViewerToolbar onZoomIn/onZoomOut/onGoHome/onToggleFullscreen/onToggleNavigator>
        |     Calls skyViewerRef.current.zoomIn() etc. (imperative handle)
        |
        +-- <ScaleBar viewer={osdViewer} wcsParams={wcsParams}>
        |     pixelScaleArcsec = sqrt(cd1_1^2 + cd2_1^2) * 3600
        |     On zoom event: compute arcsecPerScreenPixel, pick nice value, set bar width
        |
        +-- Coordinate overlay bar (inline JSX)
              liveCoordRef (imperative DOM), displayMode toggle, pinnedCoordinate, copyToast
```

**Data flow for coordinate display:**
```
Mouse position (screen px)
  --> OSD viewport.pointFromPixel() (viewport coords)
  --> OSD viewport.viewportToImageCoordinates() (image px)
  --> FITS Y-flip: fitsY = naxis2 - imageY
  --> pixelToRaDec(fitsX, fitsY, wcsParams)
      --> CD matrix: xi = cd1_1*dx + cd1_2*dy, eta = cd2_1*dx + cd2_2*dy
      --> TAN deprojection: c = atan(rTheta), then spherical rotation
  --> { ra: degrees, dec: degrees }
  --> formatCoordinates(ra, dec, "hms")
  --> "05h 35m 17.3s, -05d 23m 28.1s" (DOM textContent update)
```

## Decisions Made

- **Imperative DOM for coordinate display:** At ~30fps mouse movement, React state updates would cause excessive re-renders. Instead, the `handleCoordinateChange` callback directly sets `liveCoordRef.current.textContent` via DOM mutation. Only pinned coordinates and display mode use React state.
- **Extended OSD types locally:** The `@types/openseadragon` package's `MouseTrackerEvent` type omits `position` and `quick` fields that exist at runtime. Rather than patching the package or using module augmentation, a local `OsdMouseEvent` interface extends `MouseTrackerEvent` with these fields, and event handlers cast via `as unknown as OsdMouseEvent`.
- **ViewerClient as separate client boundary:** The page.tsx server component handles data fetching (fetchObservation, fetchWcsParams), and ViewerClient.tsx is the single `"use client"` entry point that owns all interactive state and composes all viewer sub-components. This keeps the server/client split clean.
- **Coordinate overlay inlined in ViewerClient:** Rather than wiring imperative refs through CoordinateOverlay.tsx, the coordinate display JSX is inlined directly in ViewerClient.tsx. The CoordinateOverlay component still exists but isn't used in this composition -- the inline approach is simpler when the parent already manages the liveCoordRef.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed OpenSeadragon TypeScript type incompatibilities**
- **Found during:** Task 2 (SkyViewer component)
- **Issue:** `@types/openseadragon` v5 lacks `position` and `quick` on `MouseTrackerEvent`, types `navigatorPosition` as string union (not `ControlAnchor` enum), and lacks `background` option
- **Fix:** Created local `OsdMouseEvent` interface extending `MouseTrackerEvent` with `position: Point` and `quick?: boolean`. Removed invalid `as ControlAnchor` cast (string literal works). Removed `background` option (container `bg-black` CSS sufficient).
- **Files modified:** `web/src/components/viewer/SkyViewer.tsx`
- **Verification:** `npx tsc --noEmit` passes cleanly
- **Committed in:** `eac9f9e` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Created ViewerClient.tsx client boundary**
- **Found during:** Task 2 (viewer page)
- **Issue:** Plan specified page.tsx as server component passing props to SkyViewer, but SkyViewer needs client-side state management for coordinate display, pinned coordinates, display mode toggle, and clipboard API. A client wrapper component was needed to compose all interactive pieces.
- **Fix:** Created `web/src/app/viewer/[uuid]/ViewerClient.tsx` as the single `"use client"` entry point that owns all interactive state and composes SkyViewer, ViewerToolbar, ScaleBar, and the inline coordinate overlay.
- **Files modified:** `web/src/app/viewer/[uuid]/ViewerClient.tsx` (new file)
- **Verification:** `npm run build` succeeds, page.tsx remains server component, ViewerClient handles all client-side interaction
- **Committed in:** `eac9f9e` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both auto-fixes necessary for TypeScript correctness and Next.js server/client architecture. No scope creep.

## Issues Encountered

None beyond the type definition gaps documented above.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness
- Sky viewer is fully functional pending a running FastAPI backend with tile data in MinIO
- Plan 03 (info panel, search, and polish) can build on top of the viewer page and components
- All components follow the established forwardRef/imperative handle pattern for toolbar integration
- CoordinateOverlay.tsx exists as a standalone component but is currently unused (overlay inlined in ViewerClient) -- Plan 03 can refactor if needed

---
*Phase: 03-sky-viewer*
*Completed: 2026-02-22*
