# rostersync

Convert PDF shift rosters to calendar (`.ics`) files.

Built for **Ambassador Theatres (國賓影城) branch daily rosters** — one page per day listing all staff with start/end times. Supports both digital PDFs (text layer) and scanned PDFs (vision model).

## Features

- **Hybrid extraction**: text-layer PDFs via `pdfplumber`, scanned PDFs via pluggable vision API (Gemini first)
- **Hours checksum validation**: compares computed duration against the roster's 時數 column
- **Cross-day shift detection**: infers overnight shifts when end < start
- **Employee filtering**: pick one person and optionally infer days off
- **ICS export**: RFC 5545 with Asia/Taipei timezone, UTF-8 line folding

## Install

```bash
git clone https://github.com/jxtssn/rostersync.git
cd rostersync
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` for scanned PDFs.

## Usage

```bash
# Convert one employee's shifts to calendar
rostersync convert roster.pdf --employee Jetson -o jetson.ics

# Also write JSON
rostersync convert roster.pdf --employee Jetson --also-json

# Extract full roster (all employees) to JSON
rostersync extract roster.pdf --json roster.json

# Inspect PDF without writing output
rostersync inspect roster.pdf
```

### Options

| Flag | Description |
|------|-------------|
| `--employee` / `-e` | Employee nickname |
| `--employee-id` | Employee ID (員工代號) |
| `--output` / `-o` | Output `.ics` path |
| `--provider` | Vision provider (`gemini`) |
| `--model` | Vision model override |
| `--strict` | Fail on validation errors |
| `--no-infer-days-off` | Skip inferring OFF for missing days |
| `--cache-dir` | Cache vision responses by page hash |
| `--also-json` | Also write JSON alongside ICS |

## Architecture

```
PDF → probe (text layer?)
  ├─ yes → pdfplumber table extraction
  └─ no  → pypdfium2 render → vision model → cached JSON
       → validate (hours checksum)
       → filter (employee + inferred days off)
       → .ics / .json
```

## Development

```bash
pytest
```

## Publish to GitHub

This repo is initialized locally. To push to GitHub:

1. Create an empty repository named `rostersync` on GitHub.
2. Run:

```bash
git remote add origin https://github.com/<your-username>/rostersync.git
git push -u origin main
```

Install [GitHub CLI](https://cli.github.com/) for one-command setup:

```bash
gh repo create rostersync --public --source=. --remote=origin --push
```

## Privacy

Real roster PDFs contain all staff names and IDs. Do **not** commit PDFs to the repository. Tests use anonymized JSON fixtures only.

## License

MIT
