# F35 — CUPS Virtual Printer (macOS/Linux) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let macOS/Linux users capture ZPL from other applications into the Inbox by routing a CUPS raw print queue to the existing `blg-connector` capture listener — via a helper script and documentation, with zero agent code changes.

**Architecture:** The connector's `Capturer` is already a cross-platform TCP listener and `looksLikeZPL` already rejects non-ZPL, so F35 adds only (a) `connector/install-capture-cups.sh` that creates a CUPS raw queue targeting `socket://127.0.0.1:9101`, (b) a README split documenting the macOS/Linux path and its limits, and (c) a doc-comment tweak plus version/changelog/release bookkeeping. Runtime verification is done on this Linux server with a real CUPS install.

**Tech Stack:** Bash, CUPS (`lpadmin`/`lp`/`lpstat`), Go 1.22 connector (unchanged behaviour), Docker-less local test.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-04-f35-cups-capture-design.md`. Variant **B**.
- **Zero changes to agent Go behaviour.** Only a doc-comment on `CaptureConfig` may change (no code path).
- Queue name default: `BarcodeLabelGen-Capture`. Target default: `127.0.0.1:9101`. Both overridable via env vars `QUEUE` / `TARGET`.
- Raw queue command: `lpadmin -p "$QUEUE" -E -v "socket://$TARGET" -m raw`.
- Script: `set -euo pipefail`, errors to STDERR, non-zero exit on failure, **no auto-`sudo`**. Match `connector/build-all.sh` style.
- Out of scope (must stay documented as such): Zebra/CUPS driver for generic apps (Word, browser). macOS is **unverified** (no physical Mac) — label it so.
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Versions: app `0.17.0 → 0.18.0` (`frontend/package.json`, `backend/pyproject.toml`); connector `0.4.0 → 0.5.0` (`connector/version.go`).

---

### Task 1: Install helper script `install-capture-cups.sh`

**Files:**
- Create: `connector/install-capture-cups.sh`

**Interfaces:**
- Consumes: nothing (standalone script).
- Produces: a CUPS raw queue named `$QUEUE` (default `BarcodeLabelGen-Capture`) whose device URI is `socket://$TARGET` (default `127.0.0.1:9101`). Later verification (Task 2) and README (Task 3) reference the exact queue name, env vars, and the `lp -d "$QUEUE"` / `lpadmin -x "$QUEUE"` usage it prints.

- [ ] **Step 1: Write the script**

Create `connector/install-capture-cups.sh` with exactly this content:

```bash
#!/usr/bin/env bash
# Create a CUPS raw print queue that forwards captured ZPL to a local
# blg-connector. Works on Linux and macOS (both ship CUPS + lpadmin).
#
# The queue is "raw" (-m raw): CUPS passes each job's bytes through with no
# filter to socket://127.0.0.1:9101, where the connector's capture listener
# picks it up. This only helps applications that ALREADY emit ZPL — generic
# apps (Word, browsers) print PostScript and the agent will reject them.
#
#   QUEUE=name TARGET=host:port ./install-capture-cups.sh
set -euo pipefail

QUEUE="${QUEUE:-BarcodeLabelGen-Capture}"
TARGET="${TARGET:-127.0.0.1:9101}"

if ! command -v lpadmin >/dev/null 2>&1; then
  echo "error: lpadmin not found — install CUPS first" >&2
  echo "  Debian/Ubuntu: sudo apt install cups cups-client" >&2
  echo "  Fedora:        sudo dnf install cups" >&2
  echo "  macOS:         CUPS is built in (check that printing is enabled)" >&2
  exit 1
fi

echo "→ creating raw queue '$QUEUE' → socket://$TARGET"
if ! lpadmin -p "$QUEUE" -E -v "socket://$TARGET" -m raw; then
  echo >&2
  echo "error: lpadmin failed — this usually means missing permissions." >&2
  echo "  Re-run with sudo, or add yourself to the CUPS admin group:" >&2
  echo "    Linux: sudo usermod -aG lpadmin \"\$USER\"  (log out/in after)" >&2
  echo "    macOS: sudo dseditgroup -o edit -a \"\$USER\" -t user _lpadmin" >&2
  exit 1
fi

echo
echo "Done. Queue '$QUEUE' forwards to socket://$TARGET."
echo "Make sure blg-connector runs with a capture.listen matching $TARGET."
echo
echo "Print a ZPL file to it:   lp -d \"$QUEUE\" label.zpl"
echo "Remove the queue:         lpadmin -x \"$QUEUE\""
```

