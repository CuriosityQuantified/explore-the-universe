# Phase 3: Sky Viewer - Research

**Researched:** 2026-02-22
**Domain:** Deep-zoom tile viewer with WCS coordinate overlay for astronomical imagery
**Confidence:** HIGH

## Summary

Phase 3 delivers a browser-based deep-zoom viewer for JWST imagery produced by Phase 2's DZI tile pipeline. The core challenge is two-fold: (1) displaying DZI tile pyramids from MinIO efficiently with OpenSeadragon, and (2) converting pixel coordinates to sky coordinates (RA/Dec) in real-time as users navigate.

OpenSeadragon is the clear choice for the DZI viewer -- it is the standard library for deep-zoom imagery, natively supports the DZI format produced by Phase 2's pyvips `dzsave()`, and has an established ecosystem of plugins (navigator, scalebar, overlays). The main technical challenge is the WCS coordinate pipeline: Phase 2 stores pointing RA/Dec and image dimensions but does NOT persist the full WCS header parameters (CRPIX, CRVAL, CD matrix) needed for pixel-to-sky conversion. Phase 3 must extract and serve these parameters.

For coordinate conversion, the recommended approach is a backend API endpoint that extracts WCS parameters from the stored FITS files and serves them as JSON. The frontend then implements the TAN gnomonic deprojection in ~40 lines of TypeScript, avoiding heavy dependencies like wcsjs (unmaintained Emscripten port) or server round-trips per mouse move.

**Primary recommendation:** Use OpenSeadragon 5.x with a custom DZI tile source pointing at MinIO, implement client-side TAN projection math from WCS parameters served by a new FastAPI endpoint, and build the viewer as a React component with `useRef`/`useEffect` for OpenSeadragon lifecycle management.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Default format: HMS/DMS (05h 35m 17.3s, -05d 23m 28s) with toggle to decimal degrees
- Hover shows live coordinates following the cursor in real-time
- Click pins a persistent coordinate readout that can be copied
- Click-to-copy: clicking a point copies coordinates to clipboard with a brief toast confirmation
- Coordinate grid overlay: available but off by default, user can toggle it on
- Minimap/overview: available but toggleable (off by default to maximize image area)
- Zoom buttons: visible +/- controls on the viewer
- Scale bar: shows angular size (arcmin/arcsec) as primary, pixel count as secondary
- Home button: resets view to fit the full image in one click
- Standard scroll-wheel zoom and drag-to-pan expected
- Dark theme (no light mode toggle for this phase) -- standard for astronomy, makes faint details pop
- Embedded layout with fullscreen toggle: viewer fills most of the page with surrounding UI, button to go fullscreen
- Observation info panel: sidebar showing observation ID, telescope, instrument, filter, exposure time, date
- Tile loading: blur-up strategy (show lower-resolution tiles immediately, sharpen as high-res tiles load -- Google Maps style)
- Client-side adjustments via CSS/canvas filters (no server re-rendering): brightness, contrast, gamma, and invert toggle
- Collapsible panel: hidden by default, expand via a toolbar button to keep viewer clean
- Reset button: single click restores all adjustments to default rendering
- Band/filter selector: dropdown or tabs to switch between available FITS files for the same observation
- Each band loads its own tile pyramid from MinIO

