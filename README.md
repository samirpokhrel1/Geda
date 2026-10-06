# Parliamentary Management System — MVP

A private, party-internal web app for coordinating parliamentary work: bills and their
workflow, research, party positions, assignments, committees, meetings, questions, tasks,
documents, notifications and an audit trail. Built from the Master PRD (v0.1).

**Stack:** Python 3.9+, Flask, SQLite (single file). No Node, no external services.

## Run it

**Windows:** double-click `run.bat`
**macOS / Linux:** `./run.sh` (run `chmod +x run.sh` once)

Or manually:

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. On first run the database is created in `data/pms.db` and filled
with **fictional demo data**.

## Demo logins (password for all: `demo1234`)

| Email | Role |
|---|---|
| admin@pms.test | Super Admin |
| partyadmin@pms.test | Party Admin |
| coordinator@pms.test | Parliamentary Coordinator |
| researcher@pms.test / researcher2@pms.test | Researcher |
| mp1@pms.test / mp2@pms.test | Parliamentarian / MP |

Try logging in as different roles: researchers and MPs only see bills assigned to them.

## What's included (maps to PRD §6 and §17)

| PRD module | Where |
|---|---|
| Dashboard (KPIs, overdue, meetings, activity) | `/` |
| Bills: create/edit/search/filter, status, priority | `/bills` |
| Bill Workspace: Overview, Research, Position, Assignments, Documents, Tasks, Timeline | `/bills/<id>` |
| Committees, members, related bills and meetings | `/committees` |
| Parliamentary Questions | `/questions` |
| Meetings (agenda, decisions, minutes) | `/meetings` |
| Tasks | `/tasks` |
| Documents (upload, category, access level, secure download) | `/documents` |
| Notifications (assignments, status, position, meetings, deadlines) | `/notifications` |
| Audit trail (Super Admin / Party Admin) | `/audit` |
| Users + demo reset (Super Admin) | `/users` |

## Permissions

| Action | Super/Party Admin, Coordinator | Researcher | MP |
|---|---|---|---|
| See all bills | yes | assigned only | assigned only |
| Create/edit bills, change status, assign, record party position | yes | no | no |
| Add research notes | yes | yes (assigned bills) | no |
| File parliamentary questions | yes | no | own only |
| Create committees/meetings | yes | no | no |
| Download "restricted" documents | yes | no | no |
| Audit trail | Super/Party Admin | no | no |
| Manage users, reset demo data | Super Admin | no | no |

All checks are enforced **on the server** (`PERMS` table and `bill_scope()` in `app.py`), not just
hidden in the UI.

## Security built in

Hashed passwords, server-side sessions cookies (HttpOnly, SameSite=Lax), CSRF tokens on every POST,
parameterised SQL only, input validation, upload allow-list + random stored file names + size limit,
auth on every page, audit log for important actions, open-redirect protection.

## Before real use (not done in this MVP)

- Put it behind **HTTPS** (a reverse proxy such as Nginx/Caddy) and run with a production server,
  e.g. `pip install waitress` then `waitress-serve --port 8000 app:app`.
- Set a fixed secret: `PMS_SECRET_KEY=<long random string>` (otherwise one is generated in `data/secret.key`).
- Hide the demo-accounts box: `PMS_DEMO=0`, and **delete or change all demo users/passwords**.
- Add login rate-limiting / lockout and password-reset flow.
- Back up `data/pms.db` and `data/uploads/`. Keep demo and production data in separate folders
  (`PMS_DATA_DIR=/path/to/dir`).
- SQLite suits a small team. Moving to PostgreSQL/Supabase (as in the PRD) is the natural next step
  for multi-user scale; the schema in `app.py` maps 1:1 to PRD §9 (roles are a code constant here
  rather than a table).

## Settings (environment variables)

`PMS_HOST` (127.0.0.1) · `PMS_PORT` (5000) · `PMS_DATA_DIR` (./data) · `PMS_SECRET_KEY` ·
`PMS_DEMO` (1) · `PMS_DEMO_PASSWORD` (demo1234) · `PMS_DEBUG` (0)

Copy `.env.example` as a reference when configuring the environment. Flask does not
load `.env` automatically; export variables in your shell or configure them in your
deployment environment. Leave `PMS_SECRET_KEY` unset for a local development key, and
set a securely generated value for a persistent deployment.

## English and Nepali

Use the **नेपाली / English** language switch in the sidebar (or on the login page).
The guest preference is kept in the browser session; a signed-in user's preference is
saved on their user profile and restored on their next login. Translation messages live
in `static/locales/en.json` and `static/locales/ne.json`; database values and user-entered
content remain unchanged when switching languages. The interface uses UTF-8 throughout.

## Commands

```bash
python app.py --reset   # wipe everything and reload demo data
python test_app.py      # 90+ automated checks incl. role permissions
python test_i18n.py     # English/Nepali switching and preference persistence
```

## Files

```
app.py          routes, permissions, schema
seed.py         fictional demo data
templates/      HTML pages (Jinja2)
static/style.css
static/i18n.js  locale loader and interface translation
static/locales/ centralized English and Nepali message catalogs
test_app.py     automated tests
```

## Next steps from the PRD roadmap

Calendar view for meetings, e-mail notifications, bill-to-bill links, exportable reports (v0.5+),
then PostgreSQL + row-level security and SSO for the pilot (v0.6–v1.0).
