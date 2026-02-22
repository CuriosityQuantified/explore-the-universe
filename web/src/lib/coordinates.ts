/**
 * Coordinate formatting utilities for RA/Dec display.
 *
 * Converts decimal degree coordinates to HMS (hours/minutes/seconds)
 * and DMS (degrees/arcminutes/arcseconds) notation for the viewer
 * coordinate overlay (CoordinateOverlay.tsx).
 */

/**
 * Convert RA in decimal degrees to hours-minutes-seconds string.
 *
 * RA is measured in hours (0-24h), so divide degrees by 15 first.
 * Output format: "05h 35m 17.3s"
 *
 * @param degrees - Right Ascension in decimal degrees (0-360)
 * @returns Formatted HMS string
 */
export function decimalDegreesToHms(degrees: number): string {
  const totalHours = degrees / 15;
  const hours = Math.floor(totalHours);
  const remainingMinutes = (totalHours - hours) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  const hoursStr = String(hours).padStart(2, "0");
  const minutesStr = String(minutes).padStart(2, "0");
  const secondsStr = seconds.toFixed(1).padStart(4, "0");

  return `${hoursStr}h ${minutesStr}m ${secondsStr}s`;
}

/**
 * Convert Declination in decimal degrees to degrees-arcminutes-arcseconds string.
 *
 * Output format: "+05d 23m 28.1s" or "-05d 23m 28.1s"
 *
 * @param degrees - Declination in decimal degrees (-90 to +90)
 * @returns Formatted DMS string with sign prefix
 */
export function decimalDegreesToDms(degrees: number): string {
  const sign = degrees >= 0 ? "+" : "-";
  const absDeg = Math.abs(degrees);
  const deg = Math.floor(absDeg);
  const remainingMinutes = (absDeg - deg) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  const degStr = String(deg).padStart(2, "0");
  const minutesStr = String(minutes).padStart(2, "0");
  const secondsStr = seconds.toFixed(1).padStart(4, "0");

  return `${sign}${degStr}d ${minutesStr}m ${secondsStr}s`;
}

/**
 * Format RA/Dec coordinates for display in the viewer overlay.
 *
 * @param ra - Right Ascension in decimal degrees
 * @param dec - Declination in decimal degrees
 * @param mode - "hms" for HMS/DMS notation, "decimal" for decimal degrees
 * @returns Formatted coordinate string
 */
export function formatCoordinates(
  ra: number,
  dec: number,
  mode: "hms" | "decimal",
): string {
  if (mode === "decimal") {
    return `${ra.toFixed(3)}d, ${dec.toFixed(3)}d`;
  }
  return `${decimalDegreesToHms(ra)}, ${decimalDegreesToDms(dec)}`;
}