- [ ] **Step 2: Make it executable and lint it**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
chmod +x install-capture-cups.sh
bash -n install-capture-cups.sh && echo "SYNTAX-OK"
command -v shellcheck >/dev/null && shellcheck install-capture-cups.sh || echo "shellcheck not installed — skipping"
```
Expected: `SYNTAX-OK`; if shellcheck is present, no errors (warnings acceptable, fix any SC2086-style quoting it flags).

- [ ] **Step 3: Dry-run the no-CUPS error path**

Run (simulate missing lpadmin by shadowing PATH):
```bash
env -i PATH=/nonexistent bash /var/www/html/BarcodeLabelGen/connector/install-capture-cups.sh; echo "exit=$?"
```
Expected: prints `error: lpadmin not found …` to stderr and `exit=1`.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/install-capture-cups.sh
git commit -m "feat(connector): install-capture-cups.sh — CUPS raw queue helper (F35)

Creates a raw CUPS queue forwarding to the agent's capture listener, for
capturing ZPL from other apps on macOS/Linux. Idempotent, no auto-sudo.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Runtime verification on Linux (real CUPS)

**Files:** none (verification only — produces evidence, no repo change unless a bug is found).

**Interfaces:**
- Consumes: the script and queue behaviour from Task 1; the connector binary (`go build`), its `capture.listen`/`capture.spool_dir` config (`connector/config.go`), and `looksLikeZPL` rejection (`connector/zplcheck.go`).
- Produces: confirmed evidence that a `lp` job of valid ZPL reaches the agent spool and that non-ZPL is rejected — recorded in the task's report. No code artifact.

- [ ] **Step 1: Ensure CUPS is available on this server**

Run:
```bash
command -v lpadmin lp lpstat || (sudo apt-get update -qq && sudo apt-get install -y cups cups-client)
sudo systemctl start cups 2>/dev/null || sudo cupsd 2>/dev/null || true
lpstat -r || echo "scheduler status above"
```
Expected: `lpadmin`, `lp`, `lpstat` resolve and the scheduler is running. If install is refused/unavailable, STOP and report BLOCKED (do not fake the queue).

- [ ] **Step 2: Build the connector and write a test config**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
go build -o /tmp/blg-connector .
mkdir -p /tmp/blg-cap-spool
cat > /tmp/blg-cap-test.yaml <<'YAML'
server_url: "http://127.0.0.1:1"   # dummy — upload will fail, that's fine
token: "blg_test"
poll_interval_seconds: 3600
heartbeat_interval_seconds: 3600
listen: "127.0.0.1:19110"
printers: []
capture:
  listen: "127.0.0.1:9101"
  spool_dir: "/tmp/blg-cap-spool"
YAML
```
Expected: binary at `/tmp/blg-connector`, config written.

- [ ] **Step 3: Start the agent in the background**

Run:
```bash
/tmp/blg-connector -config /tmp/blg-cap-test.yaml > /tmp/blg-cap.log 2>&1 &
echo $! > /tmp/blg-cap.pid
sleep 1
grep -q "virtual printer listening on 127.0.0.1:9101" /tmp/blg-cap.log && echo "LISTENER-UP"
```
Expected: `LISTENER-UP`.

- [ ] **Step 4: Create the queue via the script**

Run:
```bash
sudo QUEUE=BLG-Test TARGET=127.0.0.1:9101 bash /var/www/html/BarcodeLabelGen/connector/install-capture-cups.sh
lpstat -v BLG-Test
```
Expected: script prints "Done…"; `lpstat -v` shows `device for BLG-Test: socket://127.0.0.1:9101`.

- [ ] **Step 5: Print valid ZPL and confirm capture**

Run:
```bash
printf '^XA^FO50,50^A0N,40,40^FDF35 capture test^FS^XZ' > /tmp/test.zpl
lp -d BLG-Test -o raw /tmp/test.zpl
sleep 3
echo "--- agent log ---"; tail -5 /tmp/blg-cap.log
echo "--- spool ---"; ls -la /tmp/blg-cap-spool/
```
Expected: agent log shows a captured job (e.g. "captured … bytes" / an upload attempt); a spool file exists (upload to the dummy server fails and it stays queued — that proves *capture* worked).

- [ ] **Step 6: Negative test — non-ZPL is rejected**

Run:
```bash
printf '%%!PS-Adobe-3.0\nshowpage\n' > /tmp/test.ps
lp -d BLG-Test -o raw /tmp/test.ps
sleep 2
tail -5 /tmp/blg-cap.log
```
Expected: agent log shows rejection (payload "looks like a PostScript document, not ZPL" or equivalent); no new valid job accepted.

- [ ] **Step 7: Idempotency — run the script again**

Run:
```bash
sudo QUEUE=BLG-Test TARGET=127.0.0.1:9101 bash /var/www/html/BarcodeLabelGen/connector/install-capture-cups.sh
lpstat -p BLG-Test | head -1
```
Expected: succeeds again, no duplicate queue (still one `BLG-Test`).

- [ ] **Step 8: Tear down the test queue and agent**