### Claude's Discretion
- Deep-zoom library choice (OpenSeadragon, Leaflet, or equivalent)
- Coordinate grid rendering approach (canvas overlay, SVG, etc.)
- Exact sidebar layout and responsive breakpoints
- Keyboard shortcut mappings
- Touch gesture support details
- Error states for missing/failed tiles

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BROWSE-01 | User can pan and zoom across ingested imagery like a map, from full field down to individual objects | OpenSeadragon natively provides smooth pan/zoom for DZI pyramids. Phase 2 produces DZI tiles (256px, 1px overlap, JPEG Q=85) stored in MinIO. Custom tile source routes requests to MinIO via FastAPI proxy or direct MinIO URLs. Blur-up is OpenSeadragon's default behavior (lower-level tiles shown while higher-level tiles load). |
| BROWSE-02 | User sees sky coordinates (RA/Dec) on hover or click within the viewer | OpenSeadragon's `MouseTracker` provides pixel coordinates on `moveHandler`. Combined with WCS parameters (CRPIX, CRVAL, CD matrix) served by a new API endpoint, client-side TAN gnomonic deprojection converts pixels to RA/Dec in real-time. HMS/DMS formatting is ~20 lines of conversion code. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| OpenSeadragon | 5.0.1 | Deep-zoom tile viewer | Industry standard for DZI/IIIF imagery. 5.6k GitHub stars. Native DZI support matches Phase 2's pyvips `dzsave()` output exactly. |
| @types/openseadragon | 3.0.10+ | TypeScript definitions | DefinitelyTyped types. Note: v5 types may lag -- declare missing types locally if needed. |
| React 19 + Next.js 16 | (already installed) | App framework | Existing project stack (web/package.json). OpenSeadragon is imperative -- wrap with useRef/useEffect. |
| Tailwind CSS 4 | (already installed) | Styling | Existing project stack. Dark theme via Tailwind classes. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openseadragon-scalebar | 1.1.3 | Scale bar overlay | Angular size display (arcmin/arcsec). Has built-in ASTRONOMY renderer. |
| astropy (server-side) | (already installed) | WCS extraction from FITS | Backend API endpoint extracts CRPIX/CRVAL/CD matrix from FITS headers. Already used in validate_wcs task. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenSeadragon | Leaflet + leaflet-deepzoom | Leaflet is map-first; DZI support is via plugin, not native. OpenSeadragon is image-first with native DZI. Clear winner for astronomical imagery. |
| OpenSeadragon | Aladin Lite | Full astronomical viewer with HiPS survey support, but opinionated about data formats (HiPS, not DZI). Would require converting Phase 2 output. Too heavyweight for our use case. |
| Client-side TAN math | wcsjs (astrojs/wcsjs) | Emscripten port of WCSLIB. Unmaintained (no releases, 157 commits, last activity years ago). Huge bundle for what amounts to ~40 lines of TAN projection math. Not worth the dependency. |
| Client-side TAN math | Server-side conversion API per pixel | Round-trip latency makes real-time hover coordinate display impossible. Must be client-side. |
| FastAPI tile proxy | Direct MinIO presigned URLs | Presigned URLs are possible but add complexity (URL expiration, CORS config on MinIO, signature version issues). A FastAPI proxy endpoint is simpler, avoids CORS entirely, and adds zero perceptible latency for 256px JPEG tiles. |

**Installation:**
```bash
cd web && npm install openseadragon @types/openseadragon
```

The scalebar plugin has no npm package -- include via `openseadragon-scalebar.js` downloaded to `web/public/` or vendor it.

## Architecture Patterns

### Recommended Project Structure
```
web/src/
├── app/
│   ├── layout.tsx                    # Root layout (dark theme)
│   ├── page.tsx                      # Landing / observation list
│   └── viewer/[uuid]/
│       └── page.tsx                  # Viewer page (server component, fetches observation)
├── components/
│   ├── viewer/
│   │   ├── SkyViewer.tsx             # Main OpenSeadragon wrapper (client component)
│   │   ├── CoordinateOverlay.tsx     # RA/Dec readout HUD
│   │   ├── ViewerToolbar.tsx         # Zoom buttons, home, fullscreen, settings
│   │   ├── ImageAdjustments.tsx      # Brightness/contrast/gamma/invert panel
│   │   ├── BandSelector.tsx          # Filter/band dropdown
│   │   ├── ScaleBar.tsx              # Angular scale bar
│   │   └── ObservationInfo.tsx       # Sidebar with observation metadata
│   └── ui/
│       └── Toast.tsx                 # Copy-to-clipboard confirmation
├── lib/
│   ├── wcs.ts                        # TAN gnomonic projection math
│   ├── coordinates.ts                # HMS/DMS formatting, decimal toggle
│   └── api.ts                        # API client (fetch observation, WCS params)
└── types/
    └── observation.ts                # TypeScript interfaces
```

