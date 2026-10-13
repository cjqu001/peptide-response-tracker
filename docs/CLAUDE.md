# Habit Tracker: setup handoff for Claude

Read this file first in every session. Written on 2026-10-11, based on a
working habit tracker on a Synology NAS. This version is for a Windows PC.

## Who you are helping
- A beginner setting up their first self-hosted app. The goal is **understanding**, not copy and paste.
- Explain each step in 1 to 3 plain sentences: what it does and why.
- Do one step at a time. Confirm it works before moving on.
- Ask before deleting, overwriting, or exposing anything to the internet.

## What the app is
- A small web app for tracking daily habits as numbers or checkboxes, with a year grid, streaks, and CSV export.
- Built with Python **Flask** (a web framework) and **SQLite** (a database stored in one file).
- **waitress** serves the app (`serve.py`). **Docker** packages it so it runs the same on any machine.
- It is opened in a browser at `http://localhost:5055`.

## Hard rules
1. Use only 100% free, open-source software, with no freemium or paid tiers. **Do not install Docker Desktop**, because it has paid tiers. Use Docker Engine inside WSL2 instead.
2. Keep it local. Do not open router ports or expose it to the internet. The app has **no login**.
3. All data is in `data/habits.db`. Back up that one file. Never delete the `data/` folder.
4. Keep a log in `project_log.md` in the app folder. Add one dated entry per session.

## Files in the kit
| File | Purpose |
|---|---|
| `app.py` | The app: web pages plus the API (the URLs the page calls to save data) |
| `serve.py` | Starts the app under waitress on port 5055 |
| `templates/` | The HTML page: `index.html` (the whole tracker UI) |
| `requirements.txt` | Python packages: `flask`, `waitress` |
| `Dockerfile` | Recipe for building the container image |
| `docker-compose.yml` | Runs the container: port, data folder, restart policy |
| `data/` | Empty at first. `habits.db` is created on the first start. |

## Build order (do not skip ahead)
1. **WSL2.** Run `wsl --install` in PowerShell as Administrator, then reboot. This gives Windows a real Linux (Ubuntu).
2. **Docker Engine in Ubuntu.** Use the official script from https://docs.docker.com/engine/install/ubuntu/ and add the user to the `docker` group. Verify with `docker run hello-world`.
3. **Copy the kit into Linux**, at `~/habit_tracker`. Do not run it from `/mnt/c/...`. Files on the Windows side are slow and cause permission errors.
4. **Start it.** Run `cd ~/habit_tracker && docker compose up -d --build`. Open `http://localhost:5055`.
5. **Add habits and test.** Log a value, refresh the page, and confirm the value is still there.
6. **Backup.** Copy `~/habit_tracker/data/habits.db` to a Windows folder each week.

## How changes work
- `app.py`, `serve.py`, and `templates/` are mounted read-only into the container, so a code edit only needs a restart: `docker restart habit-tracker`.
- A change to `requirements.txt` or `Dockerfile` needs a rebuild: `docker compose up -d --build`.
- Flask does not hot-reload, so a restart is always required after an edit.

## Everyday commands (run in `~/habit_tracker`)
| Task | Command |
|---|---|
| Start or apply changes | `docker compose up -d` |
| Stop | `docker compose down` (data is kept) |
| Restart after editing code | `docker restart habit-tracker` |
| Logs | `docker compose logs -f` |
| Is it running? | `docker ps` |

## Habit types
| Type | Use for | How a day is entered |
|---|---|---|
| Number | Reps, glasses, minutes (adds up) | Whole number; Quick Log adds to the day |
| Checkbox | Did it / did not | Click: tick, then X, then blank |
| Measurement | Weight, waist | One decimal reading per day |
| Dose | Peptides, medications | One decimal amount per day with a unit (mg, mcg, units). Stored as a measurement, so totals show the **average dose on dosing days**. Two doses in one day: enter the day's sum. |

## Known limits (explain these, do not hide them)
- WSL shuts down shortly after the last Ubuntu window closes, and the app stops with it. Open Ubuntu to bring it back.
- From a phone or another PC, `localhost` will not work. LAN access needs extra WSL network setup. Leave it out of scope until the basics work.
- Profiles: three "Name here" buttons plus "Example". Each is a separate habit list (e.g. one per person). Double-click a "Name here" button to type a name or initials; double-click again, clear the box, and press OK to remove the name. "Example" holds made-up demo data (2 weeks): water, walk, read, vitamin, BPC-157 and TB-500 doses, and a response journal (sleep, resting HR, HRV, energy, pain). Keep it as a reference for how habits, checkboxes, and the grid work. A profile is a view filter, not a login.

## Lessons from the original setup
- A missing bind-mount folder breaks the container quietly. Check that `data/` exists before `up`.
- Back up `habits.db` before any code change. Keep dated copies such as `habits_backup_YYYYMMDD.db`.
- Edit code with a plain text editor (Notepad works). Never edit `habits.db` while the container is running.