Run:
```bash
sudo lpadmin -x BLG-Test || true
kill "$(cat /tmp/blg-cap.pid)" 2>/dev/null || true
```
Expected: queue removed, agent stopped. (No commit — this task changes no repo files. If a defect was found, fix it in Task 1 and re-run.)

---

### Task 3: README — macOS/Linux capture path + doc-comment

**Files:**
- Modify: `connector/README.md` (the "Wirtualna drukarka (przechwytywanie ZPL…)" section, currently the Windows-only steps around lines 105–127)
- Modify: `connector/config.go:24-30` (the `CaptureConfig` doc-comment)

**Interfaces:**
- Consumes: the queue name, env vars, and `lp`/`lpadmin` usage from Task 1; the capture limits already documented (no `^GFB`, bitmap passthrough, spool retry).
- Produces: user-facing docs; no code symbols.

- [ ] **Step 1: Restructure the README capture section**

In `connector/README.md`, replace the current single-path "Konfiguracja na Windows…" body so the section reads (keep the existing intro paragraph about the Inbox, and keep the existing "Ograniczenia:" paragraph at the end unchanged):

```markdown
**Konfiguracja na Windows (bez pisania sterownika):**

1. Zainstaluj darmowy sterownik **ZDesigner** (ze strony Zebry) — to on
   generuje ZPL.
2. *Ustawienia → Drukarki → Dodaj drukarkę → ręcznie*: nowy port
   **Standard TCP/IP**, adres `127.0.0.1`, port `9101`, protokół **RAW**,
   **wyłącz SNMP**.
3. Jako sterownik wybierz ZDesigner (dowolny model o rozmiarze twoich
   etykiet). Nazwij drukarkę np. „BarcodeLabelGen (przechwytywanie)".
4. Drukuj na nią z dowolnej aplikacji — zadanie pojawi się w Inboxie.

**Konfiguracja na macOS / Linux (CUPS):**

Na Unix nie ma sterownika ZDesigner, więc przechwytywanie działa dla
aplikacji, które **już wysyłają ZPL** (POS, systemy etykietujące, skrypty).
Zwykłe aplikacje (Word, przeglądarka) drukują PostScript — agent je odrzuci.

1. W `config.yaml` agenta włącz sekcję `capture` nasłuchującą na porcie
   `127.0.0.1:9101` (patrz przykład konfiguracji wyżej) i uruchom agenta.
2. Utwórz systemową kolejkę CUPS kierującą na agenta — jedną komendą:

   ```
   cd connector
   ./install-capture-cups.sh
   ```

   (nazwę kolejki lub cel zmienisz przez `QUEUE=… TARGET=host:port
   ./install-capture-cups.sh`). Równoważnie ręcznie:
   `lpadmin -p BarcodeLabelGen-Capture -E -v socket://127.0.0.1:9101 -m raw`.
   Skrypt nie wywołuje `sudo` sam — jeśli `lpadmin` zgłosi brak uprawnień,
   uruchom go przez `sudo` lub dodaj się do grupy `lpadmin`/`_lpadmin`.
3. Drukuj ZPL na kolejkę: `lp -d BarcodeLabelGen-Capture etykieta.zpl` —
   zadanie pojawi się w Inboxie. Kolejkę usuniesz przez
   `lpadmin -x BarcodeLabelGen-Capture`.

> **macOS:** nowsze wersje CUPS od Apple bywają restrykcyjne wobec kolejek
> „raw". Ścieżka jest udokumentowana, ale **nie została zweryfikowana na
> fizycznym Macu** — na Linuksie działa. Zgłoś, jeśli natrafisz na problem.

> Chcesz przechwytywać ze zwykłych aplikacji (nie-ZPL)? To wymaga sterownika
> Zebra/CUPS generującego ZPL — poza zakresem tej wersji.
```

- [ ] **Step 2: Update the `CaptureConfig` doc-comment**

In `connector/config.go`, replace the `CaptureConfig` doc-comment (lines 24–26) so it no longer implies Windows-only:

```go
// CaptureConfig enables the virtual-printer listener: a print queue pointed
// at this TCP port turns another app's ZPL output into a captured job.
// Windows: Standard TCP/IP port → 127.0.0.1:9101 with a ZDesigner driver.
// macOS/Linux: a CUPS raw queue → socket://127.0.0.1:9101 (see README).
```

- [ ] **Step 3: Verify the connector still builds/vets (comment-only change)**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
gofmt -l . && go vet ./... && go test ./... 2>&1 | tail -1
```
Expected: `gofmt` prints nothing, `vet` clean, tests `ok`.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/README.md connector/config.go
git commit -m "docs(connector): document CUPS capture path for macOS/Linux (F35)