### Pattern 1: OpenSeadragon React Wrapper
**What:** Imperative library managed via React refs and effects
**When to use:** Always -- OpenSeadragon manages its own DOM; React should not interfere
**Example:**
```typescript
// Source: OpenSeadragon docs + community patterns
'use client';
import { useRef, useEffect, useCallback } from 'react';
import OpenSeadragon from 'openseadragon';

interface SkyViewerProps {
  observationUuid: string;
  dziUrl: string;
  wcsParams: WcsParams;
}

export function SkyViewer({ observationUuid, dziUrl, wcsParams }: SkyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const viewer = OpenSeadragon({
      element: containerRef.current,
      tileSources: {
        Image: {
          xmlns: 'http://schemas.microsoft.com/deepzoom/2008',
          Url: `/api/tiles/${observationUuid}/`,
          Format: 'jpg',
          Overlap: '1',
          TileSize: '256',
          Size: { Width: String(wcsParams.naxis1), Height: String(wcsParams.naxis2) },
        },
      },
      showNavigator: false,       // user toggles on
      navigatorPosition: 'BOTTOM_LEFT',
      zoomInButton: 'zoom-in',
      zoomOutButton: 'zoom-out',
      homeButton: 'home-button',
      fullPageButton: 'fullscreen-button',
      gestureSettingsMouse: { scrollToZoom: true },
      visibilityRatio: 1.0,
      minZoomLevel: 0.5,
      defaultZoomLevel: 0,
      immediateRender: true,
      imageLoaderLimit: 4,
    });

    viewerRef.current = viewer;

    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, [observationUuid, dziUrl, wcsParams]);

  return <div ref={containerRef} className="h-full w-full bg-black" />;
}
```

### Pattern 2: Tile Serving via FastAPI Proxy
**What:** FastAPI endpoint proxies tile requests to MinIO, avoiding CORS
**When to use:** For all tile and DZI requests from the browser
**Example:**
```python
# Source: MinIO S3 + FastAPI patterns
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from shared.s3 import get_s3_client
from shared.config import settings

router = APIRouter(prefix="/api/tiles", tags=["tiles"])

@router.get("/{observation_uuid}/{level}/{col}_{row}.jpg")
def get_tile(observation_uuid: str, level: int, col: int, row: int):
    s3_key = f"{observation_uuid}/tiles/{level}/{col}_{row}.jpg"
    s3_client = get_s3_client()
    response = s3_client.get_object(
        Bucket=settings.s3_bucket_tiles, Key=s3_key
    )
    return StreamingResponse(
        response["Body"],
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
```

### Pattern 3: Client-side WCS Conversion (TAN Gnomonic Projection)
**What:** Convert image pixel coordinates to RA/Dec using WCS parameters
**When to use:** On every mouse move event over the viewer
**Example:**
```typescript
// Source: FITS WCS standard (Calabretta & Greisen 2002), TAN projection math
interface WcsParams {
  crpix1: number;  // reference pixel X
  crpix2: number;  // reference pixel Y
  crval1: number;  // reference RA (degrees)
  crval2: number;  // reference Dec (degrees)
  cd1_1: number;   // CD matrix element
  cd1_2: number;
  cd2_1: number;
  cd2_2: number;
  naxis1: number;  // image width
  naxis2: number;  // image height
}

function pixelToRaDec(
  pixelX: number, pixelY: number, wcs: WcsParams
): { ra: number; dec: number } {
  // Step 1: Pixel offset from reference pixel
  const dx = pixelX - wcs.crpix1;
  const dy = pixelY - wcs.crpix2;

  // Step 2: CD matrix -> intermediate world coordinates (degrees)
  const xi  = wcs.cd1_1 * dx + wcs.cd1_2 * dy;   // degrees
  const eta = wcs.cd2_1 * dx + wcs.cd2_2 * dy;    // degrees

  // Step 3: Convert to radians for trig
  const xiRad  = (xi  * Math.PI) / 180;
  const etaRad = (eta * Math.PI) / 180;
  const ra0Rad  = (wcs.crval1 * Math.PI) / 180;
  const dec0Rad = (wcs.crval2 * Math.PI) / 180;

  // Step 4: TAN (gnomonic) deprojection
  const rTheta = Math.sqrt(xiRad * xiRad + etaRad * etaRad);
  const c = Math.atan(rTheta);
  const sinC = Math.sin(c);
  const cosC = Math.cos(c);

  let dec: number;
  let ra: number;

  if (rTheta === 0) {
    dec = wcs.crval2;
    ra = wcs.crval1;
  } else {
    dec = Math.asin(
      cosC * Math.sin(dec0Rad) +
      (etaRad * sinC * Math.cos(dec0Rad)) / rTheta
    ) * (180 / Math.PI);

    ra = (ra0Rad + Math.atan2(
      xiRad * sinC,
      rTheta * Math.cos(dec0Rad) * cosC -
      etaRad * Math.sin(dec0Rad) * sinC
    )) * (180 / Math.PI);
  }

  // Normalize RA to [0, 360)
  ra = ((ra % 360) + 360) % 360;

  return { ra, dec };
}
```

