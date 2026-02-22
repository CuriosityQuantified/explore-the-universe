"use client";

import {
  useEffect,
  useRef,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import OpenSeadragon from "openseadragon";
import type { WcsParams, TileMetadata } from "@/types/observation";
import { pixelToRaDec } from "@/lib/wcs";

/**
 * Extended mouse tracker event type. The @types/openseadragon definitions
 * are incomplete -- moveHandler and clickHandler receive events with
 * `position` and `quick` properties at runtime, but the type defs only
 * declare the base MouseTrackerEvent without these fields.
 */
interface OsdMouseEvent extends OpenSeadragon.MouseTrackerEvent {
  position: OpenSeadragon.Point;
  quick?: boolean;
}

export interface SkyViewerHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  goHome: () => void;
  toggleFullscreen: () => void;
  toggleNavigator: () => void;
}

interface SkyViewerProps {
  observationUuid: string;
  wcsParams: WcsParams;
  tileMetadata: TileMetadata;
  tileBaseUrl: string;
  onCoordinateChange: (
    ra: number,
    dec: number,
    pixelX: number,
    pixelY: number,
  ) => void;
  onCoordinateClick: (ra: number, dec: number) => void;
  onViewerReady: (viewer: OpenSeadragon.Viewer) => void;
}

const SkyViewer = forwardRef<SkyViewerHandle, SkyViewerProps>(
  function SkyViewer(
    {
      observationUuid,
      wcsParams,
      tileMetadata,
      tileBaseUrl,
      onCoordinateChange,
      onCoordinateClick,
      onViewerReady,
    },
    ref,
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);
    const rafPendingRef = useRef(false);

    // Stable callback refs to avoid re-creating mouse tracker on every render
    const onCoordinateChangeRef = useRef(onCoordinateChange);
    onCoordinateChangeRef.current = onCoordinateChange;
    const onCoordinateClickRef = useRef(onCoordinateClick);
    onCoordinateClickRef.current = onCoordinateClick;

    // Expose viewer controls to parent via ref
    useImperativeHandle(
      ref,
      () => ({
        zoomIn: () => {
          viewerRef.current?.viewport.zoomBy(1.5);
          viewerRef.current?.viewport.applyConstraints();
        },
        zoomOut: () => {
          viewerRef.current?.viewport.zoomBy(0.67);
          viewerRef.current?.viewport.applyConstraints();
        },
        goHome: () => {
          viewerRef.current?.viewport.goHome();
        },
        toggleFullscreen: () => {
          if (viewerRef.current) {
            viewerRef.current.setFullScreen(
              !viewerRef.current.isFullPage(),
            );
          }
        },
        toggleNavigator: () => {
          if (viewerRef.current) {
            const nav = viewerRef.current.navigator;
            if (nav) {
              const element = nav.element as HTMLElement;
              element.style.display =
                element.style.display === "none" ? "block" : "none";
            }
          }
        },
      }),
      [],
    );

    // Initialize OpenSeadragon viewer
    useEffect(() => {
      if (!containerRef.current) return;

      const viewer = OpenSeadragon({
        element: containerRef.current,
        tileSources: {
          Image: {
            xmlns: "http://schemas.microsoft.com/deepzoom/2008",
            Url: `${tileBaseUrl}tiles/`,
            Format: "jpg",
            Overlap: "1",
            TileSize: "256",
            Size: {
              Width: String(tileMetadata.image_width_pixels),
              Height: String(tileMetadata.image_height_pixels),
            },
          },
        },
        showNavigator: false,
        navigatorPosition: "BOTTOM_LEFT",
        gestureSettingsMouse: { scrollToZoom: true },
        gestureSettingsTouch: { pinchToZoom: true },
        visibilityRatio: 1.0,
        minZoomLevel: 0.5,
        defaultZoomLevel: 0,
        immediateRender: true,
        imageLoaderLimit: 4,
        showNavigationControl: false,
      });

      viewerRef.current = viewer;
      onViewerReady(viewer);

      return () => {
        viewer.destroy();
        viewerRef.current = null;
      };
    }, [observationUuid, tileMetadata, tileBaseUrl, onViewerReady]);

    // Mouse tracking for coordinate overlay
    useEffect(() => {
      const viewer = viewerRef.current;
      if (!viewer || !containerRef.current) return;

      const tracker = new OpenSeadragon.MouseTracker({
        element: containerRef.current,
        moveHandler: (event) => {
          if (rafPendingRef.current) return;
          rafPendingRef.current = true;

          const osdEvent = event as unknown as OsdMouseEvent;

          requestAnimationFrame(() => {
            rafPendingRef.current = false;
            if (!viewer.viewport || !osdEvent.position) return;

            const viewportPoint = viewer.viewport.pointFromPixel(
              osdEvent.position,
            );
            const imagePoint =
              viewer.viewport.viewportToImageCoordinates(viewportPoint);

            // Convert to FITS pixel coords (Y flip: FITS origin is bottom-left)
            const fitsX = imagePoint.x;
            const fitsY = wcsParams.naxis2 - imagePoint.y;

            const { ra, dec } = pixelToRaDec(fitsX, fitsY, wcsParams);
            onCoordinateChangeRef.current(
              ra,
              dec,
              imagePoint.x,
              imagePoint.y,
            );
          });
        },
        clickHandler: (event) => {
          const osdEvent = event as unknown as OsdMouseEvent;
          if (!viewer.viewport || !osdEvent.position) return;
          // Only handle single clicks (not double-click zoom)
          if (osdEvent.quick) {
            const viewportPoint = viewer.viewport.pointFromPixel(
              osdEvent.position,
            );
            const imagePoint =
              viewer.viewport.viewportToImageCoordinates(viewportPoint);

            const fitsX = imagePoint.x;
            const fitsY = wcsParams.naxis2 - imagePoint.y;

            const { ra, dec } = pixelToRaDec(fitsX, fitsY, wcsParams);
            onCoordinateClickRef.current(ra, dec);
          }
        },
      });

      return () => {
        tracker.destroy();
      };
    }, [wcsParams]);

    return <div ref={containerRef} className="h-full w-full bg-black" />;
  },
);

export default SkyViewer;