Split the virtual-printer section into Windows and macOS/Linux (CUPS raw
queue), with the ZPL-source limit and the macOS-unverified caveat spelled
out. Widen the CaptureConfig doc-comment beyond Windows.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Version bump, CHANGELOG, PROJECT.md, release v0.18.0

**Files:**
- Modify: `frontend/package.json` (`"version"`), `backend/pyproject.toml` (`version`), `connector/version.go` (`Version`)
- Modify: `CHANGELOG.md` (new `[0.18.0]` section + reference links)
- Modify: `docs/PROJECT.md` (F35 row → zrealizowane)

**Interfaces:**
- Consumes: the completed script (Task 1) and docs (Task 3).
- Produces: tag `v0.18.0` + GitHub release with the existing 6 connector binaries.

- [ ] **Step 1: Bump versions**

Run:
```bash
cd /var/www/html/BarcodeLabelGen
sed -i 's/"version": "0.17.0"/"version": "0.18.0"/' frontend/package.json
sed -i '0,/^version = "0.17.0"/s//version = "0.18.0"/' backend/pyproject.toml
sed -i 's/const Version = "0.4.0"/const Version = "0.5.0"/' connector/version.go
grep '"version"' frontend/package.json; grep -m1 '^version' backend/pyproject.toml; grep 'const Version' connector/version.go
```
Expected: app `0.18.0`, connector `0.5.0`.

- [ ] **Step 2: Add the CHANGELOG section**

In `CHANGELOG.md`, under `## [Unreleased]` (leave it `_Nothing yet._`), insert a new section directly above `## [0.17.0] — 2026-07-04`:

```markdown
## [0.18.0] — 2026-07-04

### Added
- **CUPS virtual printer for macOS and Linux (F35).** Capture ZPL from
  other applications on Unix by routing a CUPS raw queue to the connector's
  capture listener. New `connector/install-capture-cups.sh` creates the
  queue in one command (`socket://127.0.0.1:9101`, `-m raw`, idempotent,
  no auto-sudo). The connector needs no code changes — its capture listener
  was already cross-platform. Works for apps that already emit ZPL; generic
  apps (Word, browsers) still need a Zebra driver (out of scope). README
  gains a Windows / macOS+Linux split; the macOS raw-queue path is
  documented but unverified on physical hardware.
```

And add the reference link — replace:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.17.0...HEAD
[0.17.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.17.0
```
with:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.18.0...HEAD
[0.18.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.18.0
[0.17.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.17.0
```

- [ ] **Step 3: Mark F35 done in PROJECT.md**

In `docs/PROJECT.md`, find the `| F35 |` row and append to its description (before the trailing `| P2 |`): ` — **zrealizowane w v0.18.0** (`connector/install-capture-cups.sh` + README; sterownik Zebry dla zwykłych aplikacji poza zakresem)`.

- [ ] **Step 4: Rebuild connector binaries (unchanged src, for release Assets)**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
./build-all.sh 2>&1 | tail -3
```
Expected: 6 binaries in `connector/dist/` (they now report `0.5.0`).

- [ ] **Step 5: Commit, tag, push**

```bash
cd /var/www/html/BarcodeLabelGen
git add frontend/package.json backend/pyproject.toml connector/version.go CHANGELOG.md docs/PROJECT.md
git commit -m "chore(release): v0.18.0 — CUPS virtual printer for macOS/Linux (F35)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git tag -a v0.18.0 -m "v0.18.0 — CUPS virtual printer for macOS/Linux (F35)"
git push origin main && git push origin v0.18.0
```
Expected: pushed, tag on remote.

- [ ] **Step 6: Create the GitHub release with binaries**

```bash
cd /var/www/html/BarcodeLabelGen
gh release create v0.18.0 \
  --title "v0.18.0 — CUPS virtual printer for macOS/Linux" \
  --notes "$(awk '/^## \[0.18.0\]/{f=1;next} /^## \[0.17.0\]/{f=0} f' CHANGELOG.md)" \
  connector/dist/blg-connector-windows-amd64.exe \
  connector/dist/blg-connector-macos-intel \
  connector/dist/blg-connector-macos-apple \
  connector/dist/blg-connector-linux-amd64 \
  connector/dist/blg-connector-linux-arm64 \
  connector/dist/blg-connector-linux-arm
gh release view v0.18.0 --json assets --jq '.assets[].name'
```
Expected: release URL printed; all 6 asset names listed.

---

## Notes for the implementer

- **No web-app rebuild needed.** F35 touches only the connector script + docs; the Docker stack (backend/frontend) is unchanged, so `tools/rebuild.sh` is not required for this feature.
- **Task 2 is verification, not code** — if it surfaces a bug, fix it back in Task 1's script and re-run Task 2 before moving on.
- If CUPS cannot be installed on the server, report Task 2 as BLOCKED (with the exact failure) rather than skipping verification silently — the script/docs can still ship, but say plainly it went out Linux-unverified.