### Pattern 4: HMS/DMS Coordinate Formatting
**What:** Convert decimal degrees to astronomical notation
**When to use:** Display coordinates in the overlay
**Example:**
```typescript
function decimalDegreesToHms(degrees: number): string {
  const hours = degrees / 15;
  const h = Math.floor(hours);
  const minutesDecimal = (hours - h) * 60;
  const m = Math.floor(minutesDecimal);
  const s = (minutesDecimal - m) * 60;
  return `${h.toString().padStart(2, '0')}h ${m.toString().padStart(2, '0')}m ${s.toFixed(1)}s`;
}

function decimalDegreesToDms(degrees: number): string {
  const sign = degrees < 0 ? '-' : '+';
  const absDeg = Math.abs(degrees);
  const d = Math.floor(absDeg);
  const minutesDecimal = (absDeg - d) * 60;
  const m = Math.floor(minutesDecimal);
  const s = (minutesDecimal - m) * 60;
  return `${sign}${d.toString().padStart(2, '0')}d ${m.toString().padStart(2, '0')}m ${s.toFixed(1)}s`;
}
```

### Anti-Patterns to Avoid
- **Re-rendering OpenSeadragon on React state changes:** OpenSeadragon manages its own canvas. Never unmount/remount the viewer on state changes. Use refs for viewer instance, communicate via imperative API.
- **Server round-trip for coordinate conversion:** With ~60fps mouse moves, any network latency makes coordinate display laggy. Must be client-side.
- **Loading entire FITS file in browser for WCS:** FITS files are 100MB-10GB+. Extract WCS parameters server-side, send ~200 bytes of JSON.
- **Using OpenSeadragon's built-in DZI AJAX loader with MinIO:** The default DZI loader expects the `.dzi` XML at a predictable URL. Since tiles are in MinIO behind a proxy, use inline DZI configuration with explicit `Url` pointing to the API proxy.
- **Proxying tiles without cache headers:** Tiles are immutable once generated. Always set `Cache-Control: public, max-age=31536000, immutable` so browsers cache aggressively.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deep zoom tile viewer | Custom canvas zoom/pan | OpenSeadragon | Tile loading priority, viewport management, touch gestures, accessibility -- extremely complex to get right |
| Minimap/navigator | Custom thumbnail + viewport indicator | OpenSeadragon Navigator (built-in) | `showNavigator: true` -- it tracks viewport position automatically |
| Scale bar | Custom pixel-measurement display | openseadragon-scalebar plugin | Handles zoom-dependent scale updates, unit conversion, positioning |
| Toast notifications | Custom timeout/animation | CSS animation + setTimeout | Simple enough that a library is overkill, but don't build a toast system |
| Fullscreen API | Custom fullscreen logic | `document.documentElement.requestFullscreen()` | Browser-native API, OpenSeadragon also has `setFullPage()` |

**Key insight:** OpenSeadragon has solved the hard problems (tile loading priority, viewport management, level-of-detail transitions, memory management). The custom work is exclusively the WCS-to-coordinate bridge and the UI panels around the viewer.

## Common Pitfalls

