/**
 * Computes the on-screen scale (px per mm) so the entire stage fits inside
 * the container with a small padding. Returns 0 when the container hasn't
 * been measured yet, so the caller can skip rendering until layout settles
 * — otherwise we'd briefly draw a 100-px-wide stub and then resize.
 */
export function fitScale(
  container: { width: number; height: number },
  stage: { width_mm: number; height_mm: number },
  paddingPx = 16,
): number {
  if (container.width <= 0 || container.height <= 0) return 0;
  const availW = Math.max(50, container.width - paddingPx * 2);
  const availH = Math.max(50, container.height - paddingPx * 2);
  const scaleX = availW / stage.width_mm;
  const scaleY = availH / stage.height_mm;
  return Math.min(scaleX, scaleY);
}
