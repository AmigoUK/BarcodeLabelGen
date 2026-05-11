/**
 * Computes the on-screen scale (px per mm) so the entire stage fits inside
 * the container with a small padding. Pure function — easy to unit-test
 * once we add Vitest.
 */
export function fitScale(
  container: { width: number; height: number },
  stage: { width_mm: number; height_mm: number },
  paddingPx = 32,
): number {
  const availW = Math.max(100, container.width - paddingPx * 2);
  const availH = Math.max(100, container.height - paddingPx * 2);
  const scaleX = availW / stage.width_mm;
  const scaleY = availH / stage.height_mm;
  return Math.min(scaleX, scaleY);
}
