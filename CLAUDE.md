# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeeTimeBot is a Python automation bot that books tee times at Cypress Lake Country Club via their Clubhouse Online portal. It runs as a scheduled AWS Lambda function (every Saturday at 6:00 AM ET), using Playwright for browser automation and Google Sheets for booking configuration.

## Commands

### Run locally
```bash
python clubhouse_bot.py                  # Run with browser visible
python clubhouse_bot.py --headless       # Run headless
python clubhouse_bot.py --keep-open      # Keep browser open after completion
```

### Docker
```bash
docker build -t teetimebot:latest .
docker run -e CLUBHOUSE_USERNAME=... -e CLUBHOUSE_PASSWORD=... teetimebot:latest
```

### CDK infrastructure (from infra/)
```bash
cd infra && npm ci
npm run build        # Compile TypeScript
npx cdk synth        # Synthesize CloudFormation template
npx cdk deploy       # Deploy stack
npx cdk diff         # Preview changes
```

### Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

## Architecture

Three Python modules with clear separation of concerns:

- **`clubhouse_bot.py`** — `ClubhouseBot` class handles all browser automation: login, navigation, date selection, tee time selection, guest booking, and form submission. Uses Playwright sync API with CSS/XPath selectors against the Clubhouse Online portal. Also contains `get_next_saturday()` utility.
- **`config_reader.py`** — Reads booking preferences from a Google Sheets spreadsheet (two tabs: "Settings" for how many times to book, "Preferences" for prioritized time/hole/transport choices). Uses `TeeTimePreference` and `TeeTimeConfig` dataclasses. Falls back to `get_default_config()` if Sheets is unavailable.
- **`lambda_handler.py`** — AWS Lambda entry point (`handler(event, context)`). Orchestrates the full booking flow: load config → login → navigate → select date → iterate preferences → book. Returns structured JSON result.

### Booking Flow

1. Load config from Google Sheets (or defaults)
2. Launch headless Chromium, login to Clubhouse Online
3. Navigate to Tee Times page
4. Click next Saturday's date on the calendar (`a.date-wrapper[data-date][data-month][data-year]`)
5. For each preference (by priority), find the tee time card (`div.tt.card[data-timeof][data-hole]`)
6. If available, click book → add guests → set holes/transport → submit reservation
7. Stop when target booking count is reached

### Infrastructure

- **`infra/`** — AWS CDK stack (TypeScript): Lambda function (Docker image, 1024MB, 180s timeout), EventBridge scheduler, ECR repository, GitHub OIDC for CI/CD
- **`.github/workflows/deploy.yml`** — CI/CD pipeline: Docker build → ECR push → CDK deploy → Lambda update
- **`Dockerfile`** — Based on `public.ecr.aws/lambda/python:3.12` with Chromium installed for Playwright

## Environment Variables

Required: `CLUBHOUSE_USERNAME`, `CLUBHOUSE_PASSWORD`
Optional: `CLUBHOUSE_URL`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS` (JSON string of service account creds)

## Code Conventions

- Python methods on `ClubhouseBot` use camelCase (`navToTeeTimes`, `isOnTeeTimesPage`)
- Page interactions follow: wait_for → fill/click → verify, with `time.sleep()` for render delays
- Formatter: Black. Linter: Flake8 (configured in devcontainer, not enforced in CI)