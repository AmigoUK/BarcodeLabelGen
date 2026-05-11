# BarcodeLabelGen

Web-based label editor and PDF batch generator for non-technical office users.

> Status: 🚧 **MVP Specification Phase** — implementation starting from Sprint 0.
> Project specification: [`docs/PROJECT.md`](docs/PROJECT.md)

## What it does

- **Online label editor** — Canva-like drag&drop interface (text, images, barcodes, dynamic fields)
- **Barcodes** — EAN-13, EAN-14, EAN-128, GTIN, Code 128, QR (with checksum validation)
- **Batch PDF from spreadsheet** — upload XLS/CSV, map columns to dynamic fields, generate up to 1000 unique labels in one PDF
- **Template catalog** — personal & shared templates, categories, tags, search
- **Multilingual UI** — Polish + English from day one
- **Label formats** — A4, A5, A6, common Zebra sizes (4×6", 4×4", 3×2", 2×1"), custom mm

## Target user

Non-technical office worker who currently has no way to mass-print unique labels from a spreadsheet without expensive desktop software.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + react-konva + TailwindCSS |
| Backend | Python 3.12 + Flask 3 + uv + SQLAlchemy 2 + ReportLab + treepoem |
| Database | PostgreSQL 16 |
| Cache/Sessions | Redis 7 |
| Infrastructure | Docker + Docker Compose + nginx |
| Deployment | Linux host (`HOST`) via Tailscale Serve |

## Access (production)

- **URL**: `https://HOST.TAILNET.ts.net:18003`
- **Network**: Tailscale tailnet only (`TAILNET`) — not exposed publicly
- **TLS**: auto-managed by Tailscale (Let's Encrypt)

## Development

> ⏳ Project skeleton not yet scaffolded. See [`docs/PROJECT.md` §13.1](docs/PROJECT.md#131-roadmap-implementacyjny-kolejność-dla-agentów-kodujących) for the implementation roadmap (Sprint 0–6).

Once scaffolded:

```bash
# Development (hot-reload Flask + Vite dev server)
docker compose -f compose.dev.yml up

# Production (built static frontend + Gunicorn)
docker compose up -d

# Expose via Tailscale (one-time, after first start)
tailscale serve --bg --https=18003 http://127.0.0.1:18003
```

## Project structure (planned)

```
BarcodeLabelGen/
├── backend/               # Flask API (Python 3.12 + uv)
│   ├── app/
│   ├── tests/
│   └── pyproject.toml
├── frontend/              # React SPA (Vite + TS)
│   ├── src/
│   ├── tests/
│   └── package.json
├── docker/
│   ├── nginx.conf
│   └── Dockerfile.web
├── docs/
│   └── PROJECT.md         # Full project specification
├── compose.yml            # Production docker-compose
├── compose.dev.yml        # Development docker-compose
└── README.md
```

## License

GPL-3.0 — see [`LICENSE`](LICENSE).