### Pitfall 1: OpenSeadragon Destroyed on React Re-render
**What goes wrong:** Viewer flashes or resets zoom when parent component re-renders
**Why it happens:** OpenSeadragon viewer is created in useEffect without stable dependency array, or the container div is re-created by React
**How to avoid:** Use `useRef` for both the container div AND the viewer instance. Stable dependency array on useEffect (only re-create viewer when observation UUID changes). Never pass viewer state through React state -- use imperative API.
**Warning signs:** Viewer resets to home position after UI interactions, white flashes

### Pitfall 2: WCS Parameters Not Available
**What goes wrong:** Phase 2 stores center RA/Dec in the Observation record but does NOT persist the full WCS header parameters (CRPIX1/2, CRVAL1/2, CD1_1/1_2/2_1/2_2, CTYPE1/2) needed for pixel-to-sky conversion
**Why it happens:** validate_wcs task creates `WCS(header)` for round-trip validation but only saves `center_ra_degrees`, `center_dec_degrees`, and `image_dimensions` to `step_output_metadata`
**How to avoid:** Add a new API endpoint that reads the FITS file from MinIO on demand and extracts WCS header keywords. Cache the result in `step_output_metadata` or a new JSON field. Alternatively, modify the validate_wcs task to persist the WCS keywords -- but this changes Phase 2 code. Recommend: new API endpoint (cleaner separation).
**Warning signs:** Coordinates always show the same value regardless of cursor position

### Pitfall 3: Coordinate Y-axis Inversion
**What goes wrong:** Coordinates are mirrored or offset vertically
**Why it happens:** FITS images use bottom-left origin (row 0 = bottom). OpenSeadragon and web images use top-left origin (row 0 = top). The DZI tile pyramid generated by pyvips inherits the pixel order of the normalized image, which was read top-to-bottom from FITS memmap (numpy array convention: row 0 = top of array = top of image in the tiled output).
**How to avoid:** When converting OpenSeadragon image pixel coordinates to FITS pixel coordinates for WCS conversion, verify whether Y needs flipping: `fitsY = naxis2 - osdImageY`. Test with a known observation where center coordinates are stored.
**Warning signs:** Dec values decrease when cursor moves up, or coordinates don't match the stored center pointing

### Pitfall 4: MinIO CORS for Direct Browser Access
**What goes wrong:** Tiles fail to load with CORS errors in browser console
**Why it happens:** MinIO does not set CORS headers by default. Browser blocks cross-origin tile fetches from `localhost:9000`.
**How to avoid:** Don't access MinIO directly from the browser. Use a FastAPI proxy endpoint that streams tiles from MinIO. This eliminates CORS entirely and adds negligible latency for small tile images.
**Warning signs:** Net::ERR_FAILED or Access-Control-Allow-Origin errors in browser console

### Pitfall 5: OpenSeadragon Dynamic Import in Next.js SSR
**What goes wrong:** `ReferenceError: window is not defined` during server-side rendering
**Why it happens:** OpenSeadragon accesses `window` and `document` at import time. Next.js 16 renders server components by default.
**How to avoid:** Mark the viewer component with `'use client'` directive. Use dynamic import with `{ ssr: false }` if needed: `const SkyViewer = dynamic(() => import('./SkyViewer'), { ssr: false })`.
**Warning signs:** Build errors or hydration mismatches mentioning `window` or `document`

### Pitfall 6: Mouse Move Throttling
**What goes wrong:** Coordinate overlay updates cause jank/lag
**Why it happens:** Mouse move fires at 60fps. If coordinate conversion + DOM update is expensive, frames are dropped.
**How to avoid:** The TAN projection math is cheap (~microseconds). But DOM updates should use `requestAnimationFrame` or throttle to ~30fps. Update coordinate text directly via ref, not via React state (which triggers re-render).
**Warning signs:** Coordinate display lags behind cursor, viewer feels sluggish

