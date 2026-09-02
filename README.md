# twoshiftly (2shiftly)

Convert **scanned** PDF shift rosters to calendar (`.ics`) files — **fully offline**, no API keys.

Built for **Ambassador Theatres (國賓影城) branch daily rosters** using local OCR (RapidOCR) and fixed layout rules.

## Quick start (Windows)

```powershell
cd twoshiftly
.\run.ps1 convert your-roster.pdf
```

`run.ps1` / `run.bat` will:
1. Auto-install the package if needed
2. Run via `py -m twoshiftly.cli` — **no PATH setup**
3. OCR each page locally (first run downloads ~10MB ONNX models)
4. Prompt you to pick an employee → write `.ics`

## Features

- **100% offline** — no Gemini, no API key, no network after model download
- **Interactive employee picker** — omit `--employee` and choose from a list
- **Hours checksum validation** — `--strict` compares 時數 column
- **Cross-day shift detection** — overnight shifts inferred automatically
- **ICS export** — Asia/Taipei timezone, RFC 5545

## Install (manual)

```bash
pip install -e ".[dev]"
```

## Usage

```powershell
# Interactive
.\run.ps1 convert roster.pdf

# Specify employee
.\run.ps1 convert roster.pdf --employee Jetson -o jetson.ics --strict

# Extract all employees to JSON
.\run.ps1 extract roster.pdf --json roster.json

# Inspect
.\run.ps1 inspect roster.pdf
```

Equivalent:

```bash
py -m twoshiftly.cli convert roster.pdf --employee Jetson
twoshiftly convert roster.pdf --employee Jetson   # if on PATH
```

## Architecture

```
PDF (scan) → pypdfium2 render (2480px)
          → RapidOCR
          → Ambassador layout parser
          → validate (hours checksum)
          → filter employee (+ infer days off)
          → .ics / .json
```

Cache: `.twoshiftly/cache/` and `.twoshiftly/render/` next to the PDF.

## Development

```bash
pytest
```

## Supported format

Currently calibrated for **國賓影城八德分公司** daily scanned rosters (one page per day, all staff listed).

## Privacy

Do not commit real roster PDFs. Tests use anonymized JSON fixtures.

## License

MIT
