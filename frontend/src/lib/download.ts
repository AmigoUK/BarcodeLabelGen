/** Trigger a browser download of a Blob with a chosen filename.
 *  Centralizes the throwaway-anchor-element trick used by every "Save as…"
 *  flow (PDF batch, template export, …) so the same one-liner is reused. */
export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
