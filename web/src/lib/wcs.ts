/**
 * WCS (World Coordinate System) TAN gnomonic deprojection.
 *
 * Converts pixel coordinates from an OpenSeadragon image to RA/Dec sky
 * coordinates using the TAN (gnomonic) projection defined in FITS WCS
 * headers (Calabretta & Greisen 2002).
 *
 * The math follows the FITS WCS standard:
 *   1. Pixel offset from reference pixel (CRPIX)
 *   2. CD matrix transform to intermediate world coords (degrees)
 *   3. TAN deprojection to native spherical coords
 *   4. Spherical rotation to celestial (RA/Dec)
 */

import type { WcsParams } from "@/types/observation";

/**
 * Convert image pixel coordinates to RA/Dec sky coordinates.
 *
 * @param pixelX - X coordinate in FITS pixel space (1-indexed)
 * @param pixelY - Y coordinate in FITS pixel space (1-indexed)
 * @param wcs - WCS parameters from the FITS header (CRPIX, CRVAL, CD matrix)
 * @returns Object with ra (degrees, 0-360) and dec (degrees, -90 to +90)
 */
export function pixelToRaDec(
  pixelX: number,
  pixelY: number,
  wcs: WcsParams,
): { ra: number; dec: number } {
  // Step 1: Pixel offset from reference pixel (FITS is 1-indexed)
  const dx = pixelX - wcs.crpix1;
  const dy = pixelY - wcs.crpix2;

  // Step 2: Apply CD matrix to get intermediate world coordinates (degrees)
  const xiDeg = wcs.cd1_1 * dx + wcs.cd1_2 * dy;
  const etaDeg = wcs.cd2_1 * dx + wcs.cd2_2 * dy;

  // Convert to radians for trig
  const deg2rad = Math.PI / 180;
  const rad2deg = 180 / Math.PI;
  const xi = xiDeg * deg2rad;
  const eta = etaDeg * deg2rad;

  // Reference point in radians
  const ra0 = wcs.crval1 * deg2rad;
  const dec0 = wcs.crval2 * deg2rad;

  // Step 3: TAN deprojection
  const rTheta = Math.sqrt(xi * xi + eta * eta);

  if (rTheta === 0) {
    // At the reference pixel -- return reference coordinates directly
    return { ra: wcs.crval1, dec: wcs.crval2 };
  }

  const c = Math.atan(rTheta);
  const sinC = Math.sin(c);
  const cosC = Math.cos(c);

  // Step 4: Spherical rotation to celestial coordinates
  const dec = Math.asin(
    cosC * Math.sin(dec0) + (eta * sinC * Math.cos(dec0)) / rTheta,
  );

  const ra = ra0 + Math.atan2(
    xi * sinC,
    rTheta * Math.cos(dec0) * cosC - eta * Math.sin(dec0) * sinC,
  );

  // Normalize RA to [0, 360)
  let raDeg = ra * rad2deg;
  raDeg = ((raDeg % 360) + 360) % 360;

  return { ra: raDeg, dec: dec * rad2deg };
}
