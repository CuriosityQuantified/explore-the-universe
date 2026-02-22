# Phase 3: Sky Viewer - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Deep-zoom tile viewer for ingested JWST imagery. Users can pan and zoom smoothly from full field to pixel scale, with sky coordinates displayed on hover and click. Tiles are DZI pyramids stored in MinIO (produced by Phase 2). Search, object overlays, and segmentation display belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Coordinate display
- Default format: HMS/DMS (05h 35m 17.3s, -05d 23m 28s) with toggle to decimal degrees
- Hover shows live coordinates following the cursor in real-time
- Click pins a persistent coordinate readout that can be copied
- Click-to-copy: clicking a point copies coordinates to clipboard with a brief toast confirmation
- Coordinate grid overlay: available but off by default, user can toggle it on

### Viewer controls
- Minimap/overview: available but toggleable (off by default to maximize image area)
- Zoom buttons: visible +/- controls on the viewer
- Scale bar: shows angular size (arcmin/arcsec) as primary, pixel count as secondary
- Home button: resets view to fit the full image in one click
- Standard scroll-wheel zoom and drag-to-pan expected

### Page layout & styling
- Dark theme (no light mode toggle for this phase) -- standard for astronomy, makes faint details pop
- Embedded layout with fullscreen toggle: viewer fills most of the page with surrounding UI, button to go fullscreen
- Observation info panel: sidebar showing observation ID, telescope, instrument, filter, exposure time, date
- Tile loading: blur-up strategy (show lower-resolution tiles immediately, sharpen as high-res tiles load -- Google Maps style)

### Image adjustment
- Client-side adjustments via CSS/canvas filters (no server re-rendering)
- Full control set: brightness, contrast, gamma, and invert toggle
- Collapsible panel: hidden by default, expand via a toolbar button to keep viewer clean
- Reset button: single click restores all adjustments to default rendering

### Band selection
- Band/filter selector: dropdown or tabs to switch between available FITS files for the same observation
- Each band loads its own tile pyramid from MinIO

### Claude's Discretion
- Deep-zoom library choice (OpenSeadragon, Leaflet, or equivalent)
- Coordinate grid rendering approach (canvas overlay, SVG, etc.)
- Exact sidebar layout and responsive breakpoints
- Keyboard shortcut mappings
- Touch gesture support details
- Error states for missing/failed tiles

</decisions>

<specifics>
## Specific Ideas

- Blur-up tile loading like Google Maps -- lower res visible immediately, high-res sharpens in
- Coordinate readout should feel like DS9 or Aladin Lite -- live, responsive, professional
- Dark theme is the only theme for now -- space imagery on dark backgrounds is the standard
- Band selector enables comparing the same field in different filters without leaving the page

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 03-sky-viewer*
*Context gathered: 2026-02-22*
