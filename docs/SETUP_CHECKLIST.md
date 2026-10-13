# Habit Tracker: setup checklist (Windows PC)

Tick each box in order. Estimated time: 45 to 60 minutes, including one reboot.

## A. Downloads and installs (all free, no paid tiers)
- [ ] **Windows 10 (22H2) or Windows 11**, fully updated
- [ ] **WSL2 + Ubuntu**: built into Windows, installed with one command (step C1)
- [ ] **Docker Engine**: installed inside Ubuntu from https://docs.docker.com/engine/install/ubuntu/
- [ ] **Habit tracker kit** (`habit_tracker_friend_kit.zip` from Tio), unzipped to `C:\Users\<you>\Downloads\habit_tracker_friend_kit`
- [ ] **Do NOT install** Docker Desktop (it has paid tiers)

## B. Things you will type in or choose
| Prompt | What to enter | Write it down? |
|---|---|---|
| Ubuntu username (first launch) | Short lowercase name, e.g. `alex` | Yes |
| Ubuntu password | Any password; used for `sudo` | Yes, store safely |
| Folder for the app | `~/habit_tracker` (keep this) | No |
| Port | `5055` (already set in the compose file) | No |
| Profile name | Double-click a "Name here" button at the top; type a name or initials | No |
| Remove a name | Double-click the name, clear the box, press OK (back to "Name here") | No |
| Dose habit (peptides) | New habit, type **Dose**, unit `mg`, `mcg`, or `units`; then type the amount in the day's cell (e.g. `0.25`) | No |
| Habits | Name, unit (e.g. `min`, `glasses`), daily target, type (number or checkbox) | No |

## C. Commands, in order
**C1. Install WSL2** (PowerShell, Run as Administrator)
- [ ] Press the Windows key, type `PowerShell`, right-click **Windows PowerShell**, choose **Run as administrator**, click **Yes**
- [ ] `wsl --install`
- [ ] Reboot. Ubuntu opens and asks for the username and password from table B.

**C2. Install Docker Engine** (Ubuntu window: Windows key, type `Ubuntu`, open it)
- [ ] `curl -fsSL https://get.docker.com -o get-docker.sh`
- [ ] `sudo sh get-docker.sh`
- [ ] `sudo usermod -aG docker $USER`, then close Ubuntu and reopen it
- [ ] `docker run hello-world` prints "Hello from Docker!"

**C3. Copy the kit into Linux** (Ubuntu window; replace `<you>` with your Windows username)
- [ ] `cp -r /mnt/c/Users/<you>/Downloads/habit_tracker_friend_kit/habit_tracker ~/habit_tracker`
- [ ] `mkdir -p ~/habit_tracker/data`
- [ ] `ls ~/habit_tracker` shows `app.py  data  docker-compose.yml  Dockerfile  requirements.txt  serve.py  templates`

**C4. Build and start**
- [ ] `cd ~/habit_tracker && docker compose up -d --build`
- [ ] `docker ps` shows `habit-tracker` with status `Up`

**C5. Use it**
- [ ] Open `http://localhost:5055` in a Windows browser
- [ ] Click **Example** to see sample habits and how the grid looks
- [ ] Click a **Name here** button, double-click it to enter your name or initials
- [ ] Add one habit, log a value, refresh the page, and check the value is still there
- [ ] `ls ~/habit_tracker/data` shows `habits.db`

## D. After setup
- [ ] Weekly backup: `cp ~/habit_tracker/data/habits.db /mnt/c/Users/<you>/Documents/habits_backup_$(date +%Y%m%d).db`
- [ ] Bookmark `http://localhost:5055`
- [ ] Remember: open Ubuntu first if the page will not load

## E. If something fails
| Symptom | Likely cause | Fix |
|---|---|---|
| `permission denied ... docker.sock` | Not in the docker group yet | Close and reopen Ubuntu (after C2 step 3) |
| `Cannot connect to the Docker daemon` | Docker not started | `sudo service docker start` |
| Page will not load | WSL shut down, or container stopped | Open Ubuntu, then `docker ps`; then `docker compose up -d` |
| `port is already allocated` | Something else uses 5055 | Change the left side of `"5055:5055"` (e.g. `"5056:5055"`) |
| Edits do not appear | No restart | `docker restart habit-tracker` |