### Pitfall 7: Tile URL Pattern Mismatch
**What goes wrong:** Tiles 404 or show wrong tiles
**Why it happens:** Phase 2 uploads tiles with S3 key structure `{uuid}/tiles/{level}/{col}_{row}.jpg`. OpenSeadragon's default DZI URL pattern may differ from what's stored in MinIO.
**How to avoid:** Use inline DZI configuration with custom `Url` pointing to the FastAPI proxy. The proxy reconstructs the S3 key from the URL path. Verify the URL pattern matches by checking a known tile in MinIO.
**Warning signs:** 404 errors in network tab, blank tiles, tiles from wrong zoom level

## Code Examples

### WCS Parameter Extraction API Endpoint (Backend)
```python
# api/routers/tiles.py
from astropy.io import fits
from astropy.wcs import WCS
from fastapi import APIRouter, HTTPException
from shared.s3 import get_s3_client
from shared.config import settings
import tempfile, os

router = APIRouter(prefix="/api/tiles", tags=["tiles"])

@router.get("/{observation_uuid}/wcs")
def get_wcs_params(observation_uuid: str):
    """Extract WCS parameters from the primary FITS file for client-side projection."""
    # Find FITS file in MinIO
    s3_client = get_s3_client()
    response = s3_client.list_objects_v2(
        Bucket=settings.s3_bucket_fits_raw,
        Prefix=f"{observation_uuid}/",
        MaxKeys=1,
    )
    contents = response.get("Contents", [])
    if not contents:
        raise HTTPException(404, "No FITS files found for observation")

    fits_key = contents[0]["Key"]

    # Download to temp and extract WCS header keywords
    temp_fd, temp_path = tempfile.mkstemp(suffix=".fits")
    os.close(temp_fd)
    try:
        s3_client.download_file(settings.s3_bucket_fits_raw, fits_key, temp_path)
        with fits.open(temp_path, memmap=True, mode="denywrite") as hdul:
            # Find SCI extension (same logic as validate_wcs)
            header = hdul["SCI"].header if "SCI" in hdul else hdul[0].header
            wcs_obj = WCS(header)
            if wcs_obj.naxis > 2:
                wcs_obj = wcs_obj.celestial

            h = wcs_obj.to_header()
            return {
                "crpix1": float(h.get("CRPIX1", 0)),
                "crpix2": float(h.get("CRPIX2", 0)),
                "crval1": float(h.get("CRVAL1", 0)),
                "crval2": float(h.get("CRVAL2", 0)),
                "cd1_1": float(h.get("CD1_1", h.get("CDELT1", 0))),
                "cd1_2": float(h.get("CD1_2", 0)),
                "cd2_1": float(h.get("CD2_1", 0)),
                "cd2_2": float(h.get("CD2_2", h.get("CDELT2", 0))),
                "ctype1": str(h.get("CTYPE1", "")),
                "ctype2": str(h.get("CTYPE2", "")),
                "naxis1": int(header.get("NAXIS1", 0)),
                "naxis2": int(header.get("NAXIS2", 0)),
            }
    finally:
        os.unlink(temp_path)
```

### OpenSeadragon Mouse Tracking + WCS Conversion
```typescript
// Source: OpenSeadragon viewport-coordinates example
useEffect(() => {
  if (!viewerRef.current || !wcsParams) return;

  const tracker = new OpenSeadragon.MouseTracker({
    element: viewerRef.current.container,
    moveHandler: (event: OpenSeadragon.MouseTrackerEvent) => {
      if (!event.position || !viewerRef.current) return;
      const viewportPoint = viewerRef.current.viewport.pointFromPixel(event.position);
      const imagePoint = viewerRef.current.viewport.viewportToImageCoordinates(viewportPoint);

      // Convert from OSD image coords to FITS pixel coords (Y may need flip)
      const fitsX = imagePoint.x;
      const fitsY = wcsParams.naxis2 - imagePoint.y;

      const { ra, dec } = pixelToRaDec(fitsX, fitsY, wcsParams);

      // Update DOM directly via ref (avoid React re-render)
      if (coordDisplayRef.current) {
        coordDisplayRef.current.textContent = formatCoordinates(ra, dec, displayMode);
      }
    },
  });
  tracker.setTracking(true);

  return () => tracker.destroy();
}, [wcsParams]);
```

