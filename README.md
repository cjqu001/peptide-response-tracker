# Peptide Response Tracker

A small self-hosted web app for logging daily habits, peptide doses, and wellness measures. It shows a year grid, streaks, totals, and trend charts, and it exports everything to CSV. It runs locally in Docker and stores all data in one SQLite file.

## Purpose: peptide response and wellness data

This tracker is being used to gather clinical evidence on peptide therapy. Each participant logs three kinds of data on the same daily timeline:

| Domain | What is logged | Example habits |
|---|---|---|
| Exposure | Peptide name, dose, and unit for each dosing day | BPC-157 (mcg), TB-500 (mg) |
| Response to treatment | Symptom and physiologic measures that the peptide is expected to change | Pain 0 to 10, resting heart rate (HR), heart rate variability (HRV) |
| Overall wellness | General health behaviors and self-rated wellbeing | Sleep hours, energy 1 to 10, water, walking minutes |

Because dose and outcome share one date column, the CSV export gives a ready per-person time series. That supports within-person (n-of-1) comparisons, such as baseline vs. on-treatment periods, and pooled descriptive summaries across participants.

### Evidence limitations

The data from this tool is **observational and self-reported**. Interpret it with these limits in mind:

- **No control group, blinding, or randomization.** Changes over time may reflect placebo response, regression to the mean, natural history, or co-interventions.
- **Measures are not validated instruments.** Scores such as "Pain 0 to 10" are user-defined. For research, use established scales (for example, a numeric rating scale for pain or PROMIS short forms) and record them consistently.
- **Adherence and dose accuracy are unverified.** Entries reflect what the participant reports.
- **Regulatory status.** Many research peptides, including BPC-157 and TB-500, are not approved by the U.S. Food and Drug Administration (FDA) for human use. Logging use does not imply safety or efficacy.

### Before using it for research

Collecting health data from other people for research is human subjects research. Before doing so:

1. Obtain institutional review board (IRB) approval or a formal exemption determination.
2. Obtain informed consent from each participant.
3. Keep data de-identified. Use initials or study codes as profile names, never full names or medical record numbers.
4. Keep the database off the internet. The app has **no login and no encryption** and is not HIPAA (Health Insurance Portability and Accountability Act) compliant. Each participant should run their own local copy and share only the exported CSV through an approved channel.
5. Record any adverse events through the channel your protocol specifies, not only in the tracker.

## Live demo

Try the interface with sample data at **https://cjqu001.github.io/peptide-response-tracker/**. The demo runs entirely in the browser and saves nothing. It opens on the Example profile, which shows peptide doses alongside a response journal. To rebuild it after changing the UI, run `python tools/build_static_demo.py`.

## Features

- **Habit types:** Number (adds up through the day), Checkbox (done / missed / blank), Measurement (one decimal reading per day), and Dose (decimal amount with a unit such as mg, mcg, or units).
- **Year grid** with streaks, daily targets, and per-habit colors.
- **Profiles:** three named slots plus an Example profile. A profile is a view filter, not a login.
- **Example profile:** two weeks of made-up data, including peptide doses and a response journal, to show how the grid and charts work.
- **CSV export:** one row per date, one column per habit, UTF-8 with BOM so Excel opens it cleanly.
- **Archive and restore** habits without losing their logs.

## Stack

All components are free and open source with no paid tiers.

| Layer | Tool |
|---|---|
| Web framework | [Flask](https://flask.palletsprojects.com/) |
| Server | [waitress](https://docs.pylonsproject.org/projects/waitress/) |
| Database | SQLite (Python standard library `sqlite3`) |
| Packaging | [Docker Engine](https://docs.docker.com/engine/) with Docker Compose |

## Quick start

With Docker Engine installed (on Windows, use Docker Engine inside WSL2 rather than Docker Desktop):

```bash
git clone <this-repo-url> ~/habit_tracker
cd ~/habit_tracker
mkdir -p data
docker compose up -d --build
```

Open http://localhost:5055.

Without Docker:

```bash
pip install -r requirements.txt
python app.py
```

A full beginner walkthrough for Windows is in [docs/SETUP_CHECKLIST.md](docs/SETUP_CHECKLIST.md).

## Data and backups

All data lives in `data/habits.db`. Back up that file regularly, and never edit it while the container is running:

```bash
cp data/habits.db ~/habits_backup_$(date +%Y%m%d).db
```

The `.gitignore` excludes `*.db` files so participant data is never committed to this repository.

## Everyday commands

| Task | Command |
|---|---|
| Start or apply changes | `docker compose up -d` |
| Stop (data kept) | `docker compose down` |
| Restart after editing code | `docker restart habit-tracker` |
| Rebuild after changing `requirements.txt` or `Dockerfile` | `docker compose up -d --build` |
| Logs | `docker compose logs -f` |

## API

The page calls a small JSON API in `app.py`:

| Method and path | Purpose |
|---|---|
| `GET /api/habits` | List active habits |
| `POST /api/habits` | Create a habit |
| `POST /api/log` | Add to a day's value |
| `POST /api/day` | Set a day's value or mark it missed |
| `GET /api/year/<year>` | Grid data for a year |
| `GET /api/stats` | Streaks and totals |
| `GET /api/export/csv?profile=<code>` | CSV export for one profile |

## Repository layout

```
app.py               Flask app and JSON API
serve.py             waitress entry point used in Docker
templates/index.html Entire user interface
requirements.txt     flask, waitress
Dockerfile           Container image
docker-compose.yml   Port 5055, data volume, restart policy
data/                SQLite database (created on first start; not committed)
docs/                Setup checklist, assistant notes, and the static demo (index.html)
tools/               Demo builder and in-browser mock API
```

## Disclaimer

This software is provided for personal tracking and research data collection. It is not a medical device and does not provide medical advice. Decisions about peptide or any other therapy belong with a licensed clinician.
