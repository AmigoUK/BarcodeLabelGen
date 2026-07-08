/**
 * Minimal single-file ZIP writer (stored, no compression) that carries unix
 * permission bits. A browser blob download can never set +x on the file, but
 * a zip's external attributes can — macOS Archive Utility restores the mode
 * on extraction, so a `.command` inside becomes double-clickable.
 */

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(data: Uint8Array): number {
  let c = 0xffffffff;
  for (const b of data) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** Fixed DOS timestamp (2026-01-01 00:00) — deterministic output for tests. */
const DOS_TIME = 0;
const DOS_DATE = ((2026 - 1980) << 9) | (1 << 5) | 1;

/** Build a zip containing exactly one file with the given unix mode. */
export function zipSingleFile(name: string, content: string, mode = 0o755): Uint8Array {
  const nameBytes = new TextEncoder().encode(name);
  const data = new TextEncoder().encode(content);
  const crc = crc32(data);
  // S_IFREG | mode, shifted into the high 16 bits of external attributes.
  const extAttrs = ((0o100000 | mode) << 16) >>> 0;

  const local = new Uint8Array(30 + nameBytes.length);
  const lv = new DataView(local.buffer);
  lv.setUint32(0, 0x04034b50, true); // local file header signature
  lv.setUint16(4, 20, true); // version needed
  lv.setUint16(6, 0, true); // flags
  lv.setUint16(8, 0, true); // method: stored
  lv.setUint16(10, DOS_TIME, true);
  lv.setUint16(12, DOS_DATE, true);
  lv.setUint32(14, crc, true);
  lv.setUint32(18, data.length, true); // compressed size
  lv.setUint32(22, data.length, true); // uncompressed size
  lv.setUint16(26, nameBytes.length, true);
  lv.setUint16(28, 0, true); // extra length
  local.set(nameBytes, 30);

  const central = new Uint8Array(46 + nameBytes.length);
  const cv = new DataView(central.buffer);
  cv.setUint32(0, 0x02014b50, true); // central directory signature
  cv.setUint16(4, (3 << 8) | 20, true); // version made by: unix
  cv.setUint16(6, 20, true); // version needed
  cv.setUint16(8, 0, true);
  cv.setUint16(10, 0, true); // stored
  cv.setUint16(12, DOS_TIME, true);
  cv.setUint16(14, DOS_DATE, true);
  cv.setUint32(16, crc, true);
  cv.setUint32(20, data.length, true);
  cv.setUint32(24, data.length, true);
  cv.setUint16(28, nameBytes.length, true);
  // extra/comment/disk/internal attrs = 0
  cv.setUint32(38, extAttrs, true); // external attributes: unix mode
  cv.setUint32(42, 0, true); // local header offset
  central.set(nameBytes, 46);

  const centralOffset = local.length + data.length;
  const eocd = new Uint8Array(22);
  const ev = new DataView(eocd.buffer);
  ev.setUint32(0, 0x06054b50, true); // end of central directory
  ev.setUint16(8, 1, true); // entries on this disk
  ev.setUint16(10, 1, true); // entries total
  ev.setUint32(12, central.length, true);
  ev.setUint32(16, centralOffset, true);

  const out = new Uint8Array(centralOffset + central.length + eocd.length);
  out.set(local, 0);
  out.set(data, local.length);
  out.set(central, centralOffset);
  out.set(eocd, centralOffset + central.length);
  return out;
}