### Image Adjustments via CSS Filters
```typescript
// Source: CSS filter spec
function applyImageAdjustments(
  viewer: OpenSeadragon.Viewer,
  adjustments: { brightness: number; contrast: number; gamma: number; invert: boolean }
) {
  const canvas = viewer.drawer.canvas as HTMLCanvasElement;
  const filters = [
    `brightness(${adjustments.brightness})`,
    `contrast(${adjustments.contrast})`,
    adjustments.invert ? 'invert(1)' : '',
  ].filter(Boolean).join(' ');

  canvas.style.filter = filters;

  // Gamma requires manual application -- CSS has no gamma filter.
  // Apply via canvas 2D context post-processing or use a custom
  // OpenSeadragon filter plugin. For Phase 3, gamma can be approximated
  // by adjusting brightness+contrast curves.
}
```

### Observation Data API Endpoint
```python
# api/routers/observations.py
@router.get("/{observation_uuid}")
def get_observation(observation_uuid: str, db: Session = Depends(get_database_session)):
    obs = db.query(Observation).filter(
        Observation.observation_uuid == observation_uuid
    ).first()
    if not obs:
        raise HTTPException(404)

    # Get tile metadata from processing steps
    tile_step = db.query(ProcessingStep).filter(
        ProcessingStep.observation_uuid == obs.observation_uuid,
        ProcessingStep.step_name == "generate_tiles",
        ProcessingStep.step_status == StepStatus.completed,
    ).first()

    return {
        "observation_uuid": str(obs.observation_uuid),
        "archive_observation_id": obs.archive_observation_id,
        "telescope_name": obs.telescope_name,
        "instrument_name": obs.instrument_name,
        "spectral_filters": obs.spectral_filters,
        "total_exposure_seconds": obs.total_exposure_seconds,
        "pointing_ra_degrees": obs.pointing_ra_degrees,
        "pointing_dec_degrees": obs.pointing_dec_degrees,
        "pipeline_status": obs.pipeline_status.value,
        "tile_metadata": tile_step.step_output_metadata if tile_step else None,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom canvas zoom (pre-2015) | OpenSeadragon / Leaflet-based viewers | ~2012+ | No one hand-rolls zoom/pan anymore |
| Server-side WCS per-request (Aladin Lite v1) | Client-side WCS with pre-loaded params | Aladin Lite v3 (2023) | Real-time coordinate display without latency |
| openseadragon-react-viewer package | Direct useRef/useEffect wrapper | 2024 (package deprecated) | Fewer dependencies, full control |
| IIIF for everything | DZI for deep-zoom, IIIF for interop | Ongoing | DZI is simpler when you control the pipeline; IIIF is for federated access |

**Deprecated/outdated:**
- `openseadragon-react-viewer`: Deprecated, recommends clover-iiif (IIIF-specific, not DZI)
- wcsjs: Unmaintained Emscripten port. TAN projection is simple enough to implement directly.
- OpenSeadragon 3.x/4.x: v5.0 has API improvements; use latest

## Open Questions

1. **Y-axis orientation in DZI tiles**
   - What we know: FITS uses bottom-left origin, pyvips reads arrays top-to-bottom, DZI tiles inherit this order
   - What's unclear: Whether `naxis2 - y` flip is needed or if pyvips/numpy already handles it correctly
   - Recommendation: During implementation, test with a known observation (e.g., the Orion Nebula) where center RA/Dec are stored. Compare hover coordinates at image center with stored `pointing_ra_degrees`/`pointing_dec_degrees`. If they match, no flip needed. If Dec is inverted, add the Y flip.

2. **Gamma filter implementation**
   - What we know: CSS `filter` supports brightness, contrast, invert, but NOT gamma
   - What's unclear: Best approach for gamma without server re-rendering
   - Recommendation: OpenSeadragon's canvas drawer exposes the canvas element. Apply gamma via a LUT (lookup table) in a post-draw callback, or approximate gamma via brightness/contrast combination for Phase 3 (exact gamma can be added later via WebGL shader if needed).

3. **Multiple FITS files per observation (band selection)**
   - What we know: Phase 2 processes all FITS files from the MAST download for an observation. Each produces tiles. However, the current tile upload uses the same `{observation_uuid}/tiles/` prefix for ALL files, overwriting the first file's tiles.
   - What's unclear: Whether Phase 2 actually produces multiple tile sets or just tiles the first/primary FITS file
   - Recommendation: Investigate the Phase 2 tile upload logic during planning. If only one tile set exists per observation, band selection is deferred. If multiple tile sets exist, they need distinct S3 key prefixes (e.g., `{uuid}/{fits_filename}/tiles/`).

4. **Coordinate grid overlay rendering**
   - What we know: User wants coordinate grid available (off by default)
   - What's unclear: Whether to render on a canvas overlay or as SVG
   - Recommendation: Use an HTML/SVG overlay on top of the viewer. Compute grid line positions from WCS params for the current viewport bounds. Re-render on zoom/pan. Canvas overlay would also work but SVG gives crispy lines at all zoom levels. This is the most complex feature and could be scoped to a later plan within Phase 3 if needed.

## Sources

### Primary (HIGH confidence)
- [OpenSeadragon official docs](https://openseadragon.github.io/docs/) - DZI tile source config, viewport coordinates, navigator, overlays
- [OpenSeadragon DZI tile source example](https://openseadragon.github.io/examples/tilesource-dzi/) - Inline DZI configuration with custom `Url` property
- [OpenSeadragon viewport coordinates example](https://openseadragon.github.io/examples/viewport-coordinates/) - Mouse tracking, coordinate conversion between systems
- [OpenSeadragon custom tile source](https://openseadragon.github.io/examples/tilesource-custom/) - `getTileUrl` interface for custom URL patterns
- [OpenSeadragon navigator](https://openseadragon.github.io/examples/ui-viewport-navigator/) - Navigator position, auto-fade, custom container
- Existing codebase: `pipeline/tasks/tile.py` - DZI output format (256px tiles, 1px overlap, JPEG Q=85, S3 key structure)
- Existing codebase: `pipeline/tasks/validate_wcs.py` - WCS extraction approach, stored metadata structure
- Existing codebase: `shared/models.py` - Observation and ProcessingStep schemas
- Existing codebase: `api/routers/ingest.py` - Existing API patterns (FastAPI router, Pydantic models)
- FITS WCS Standard: Calabretta & Greisen 2002 (Paper II) - TAN gnomonic projection equations

### Secondary (MEDIUM confidence)
- [OpenSeadragon npm](https://www.npmjs.com/package/openseadragon) - Version 5.0.1 confirmed
- [OpenSeadragon Scalebar plugin](https://github.com/usnistgov/OpenSeadragonScalebar) - ASTRONOMY unit renderer, pixelsPerMeter config
- [astrojs/wcsjs GitHub](https://github.com/astrojs/wcsjs) - Reviewed and rejected (unmaintained, heavy bundle)
- [Presigned URLs - Boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html) - Reviewed; proxy approach preferred over presigned URLs

### Tertiary (LOW confidence)
- [use-open-seadragon React hooks](https://github.com/stephenwf/use-open-seadragon) - TypeScript hooks wrapper. Reviewed but not recommended (adds abstraction layer, limited maintenance)
- [MinIO CORS issues](https://github.com/minio/minio/issues/11111) - Confirms CORS challenges, supports proxy approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - OpenSeadragon is the undisputed standard for DZI viewing. The existing Phase 2 pipeline was designed specifically to produce OpenSeadragon-compatible output.
- Architecture: HIGH - React wrapper pattern is well-established. Tile proxy via FastAPI is straightforward. WCS math is documented in formal papers.
- Pitfalls: HIGH - Identified from actual codebase analysis (WCS params gap, Y-axis inversion) and known issues (CORS, SSR, React re-render).
- Coordinate conversion: MEDIUM - TAN projection math is well-documented but the Y-axis flip question requires empirical validation during implementation.

**Research date:** 2026-02-22
**Valid until:** 2026-04-22 (stable domain, libraries evolving slowly)
