"""Parliamentary Management System for Nepal Political Parties (संसदीय दलको कार्यालय व्यवस्थापन प्रणाली).

Supports:
- Federal Parliament: House of Representatives (प्रतिनिधि सभा) & National Assembly (राष्ट्रिय सभा)
- 7 Province Assemblies (प्रदेश सभाहरु): Koshi, Madhesh, Bagmati, Gandaki, Lumbini, Karnali, Sudurpashchim
- Party Samsadiya Dal Office (संसदीय दलको कार्यालय):
  * Whips & Party Directives (Political Parties Act, 2073 Sec 28 / राजनीतिक दल सम्बन्धी ऐन २०७३)
  * Floor Speaker Roster Management (Zero Hour, Special Hour, Bill Deliberation)
  * Samsadiya Dal Meetings, Attendance Roll-Call & Decision Minutes
  * MP Profiles, PR Clusters, Districts & Committee Memberships
  * MP Leave & Absence Monitoring (Constitution of Nepal Art. 89(d) 10-meeting threshold)
  * Bill Amendments & Party Positions
"""
import os
import sys
import uuid
import sqlite3
import secrets
import datetime as dt
from functools import wraps

from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, flash, abort, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("PMS_DATA_DIR", os.path.join(BASE, "data"))
DB_PATH = os.path.join(DATA, "pms.db")
UPLOADS = os.path.join(DATA, "uploads")
os.makedirs(UPLOADS, exist_ok=True)

# ----------------------------------------------------------------- constants
ROLES = {
    "super_admin": "Super Admin (प्रणाली प्रशासक)",
    "party_admin": "Party Central Admin (पार्टी केन्द्र)",
    "pp_leader": "PP Leader (संसदीय दलको नेता)",
    "chief_whip": "Chief Whip (प्रमुख सचेतक)",
    "whip": "Whip (सचेतक)",
    "coordinator": "Samsadiya Dal Secretary (संसदीय दल कार्यालय सचिव)",
    "researcher": "Policy Analyst / Researcher (अनुसन्धानकर्ता)",
    "mp": "Parliamentarian / MP (माननीय सांसद)",
}
STAFF = {"super_admin", "party_admin", "coordinator", "pp_leader", "chief_whip", "whip"}
WHIPS = {"super_admin", "party_admin", "coordinator", "chief_whip", "whip"}

STATUSES = ["Draft", "New", "Under Review", "Researching", "Committee",
            "Party Discussion", "Position Decided", "Parliamentary Action",
            "Follow-up", "Closed"]
PRIORITIES = ["Low", "Medium", "High"]
CATEGORIES = ["Information Technology", "Finance & Economy", "Health",
              "Education", "Energy & Environment", "Law & Justice",
              "Agriculture", "Infrastructure", "Governance", "Other"]
POSITIONS = ["Pending", "Support", "Support with amendments", "Oppose",
             "No position"]
Q_STATUSES = ["Draft", "Submitted", "Answered", "Follow-up", "Closed"]
TASK_STATUSES = ["Open", "In Progress", "Done"]
MEETING_STATUSES = ["Scheduled", "Completed", "Cancelled"]
DOC_CATEGORIES = ["Bill Text", "Research Brief", "Minutes", "Correspondence",
                  "Position Paper", "Whip Notice", "Other"]

HOUSES = [
    "House of Representatives",
    "National Assembly",
    "Koshi Province Assembly",
    "Madhesh Province Assembly",
    "Bagmati Province Assembly",
    "Gandaki Province Assembly",
    "Lumbini Province Assembly",
    "Karnali Province Assembly",
    "Sudurpashchim Province Assembly",
]

HOUSE_LABELS = {
    "House of Representatives": "House of Representatives (प्रतिनिधि सभा)",
    "National Assembly": "National Assembly (राष्ट्रिय सभा)",
    "Koshi Province Assembly": "Koshi Province Assembly (कोशी प्रदेश सभा)",
    "Madhesh Province Assembly": "Madhesh Province Assembly (मधेश प्रदेश सभा)",
    "Bagmati Province Assembly": "Bagmati Province Assembly (बागमती प्रदेश सभा)",
    "Gandaki Province Assembly": "Gandaki Province Assembly (गण्डकी प्रदेश सभा)",
    "Lumbini Province Assembly": "Lumbini Province Assembly (लुम्बिनी प्रदेश सभा)",
    "Karnali Province Assembly": "Karnali Province Assembly (कर्णाली प्रदेश सभा)",
    "Sudurpashchim Province Assembly": "Sudurpashchim Province Assembly (सुदूरपश्चिम प्रदेश सभा)",
}

PROVINCES = [
    "Federal",
    "Koshi",
    "Madhesh",
    "Bagmati",
    "Gandaki",
    "Lumbini",
    "Karnali",
    "Sudurpashchim",
]

ELECTION_TYPES = ["FPTP", "PR", "Nominated"]
ELECTION_LABELS = {
    "FPTP": "FPTP (प्रत्यक्ष निर्वाचन)",
    "PR": "PR (समानुपातिक)",
    "Nominated": "Nominated (मनोनीत)",
}

PR_CLUSTERS = [
    "None / Direct",
    "Khas Arya",
    "Aadibasi Janajati",
    "Madhesi",
    "Dalit",
    "Tharu",
    "Muslim",
    "Disability",
    "Backward Region",
]
PR_CLUSTER_LABELS = {
    "None / Direct": "None / Direct (प्रत्यक्ष / अन्य)",
    "Khas Arya": "Khas Arya (खस आर्य)",
    "Aadibasi Janajati": "Aadibasi Janajati (आदिवासी जनजाति)",
    "Madhesi": "Madhesi (मधेशी)",
    "Dalit": "Dalit (दलित)",
    "Tharu": "Tharu (थारु)",
    "Muslim": "Muslim (मुस्लिम)",
    "Disability": "Disability (अपाङ्गता भएको)",
    "Backward Region": "Backward Region (पिछडिएको क्षेत्र)",
}

DAL_ROLES = [
    "Parliamentary Party Leader",
    "Deputy Leader",
    "Chief Whip",
    "Whip",
    "Member of Parliament",
]
DAL_ROLE_LABELS = {
    "Parliamentary Party Leader": "Parliamentary Party Leader (संसदीय दलको नेता)",
    "Deputy Leader": "Deputy Leader (संसदीय दलको उपनेता)",
    "Chief Whip": "Chief Whip (प्रमुख सचेतक)",
    "Whip": "Whip (सचेतक)",
    "Member of Parliament": "Member of Parliament / Assembly (सांसद)",
}

WHIP_TYPES = ["Three-line", "Two-line", "One-line"]
WHIP_TYPE_LABELS = {
    "Three-line": "Three-line Whip (३-लाइन ह्वीप: अनिवार्य उपस्थिति र मतदान)",
    "Two-line": "Two-line Whip (२-लाइन ह्वीप: अनिवार्य उपस्थिति)",
    "One-line": "One-line Whip (१-लाइन ह्वीप: साधारण निर्देशन / सल्लाह)",
}

WHIP_DIRECTIVES = ["In Favor", "Against", "Abstain", "Mandatory Attendance"]
WHIP_DIRECTIVE_LABELS = {
    "In Favor": "Vote In Favor (प्रस्ताव/विधेयकको पक्षमा मतदान)",
    "Against": "Vote Against (प्रस्ताव/विधेयकको विपक्षमा मतदान)",
    "Abstain": "Abstain (तटस्थ रहने)",
    "Mandatory Attendance": "Mandatory Attendance (अनिवार्य उपस्थिति मात्र)",
}

SESSION_TYPES = [
    "Zero Hour",
    "Special Hour",
    "Emergency Hour",
    "Bill Discussion",
    "Budget/Policy Debate",
    "Calling Attention",
    "Urgent Public Importance",
]
SESSION_TYPE_LABELS = {
    "Zero Hour": "Zero Hour (शून्य समय - १ मिनेट)",
    "Special Hour": "Special Hour (विशेष समय - ३-५ मिनेट)",
    "Emergency Hour": "Emergency Hour (आकस्मिक समय)",
    "Bill Discussion": "Bill Discussion (विधेयकमाथि छलफल)",
    "Budget/Policy Debate": "Budget / Policy Debate (बजेट तथा नीति छलफल)",
    "Calling Attention": "Calling Attention Motion (ध्यानाकर्षण प्रस्ताव)",
    "Urgent Public Importance": "Urgent Public Importance (सार्वजनिक महत्वको प्रस्ताव)",
}

LEAVE_TYPES = ["Medical", "Constituency Visit", "Official Foreign Visit", "Personal", "Other"]
LEAVE_TYPE_LABELS = {
    "Medical": "Medical / Health Post (उपचार / स्वास्थ्य आराम)",
    "Constituency Visit": "Constituency Work (निर्वाचन क्षेत्र भ्रमण / राहत)",
    "Official Foreign Visit": "Official Foreign Visit (विदेश भ्रमण)",
    "Personal": "Personal / Urgent (व्यक्तिगत / घरायसी)",
    "Other": "Other (अन्य कारण)",
}

MEETING_CATEGORIES = [
    "Samsadiya Dal Full Caucus (संसदीय दलको पूर्ण बैठक)",
    "Dal Working Committee (संसदीय दल कार्यसमिति)",
    "House of Representatives Caucus (प्रतिनिधि सभा दल बैठक)",
    "National Assembly Caucus (राष्ट्रिय सभा दल बैठक)",
    "Province Assembly Caucus (प्रदेश सभा दल बैठक)",
    "Bill Strategy Discussion (विधेयक रणनीति बैठक)",
    "Committee Thematic Group (समितिगत विषयगत छलफल)",
]

SITTING_STATUSES = ["Scheduled", "Held", "Adjourned"]
SITTING_ATT_STATUSES = ["Present", "Absent", "Leave", "Official Duty"]
SITTING_ATT_LABELS = {
    "Present": "Present (उपस्थित)",
    "Absent": "Absent without notice (बिना सूचना अनुपस्थित)",
    "Leave": "On approved leave (स्वीकृत बिदा)",
    "Official Duty": "Official duty (आधिकारिक काम)",
}
LETTER_DIRECTIONS = ["Incoming", "Outgoing"]
LETTER_DIRECTION_LABELS = {
    "Incoming": "Incoming (आगत पत्र)",
    "Outgoing": "Outgoing (प्रेषित पत्र)",
}
LETTER_CATEGORIES = [
    "House Secretariat",
    "Ministry",
    "Committee",
    "Whip / Floor",
    "Constituency",
    "Party Centre",
    "Province Dal Office",
    "Other",
]
LETTER_STATUSES = ["Registered", "In Process", "Replied", "Filed"]

ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt",
               "csv", "png", "jpg", "jpeg"}

PERMS = {
    "bill.create": STAFF, "bill.edit": STAFF, "bill.assign": STAFF,
    "bill.position": STAFF, "bill.status": STAFF,
    "bill.research": STAFF | {"researcher"},
    "committee.manage": STAFF, "meeting.manage": STAFF,
    "question.create": STAFF | {"mp"},
    "audit.view": {"super_admin", "party_admin"},
    "user.manage": {"super_admin"}, "demo.reset": {"super_admin"},
    # Samsadiya Dal specific permissions:
    "member.manage": STAFF,
    "sitting.manage": WHIPS,
    "letter.manage": STAFF,
    "whip.manage": WHIPS,
    "whip.issue": WHIPS,
    "whip.record": WHIPS,
    "roster.manage": WHIPS,
    "leave.manage": WHIPS,
    "leave.apply": STAFF | {"mp"},
    "amendment.manage": STAFF | {"mp"},
}

SCHEMA = """
CREATE TABLE users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL, role TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL);

CREATE TABLE parliamentarians(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ne TEXT, house TEXT, province TEXT,
  election_type TEXT, pr_cluster TEXT, dal_role TEXT, district TEXT, constituency TEXT,
  committee TEXT, contact TEXT, pa_name TEXT, pa_contact TEXT, capital_address TEXT,
  blood_group TEXT, bio TEXT, photo_url TEXT, status TEXT NOT NULL DEFAULT 'active',
  user_id INTEGER REFERENCES users(id));

CREATE TABLE committees(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, house TEXT, description TEXT,
  status TEXT NOT NULL DEFAULT 'active');

CREATE TABLE committee_members(
  committee_id INTEGER NOT NULL REFERENCES committees(id),
  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  role TEXT NOT NULL DEFAULT 'Member',
  PRIMARY KEY(committee_id, parliamentarian_id));

CREATE TABLE bills(
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, nepali_title TEXT, description TEXT,
  category TEXT, house TEXT DEFAULT 'House of Representatives', bill_type TEXT DEFAULT 'Government',
  status TEXT NOT NULL DEFAULT 'New', priority TEXT NOT NULL DEFAULT 'Medium',
  introduced_date TEXT, committee_id INTEGER REFERENCES committees(id),
  deadline TEXT, next_action TEXT, party_position TEXT DEFAULT 'Pending',
  decision_date TEXT, created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE bill_assignments(
  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  assignment_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  assigned_at TEXT NOT NULL);

CREATE TABLE bill_research(
  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
  researcher_id INTEGER REFERENCES users(id), summary TEXT NOT NULL,
  notes TEXT, created_at TEXT NOT NULL);

CREATE TABLE party_positions(
  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
  position TEXT NOT NULL, decision_date TEXT, decided_by TEXT, notes TEXT,
  recorded_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE parliamentary_questions(
  id INTEGER PRIMARY KEY, question TEXT NOT NULL,
  parliamentarian_id INTEGER REFERENCES parliamentarians(id),
  ministry TEXT, subject TEXT, submitted_date TEXT,
  status TEXT NOT NULL DEFAULT 'Draft', response TEXT, follow_up TEXT,
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE tasks(
  id INTEGER PRIMARY KEY, title TEXT NOT NULL,
  owner_id INTEGER REFERENCES users(id), related_type TEXT, related_id INTEGER,
  deadline TEXT, priority TEXT NOT NULL DEFAULT 'Medium',
  status TEXT NOT NULL DEFAULT 'Open', notes TEXT,
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE meetings(
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL,
  location TEXT, committee_id INTEGER REFERENCES committees(id),
  bill_id INTEGER REFERENCES bills(id), participants TEXT, agenda TEXT,
  decisions TEXT, minutes TEXT, status TEXT NOT NULL DEFAULT 'Scheduled',
  meeting_category TEXT DEFAULT 'Samsadiya Dal Meeting', house TEXT,
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE meeting_attendance(
  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  status TEXT NOT NULL DEFAULT 'Present',
  remarks TEXT,
  PRIMARY KEY(meeting_id, parliamentarian_id));

CREATE TABLE documents(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, file_path TEXT NOT NULL,
  original_name TEXT NOT NULL, category TEXT, related_type TEXT,
  related_id INTEGER, access_level TEXT NOT NULL DEFAULT 'internal',
  uploaded_by INTEGER REFERENCES users(id), uploaded_at TEXT NOT NULL);

CREATE TABLE activity_logs(
  id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, detail TEXT,
  timestamp TEXT NOT NULL);

CREATE TABLE notifications(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
  type TEXT NOT NULL, message TEXT NOT NULL, link TEXT, read_at TEXT,
  created_at TEXT NOT NULL);

CREATE TABLE whips(
  id INTEGER PRIMARY KEY, ref_no TEXT NOT NULL, title TEXT NOT NULL,
  whip_type TEXT NOT NULL, house TEXT NOT NULL, directive TEXT NOT NULL,
  voting_date TEXT NOT NULL, voting_time TEXT, bill_id INTEGER REFERENCES bills(id),
  agenda TEXT NOT NULL, legal_basis TEXT DEFAULT 'राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८',
  status TEXT NOT NULL DEFAULT 'Issued', issued_by INTEGER REFERENCES users(id),
  issued_at TEXT NOT NULL, notes TEXT);

CREATE TABLE whip_members(
  id INTEGER PRIMARY KEY, whip_id INTEGER NOT NULL REFERENCES whips(id) ON DELETE CASCADE,
  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  served_status TEXT NOT NULL DEFAULT 'Served', served_at TEXT,
  attendance_status TEXT NOT NULL DEFAULT 'Present',
  vote_cast TEXT NOT NULL DEFAULT 'Pending',
  compliance_status TEXT NOT NULL DEFAULT 'Pending',
  disciplinary_action TEXT NOT NULL DEFAULT 'None',
  remarks TEXT,
  UNIQUE(whip_id, parliamentarian_id));

CREATE TABLE speaker_rosters(
  id INTEGER PRIMARY KEY, house TEXT NOT NULL, session_date TEXT NOT NULL,
  session_type TEXT NOT NULL, parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  topic TEXT NOT NULL, allocated_minutes INTEGER NOT NULL DEFAULT 3,
  speaking_order INTEGER NOT NULL DEFAULT 1, talking_points TEXT,
  bill_id INTEGER REFERENCES bills(id), status TEXT NOT NULL DEFAULT 'Scheduled',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE mp_leaves(
  id INTEGER PRIMARY KEY, parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  leave_type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  days_count INTEGER NOT NULL, reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Approved', approved_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL);

CREATE TABLE bill_amendments(
  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
  parliamentarian_id INTEGER REFERENCES parliamentarians(id),
  section_clause TEXT NOT NULL, proposed_text TEXT NOT NULL, rationale TEXT,
  party_stance TEXT NOT NULL DEFAULT 'Endorsed',
  status TEXT NOT NULL DEFAULT 'Registered',
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL);

CREATE TABLE house_sittings(
  id INTEGER PRIMARY KEY, house TEXT NOT NULL, sitting_date TEXT NOT NULL,
  sitting_no TEXT, session_name TEXT, agenda TEXT,
  status TEXT NOT NULL DEFAULT 'Held',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE sitting_attendance(
  sitting_id INTEGER NOT NULL REFERENCES house_sittings(id) ON DELETE CASCADE,
  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
  status TEXT NOT NULL DEFAULT 'Present', remarks TEXT,
  PRIMARY KEY(sitting_id, parliamentarian_id));

CREATE TABLE office_letters(
  id INTEGER PRIMARY KEY, direction TEXT NOT NULL, ref_no TEXT NOT NULL,
  letter_date TEXT NOT NULL, subject TEXT NOT NULL, from_party TEXT,
  to_party TEXT, house TEXT, category TEXT,
  status TEXT NOT NULL DEFAULT 'Registered', notes TEXT,
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

CREATE INDEX ix_bills_status ON bills(status);
CREATE INDEX ix_tasks_owner ON tasks(owner_id);
CREATE INDEX ix_log_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX ix_notif_user ON notifications(user_id, read_at);
CREATE INDEX ix_whips_status ON whips(status);
CREATE INDEX ix_whip_members ON whip_members(whip_id, parliamentarian_id);
CREATE INDEX ix_roster_date ON speaker_rosters(session_date, house);
CREATE INDEX ix_leaves_mp ON mp_leaves(parliamentarian_id);
CREATE INDEX ix_amendments_bill ON bill_amendments(bill_id);
CREATE INDEX ix_sittings_house ON house_sittings(house, sitting_date);
CREATE INDEX ix_letters_date ON office_letters(letter_date);
"""

# ----------------------------------------------------------------- app setup
app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


def _secret():
    env = os.environ.get("PMS_SECRET_KEY")
    if env:
        return env
    path = os.path.join(DATA, "secret.key")
    if not os.path.exists(path):
        with open(path, "w") as fh:
            fh.write(secrets.token_hex(32))
    with open(path) as fh:
        return fh.read().strip()


app.secret_key = _secret()


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def today():
    return dt.date.today().isoformat()


NEP_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def nepali_digits(val):
    if val is None:
        return ""
    return str(val).translate(NEP_DIGITS)


def approx_ad_to_bs(date_str):
    """Converts YYYY-MM-DD string to an approximate Bikram Sambat (BS) date string with Nepali month."""
    if not date_str:
        return ""
    try:
        parts = date_str[:10].split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        months_nepali = [
            ("बैशाख", 1), ("जेठ", 2), ("असार", 3), ("साउन", 4),
            ("भदौ", 5), ("असोज", 6), ("कात्तिक", 7), ("मंसिर", 8),
            ("पुस", 9), ("माघ", 10), ("फागुन", 11), ("चैत", 12)
        ]
        ref_ad = dt.date(2024, 4, 13)
        cur_ad = dt.date(y, m, d)
        delta_days = (cur_ad - ref_ad).days

        bs_year = 2081
        bs_day_of_year = delta_days
        while bs_day_of_year < 0:
            bs_year -= 1
            bs_day_of_year += 365
        while bs_day_of_year >= 365:
            bs_year += 1
            bs_day_of_year -= 365

        lengths = [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30]
        bs_m = 0
        while bs_m < 12 and bs_day_of_year >= lengths[bs_m]:
            bs_day_of_year -= lengths[bs_m]
            bs_m += 1
        bs_month = min(bs_m + 1, 12)
        bs_day = bs_day_of_year + 1
        m_name = months_nepali[bs_month - 1][0]
        return f"{nepali_digits(bs_year)} {m_name} {nepali_digits(bs_day)} ({bs_year}-{bs_month:02d}-{bs_day:02d} BS)"
    except Exception:
        return date_str


# ----------------------------------------------------------------- database
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def q(sql, args=(), one=False):
    cur = db().execute(sql, args)
    return cur.fetchone() if one else cur.fetchall()


def ex(sql, args=()):
    cur = db().execute(sql, args)
    db().commit()
    return cur.lastrowid


def log(action, etype=None, eid=None, detail=""):
    uid = g.user["id"] if getattr(g, "user", None) else None
    ex("INSERT INTO activity_logs(actor_id,action,entity_type,entity_id,detail,timestamp)"
       " VALUES(?,?,?,?,?,?)", (uid, action, etype, eid, detail, now()))


def notify(user_id, ntype, message, link=None):
    if user_id is None:
        return
    if getattr(g, "user", None) and user_id == g.user["id"]:
        return
    ex("INSERT INTO notifications(user_id,type,message,link,created_at) VALUES(?,?,?,?,?)",
       (user_id, ntype, message, link, now()))


# ----------------------------------------------------------------- auth/perm
@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        u = q("SELECT * FROM users WHERE id=? AND status='active'", (uid,), one=True)
        if u:
            g.user = u
            # Authenticated preferences are authoritative, including on a new device.
            session["language"] = u["language"] if "language" in u.keys() else "en"
        else:
            session.clear()
    if request.method == "POST":
        token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("csrf"):
            abort(400, "Invalid or missing CSRF token. Reload the page and try again.")


def csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def can(perm):
    return bool(g.user) and g.user["role"] in PERMS.get(perm, set())


def is_staff():
    return bool(g.user) and g.user["role"] in STAFF


def is_whip_authority():
    return bool(g.user) and g.user["role"] in WHIPS


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not g.user:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return fn(*a, **kw)
    return wrapper


def perm_required(perm):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if not can(perm):
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject():
    unread = 0
    if g.get("user"):
        unread = q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND read_at IS NULL",
                   (g.user["id"],), one=True)["c"]
    return dict(
        csrf=csrf, can=can, is_staff=is_staff, is_whip_authority=is_whip_authority,
        ROLES=ROLES, unread=unread, STATUSES=STATUSES, PRIORITIES=PRIORITIES,
        today=today(), bs_today=approx_ad_to_bs(today()),
        HOUSES=HOUSES, HOUSE_LABELS=HOUSE_LABELS, PROVINCES=PROVINCES,
        ELECTION_TYPES=ELECTION_TYPES, ELECTION_LABELS=ELECTION_LABELS,
        PR_CLUSTERS=PR_CLUSTERS, PR_CLUSTER_LABELS=PR_CLUSTER_LABELS,
        DAL_ROLES=DAL_ROLES, DAL_ROLE_LABELS=DAL_ROLE_LABELS,
        WHIP_TYPES=WHIP_TYPES, WHIP_TYPE_LABELS=WHIP_TYPE_LABELS,
        WHIP_DIRECTIVES=WHIP_DIRECTIVES, WHIP_DIRECTIVE_LABELS=WHIP_DIRECTIVE_LABELS,
        SESSION_TYPES=SESSION_TYPES, SESSION_TYPE_LABELS=SESSION_TYPE_LABELS,
        LEAVE_TYPES=LEAVE_TYPES, LEAVE_TYPE_LABELS=LEAVE_TYPE_LABELS,
        MEETING_CATEGORIES=MEETING_CATEGORIES,
        SITTING_STATUSES=SITTING_STATUSES, SITTING_ATT_STATUSES=SITTING_ATT_STATUSES,
        SITTING_ATT_LABELS=SITTING_ATT_LABELS,
        LETTER_DIRECTIONS=LETTER_DIRECTIONS, LETTER_DIRECTION_LABELS=LETTER_DIRECTION_LABELS,
        LETTER_CATEGORIES=LETTER_CATEGORIES, LETTER_STATUSES=LETTER_STATUSES,
        language=session.get("language", "en"),
    )


@app.template_filter("slug")
def slug(s):
    return (s or "").lower().replace(" ", "-").replace("/", "-").replace("&", "and")


@app.template_filter("billno")
def billno(i):
    return "BILL-%04d" % i


@app.template_filter("fdt")
def fdt(s):
    return (s or "").replace("T", " ")[:16]


@app.template_filter("bs_date")
def filter_bs_date(s):
    return approx_ad_to_bs(s)


@app.template_filter("nep_digits")
def filter_nep_digits(s):
    return nepali_digits(s)


@app.errorhandler(403)
def e403(e):
    return render_template("error.html", code=403, msg="You do not have permission to do that."), 403


@app.errorhandler(404)
def e404(e):
    return render_template("error.html", code=404, msg="That page or record was not found."), 404


@app.errorhandler(400)
def e400(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request.")), 400


@app.errorhandler(413)
def e413(e):
    return render_template("error.html", code=413, msg="File too large (16 MB max)."), 413


# ----------------------------------------------------------------- visibility
def bill_scope(alias="b"):
    """SQL fragment restricting bills to what the current user may see."""
    if is_staff():
        return "", ()
    return (f" AND {alias}.id IN (SELECT bill_id FROM bill_assignments "
            "WHERE user_id=? AND status='active')", (g.user["id"],))


def visible_bills():
    frag, args = bill_scope()
    return q(f"SELECT b.id,b.title FROM bills b WHERE 1=1{frag} ORDER BY b.title", args)


def get_bill(bid):
    frag, args = bill_scope()
    b = q(f"SELECT b.*, c.name committee_name FROM bills b "
          f"LEFT JOIN committees c ON c.id=b.committee_id WHERE b.id=?{frag}",
          (bid,) + args, one=True)
    if not b:
        abort(404)
    return b


def assigned_users(bid):
    return [r["user_id"] for r in q(
        "SELECT user_id FROM bill_assignments WHERE bill_id=? AND status='active'", (bid,))]


def can_see_doc(d):
    if is_staff() or d["uploaded_by"] == g.user["id"]:
        return True
    if d["related_type"] == "bill" and d["access_level"] == "internal":
        frag, args = bill_scope()
        return q(f"SELECT 1 FROM bills b WHERE b.id=?{frag}", (d["related_id"],) + args,
                 one=True) is not None
    return False


# ----------------------------------------------------------------- forms
def parse(spec, form):
    vals, errs = {}, {}
    for f in spec:
        name = f["name"]
        v = (form.get(name) or "").strip()
        vals[name] = v
        if f.get("required") and not v:
            errs[name] = f"{f['label']} is required."
            continue
        if v and f.get("minlen") and len(v) < f["minlen"]:
            errs[name] = f"Must be at least {f['minlen']} characters."
            continue
        if v and f.get("choices"):
            valid = {c[0] for c in f["choices"]}
            if v not in valid:
                errs[name] = "Invalid choice."
    return vals, errs


def render_form(title, spec, vals, errs, cancel_url, submit_label="Save", sub=""):
    return render_template("form.html", title=title, spec=spec, values=vals,
                           errors=errs, back=cancel_url, submit=submit_label, sub=sub)


def opts(items, blank=None):
    out = [("", blank)] if blank else []
    return out + [(x, x) for x in items]


def committee_choices():
    return [("", "— none —")] + [(str(r["id"]), r["name"]) for r in
                                  q("SELECT id,name FROM committees ORDER BY name")]


def user_choices(role=None, blank="— unassigned —"):
    if role:
        rows = q("SELECT id,name FROM users WHERE status='active' AND role=? ORDER BY name", (role,))
    else:
        rows = q("SELECT id,name FROM users WHERE status='active' ORDER BY name")
    return [("", blank)] + [(str(r["id"]), r["name"]) for r in rows]


def mp_choices(house=None, blank="— select MP —"):
    sql = "SELECT id, name, name_ne, constituency, house FROM parliamentarians WHERE status='active'"
    args = ()
    if house:
        sql += " AND house=?"
        args = (house,)
    sql += " ORDER BY name"
    rows = q(sql, args)
    return [("", blank)] + [
        (str(r["id"]), f"{r['name']} ({r['constituency'] or r['house']})") for r in rows
    ]


def consecutive_absence_streak(pid, house=None):
    """Count consecutive Held sittings without notice (Art. 89(d)). Leave / presence breaks the streak."""
    mp = q("SELECT house FROM parliamentarians WHERE id=?", (pid,), one=True)
    if not mp:
        return 0
    house = house or mp["house"]
    sittings = q(
        "SELECT id FROM house_sittings WHERE house=? AND status='Held' ORDER BY sitting_date DESC, id DESC",
        (house,)
    )
    streak = 0
    for s in sittings:
        row = q(
            "SELECT status FROM sitting_attendance WHERE sitting_id=? AND parliamentarian_id=?",
            (s["id"], pid), one=True
        )
        st = row["status"] if row else "Absent"
        if st in ("Present", "Leave", "Official Duty"):
            break
        streak += 1
    return streak


def absence_watchlist(min_streak=3):
    out = []
    for mp in q("SELECT id, name, name_ne, house, constituency FROM parliamentarians WHERE status='active'"):
        streak = consecutive_absence_streak(mp["id"], mp["house"])
        if streak >= min_streak:
            out.append(dict(mp, streak=streak, risk="vacancy" if streak >= 10 else "watch"))
    out.sort(key=lambda r: -r["streak"])
    return out


def house_strength():
    rows = q(
        "SELECT house, COUNT(*) c FROM parliamentarians WHERE status='active' GROUP BY house"
    )
    counts = {r["house"]: r["c"] for r in rows}
    return [(h, counts.get(h, 0)) for h in HOUSES]


# ----------------------------------------------------------------- auth routes
def safe_next(n):
    return n if n and n.startswith("/") and not n.startswith("//") else url_for("dashboard")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        u = q("SELECT * FROM users WHERE email=? AND status='active'", (email,), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password") or ""):
            session.clear()
            session["uid"] = u["id"]
            session["language"] = u["language"] if "language" in u.keys() else "en"
            g.user = u
            log("login", "user", u["id"])
            return redirect(safe_next(request.args.get("next")))
        error = "Invalid email or password."
    demo = []
    if os.environ.get("PMS_DEMO", "1") != "0":
        demo = q("SELECT name,email,role FROM users ORDER BY id")
    return render_template("login.html", error=error, demo=demo)


@app.post("/language/<language>")
def set_language(language):
    """Set a UI locale for this browser and, when signed in, save it to the profile."""
    if language not in {"en", "ne"}:
        abort(404)
    session["language"] = language
    if g.user:
        ex("UPDATE users SET language=? WHERE id=?", (language, g.user["id"]))
        g.user = q("SELECT * FROM users WHERE id=?", (g.user["id"],), one=True)
        log("changed language preference", "user", g.user["id"], language)
    return redirect(safe_next(request.form.get("next")))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    log("logout", "user", g.user["id"])
    preferred_language = session.get("language", "en")
    session.clear()
    session["language"] = preferred_language
    return redirect(url_for("login"))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    spec = [dict(name="current", label="Current password", type="password", required=True),
            dict(name="new", label="New password", type="password", required=True,
                 minlen=8, help="At least 8 characters")]
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs and not check_password_hash(g.user["password_hash"], request.form["current"]):
            errs["current"] = "Incorrect password"
        if not errs:
            ex("UPDATE users SET password_hash=? WHERE id=?",
               (generate_password_hash(request.form["new"]), g.user["id"]))
            log("changed password", "user", g.user["id"])
            flash("Password updated.", "ok")
            return redirect(url_for("dashboard"))
        vals = {}
    return render_form("My account", spec, vals, errs, url_for("dashboard"),
                       "Change password", sub=f"{g.user['name']} · {ROLES.get(g.user['role'], g.user['role'])}")


# ----------------------------------------------------------------- dashboard
def deadline_notices(uid):
    soon = (dt.date.today() + dt.timedelta(days=2)).isoformat()
    items = [(f"Task due {r['deadline']}: {r['title']}", url_for("tasks_list")) for r in q(
        "SELECT title,deadline FROM tasks WHERE owner_id=? AND status!='Done' "
        "AND deadline IS NOT NULL AND deadline<=?", (uid, soon))]
    items += [(f"Bill deadline {r['deadline']}: {r['title']}", url_for("bill_view", bid=r["id"]))
              for r in q("SELECT b.id,b.title,b.deadline FROM bills b JOIN bill_assignments a "
                         "ON a.bill_id=b.id WHERE a.user_id=? AND a.status='active' "
                         "AND b.status!='Closed' AND b.deadline IS NOT NULL AND b.deadline<=?",
                         (uid, soon))]
    for msg, link in items:
        if not q("SELECT 1 FROM notifications WHERE user_id=? AND type='deadline' AND message=?",
                 (uid, msg), one=True):
            ex("INSERT INTO notifications(user_id,type,message,link,created_at) VALUES(?,?,?,?,?)",
               (uid, "deadline", msg, link, now()))


@app.route("/")
@login_required
def dashboard():
    deadline_notices(g.user["id"])
    frag, args = bill_scope()
    stat = lambda sql, a=(): q(sql, a, one=True)["c"]

    stats = dict(
        active=stat(f"SELECT COUNT(*) c FROM bills b WHERE b.status NOT IN ('Closed','Draft'){frag}", args),
        high=stat(f"SELECT COUNT(*) c FROM bills b WHERE b.priority='High' AND b.status!='Closed'{frag}", args),
        pending=stat(f"SELECT COUNT(*) c FROM bills b WHERE b.party_position='Pending' AND b.status!='Closed'{frag}", args),
    )
    tscope, targs = ("", ()) if is_staff() else (" AND (t.owner_id=? OR t.created_by=?)",
                                                   (g.user["id"], g.user["id"]))
    stats["open_tasks"] = stat(f"SELECT COUNT(*) c FROM tasks t WHERE t.status!='Done'{tscope}", targs)
    overdue = q(f"SELECT t.*, u.name owner FROM tasks t LEFT JOIN users u ON u.id=t.owner_id "
                f"WHERE t.status!='Done' AND t.deadline<?{tscope} ORDER BY t.deadline LIMIT 8",
                (today(),) + targs)
    stats["overdue"] = len(overdue)

    # Parliamentary Party (Samsadiya Dal) Specific Metrics
    mp_stats = dict(
        total=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active'"),
        hor=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house='House of Representatives'"),
        na=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house='National Assembly'"),
        province=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house NOT IN ('House of Representatives','National Assembly')"),
        fptp=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND election_type='FPTP'"),
        pr=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND election_type='PR'"),
    )

    # Active Whips & Upcoming Voting
    whip_stats = dict(
        total_whips=stat("SELECT COUNT(*) c FROM whips"),
        active_whips=stat("SELECT COUNT(*) c FROM whips WHERE status IN ('Issued','Draft')"),
        upcoming_votes=stat("SELECT COUNT(*) c FROM whips WHERE status='Issued' AND voting_date>=?", (today(),)),
    )
    upcoming_whips = q(
        "SELECT w.*, u.name issuer_name FROM whips w LEFT JOIN users u ON u.id=w.issued_by "
        "WHERE w.status='Issued' AND w.voting_date>=? ORDER BY w.voting_date LIMIT 4", (today(),)
    )

    # Today's Floor Speakers
    today_rosters = q(
        "SELECT r.*, p.name mp_name, p.name_ne, p.constituency, p.house mp_house "
        "FROM speaker_rosters r JOIN parliamentarians p ON p.id=r.parliamentarian_id "
        "WHERE r.session_date>=? ORDER BY r.session_date, r.speaking_order LIMIT 6", (today(),)
    )

    # Leave & Article 89(d) Consecutive Absence Risk Watchlist
    active_leaves = q(
        "SELECT l.*, p.name mp_name, p.constituency FROM mp_leaves l "
        "JOIN parliamentarians p ON p.id=l.parliamentarian_id "
        "WHERE l.status='Approved' AND l.end_date>=? ORDER BY l.start_date LIMIT 4", (today(),)
    )
    art89_watch = absence_watchlist(3)
    strength = house_strength()
    upcoming_sittings = q(
        "SELECT * FROM house_sittings WHERE sitting_date>=? ORDER BY sitting_date LIMIT 4", (today(),)
    )

    high = q(f"SELECT b.* FROM bills b WHERE b.priority='High' AND b.status!='Closed'{frag} "
             f"ORDER BY b.deadline IS NULL, b.deadline LIMIT 6", args)
    meetings = q("SELECT * FROM meetings WHERE status='Scheduled' AND date>=? ORDER BY date LIMIT 5",
                 (today(),))
    if is_staff():
        recent = q("SELECT l.*, u.name actor FROM activity_logs l LEFT JOIN users u ON u.id=l.actor_id "
                   "ORDER BY l.id DESC LIMIT 10")
    else:
        recent = q("SELECT l.*, u.name actor FROM activity_logs l LEFT JOIN users u ON u.id=l.actor_id "
                   "WHERE l.actor_id=? OR (l.entity_type='bill' AND l.entity_id IN "
                   "(SELECT bill_id FROM bill_assignments WHERE user_id=? AND status='active')) "
                   "ORDER BY l.id DESC LIMIT 10", (g.user["id"], g.user["id"]))

    return render_template("dashboard.html", stats=stats, mp_stats=mp_stats,
                           whip_stats=whip_stats, upcoming_whips=upcoming_whips,
                           today_rosters=today_rosters, active_leaves=active_leaves,
                           art89_watch=art89_watch, strength=strength,
                           upcoming_sittings=upcoming_sittings,
                           overdue=overdue, high=high, meetings=meetings, recent=recent)


# ----------------------------------------------------------------- members (Parliamentarians)
@app.route("/members")
@login_required
def members_list():
    house = request.args.get("house", "").strip()
    province = request.args.get("province", "").strip()
    election_type = request.args.get("election_type", "").strip()
    pr_cluster = request.args.get("pr_cluster", "").strip()
    dal_role = request.args.get("dal_role", "").strip()
    query = request.args.get("q", "").strip()

    sql = "SELECT p.*, u.email user_email FROM parliamentarians p LEFT JOIN users u ON u.id=p.user_id WHERE p.status='active'"
    args = []

    if house:
        sql += " AND p.house=?"
        args.append(house)
    if province:
        sql += " AND p.province=?"
        args.append(province)
    if election_type:
        sql += " AND p.election_type=?"
        args.append(election_type)
    if pr_cluster:
        sql += " AND p.pr_cluster=?"
        args.append(pr_cluster)
    if dal_role:
        sql += " AND p.dal_role=?"
        args.append(dal_role)
    if query:
        sql += " AND (p.name LIKE ? OR p.name_ne LIKE ? OR p.constituency LIKE ? OR p.district LIKE ?)"
        term = f"%{query}%"
        args.extend([term, term, term, term])

    sql += " ORDER BY CASE p.dal_role WHEN 'Parliamentary Party Leader' THEN 1 WHEN 'Deputy Leader' THEN 2 WHEN 'Chief Whip' THEN 3 WHEN 'Whip' THEN 4 ELSE 5 END, p.name"
    mps = q(sql, tuple(args))

    # Summary counts
    stat = lambda s, a=(): q(s, a, one=True)["c"]
    stats = dict(
        total=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active'"),
        hor=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house='House of Representatives'"),
        na=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house='National Assembly'"),
        province=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND house NOT IN ('House of Representatives','National Assembly')"),
        fptp=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND election_type='FPTP'"),
        pr=stat("SELECT COUNT(*) c FROM parliamentarians WHERE status='active' AND election_type='PR'"),
    )

    return render_template(
        "members.html", mps=mps, stats=stats,
        sel_house=house, sel_province=province, sel_election=election_type,
        sel_cluster=pr_cluster, sel_role=dal_role, query=query
    )


@app.route("/members/print")
@login_required
def members_print():
    grouped = []
    for h in HOUSES:
        mps = q(
            "SELECT * FROM parliamentarians WHERE status='active' AND house=? "
            "ORDER BY CASE dal_role WHEN 'Parliamentary Party Leader' THEN 1 WHEN 'Deputy Leader' THEN 2 "
            "WHEN 'Chief Whip' THEN 3 WHEN 'Whip' THEN 4 ELSE 5 END, name", (h,)
        )
        if mps:
            grouped.append((h, mps))
    return render_template("members_print.html", grouped=grouped, printed_at=now())


def member_spec():
    house_opts = [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    prov_opts = [(p, p) for p in PROVINCES]
    el_opts = [(e, ELECTION_LABELS.get(e, e)) for e in ELECTION_TYPES]
    cl_opts = [(c, PR_CLUSTER_LABELS.get(c, c)) for c in PR_CLUSTERS]
    role_opts = [(r, DAL_ROLE_LABELS.get(r, r)) for r in DAL_ROLES]
    users_opts = [("", "— None (No login linked) —")] + [
        (str(u["id"]), f"{u['name']} ({u['email']})")
        for u in q("SELECT id, name, email FROM users WHERE status='active' ORDER BY name")
    ]

    return [
        dict(name="name", label="Full Name (English) *", required=True),
        dict(name="name_ne", label="Full Name (नेपाली नाम)", help="देवनागरी लिपिमा नाम, जस्तै: माननीय रमेश अधिकारी"),
        dict(name="house", label="Legislative Body / House *", type="select", required=True, choices=house_opts),
        dict(name="province", label="Province / Level *", type="select", required=True, choices=prov_opts),
        dict(name="election_type", label="Election Category *", type="select", required=True, choices=el_opts),
        dict(name="pr_cluster", label="PR Cluster / Category", type="select", choices=cl_opts),
        dict(name="dal_role", label="Parliamentary Party Role *", type="select", required=True, choices=role_opts),
        dict(name="district", label="District (जिल्ला)", help="जस्तै: काठमाडौँ, झापा, मोरङ, दाङ"),
        dict(name="constituency", label="Constituency (निर्वाचन क्षेत्र)", help="जस्तै: काठमाडौँ-४, दाङ-१"),
        dict(name="committee", label="Key Committee Assignment"),
        dict(name="contact", label="Personal Phone / Contact"),
        dict(name="pa_name", label="PA / Personal Secretary Name (स्वकीय सचिव)"),
        dict(name="pa_contact", label="PA Phone Number"),
        dict(name="capital_address", label="Capital Residence (काठमाडौँ / राजधानी ठेगाना)"),
        dict(name="blood_group", label="Blood Group"),
        dict(name="bio", label="Bio / Parliamentary Profile", type="textarea"),
        dict(name="user_id", label="Link to System User Account", type="select", choices=users_opts),
    ]


@app.route("/members/new", methods=["GET", "POST"])
@perm_required("member.manage")
def member_new():
    spec = member_spec()
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            uid = int(vals["user_id"]) if vals.get("user_id") else None
            pid = ex(
                "INSERT INTO parliamentarians(name,name_ne,house,province,election_type,pr_cluster,dal_role,"
                "district,constituency,committee,contact,pa_name,pa_contact,capital_address,blood_group,bio,status,user_id)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["name"], vals["name_ne"], vals["house"], vals["province"], vals["election_type"],
                 vals["pr_cluster"], vals["dal_role"], vals["district"], vals["constituency"],
                 vals["committee"], vals["contact"], vals["pa_name"], vals["pa_contact"],
                 vals["capital_address"], vals["blood_group"], vals["bio"], "active", uid)
            )
            log("created parliamentarian", "parliamentarian", pid, vals["name"])
            flash(f"Member '{vals['name']}' added to party roster.", "ok")
            return redirect(url_for("member_view", pid=pid))
    return render_form("Register New Parliamentarian (सांसद दर्ता)", spec, vals, errs,
                       url_for("members_list"), "Save Member Details",
                       sub="Add MP to Parliamentary Party (Samsadiya Dal) Database")


@app.route("/members/<int:pid>")
@login_required
def member_view(pid):
    mp = q("SELECT p.*, u.email user_email FROM parliamentarians p LEFT JOIN users u ON u.id=p.user_id WHERE p.id=?",
           (pid,), one=True)
    if not mp:
        abort(404)

    # Committee memberships
    committees = q(
        "SELECT cm.role, c.id, c.name, c.house FROM committee_members cm "
        "JOIN committees c ON c.id=cm.committee_id WHERE cm.parliamentarian_id=? ORDER BY c.name", (pid,)
    )

    # Whip compliance history
    whip_history = q(
        "SELECT wm.*, w.title, w.ref_no, w.whip_type, w.directive, w.voting_date, w.status whip_status "
        "FROM whip_members wm JOIN whips w ON w.id=wm.whip_id "
        "WHERE wm.parliamentarian_id=? ORDER BY w.voting_date DESC", (pid,)
    )

    # Floor speaker appearances
    speeches = q(
        "SELECT * FROM speaker_rosters WHERE parliamentarian_id=? ORDER BY session_date DESC", (pid,)
    )

    # Leaves history
    leaves = q(
        "SELECT l.*, u.name approver_name FROM mp_leaves l LEFT JOIN users u ON u.id=l.approved_by "
        "WHERE l.parliamentarian_id=? ORDER BY l.start_date DESC", (pid,)
    )

    # Parliamentary questions
    questions = q(
        "SELECT * FROM parliamentary_questions WHERE parliamentarian_id=? ORDER BY id DESC", (pid,)
    )

    # Compliance summary
    total_whips = len(whip_history)
    complied_whips = sum(1 for w in whip_history if w["compliance_status"] == "Complied")
    violated_whips = sum(1 for w in whip_history if w["compliance_status"] == "Violated")
    total_leave_days = sum(l["days_count"] for l in leaves if l["status"] == "Approved")

    sittings = q(
        "SELECT s.sitting_date, s.sitting_no, s.session_name, s.house, sa.status att_status, sa.remarks "
        "FROM sitting_attendance sa JOIN house_sittings s ON s.id=sa.sitting_id "
        "WHERE sa.parliamentarian_id=? ORDER BY s.sitting_date DESC LIMIT 20", (pid,)
    )
    abs_streak = consecutive_absence_streak(pid, mp["house"])

    stats = dict(
        total_whips=total_whips,
        complied_whips=complied_whips,
        violated_whips=violated_whips,
        speeches_count=len(speeches),
        total_leave_days=total_leave_days,
        questions_count=len(questions),
        absence_streak=abs_streak,
    )

    return render_template(
        "member.html", mp=mp, stats=stats, committees=committees,
        whip_history=whip_history, speeches=speeches, leaves=leaves, questions=questions,
        sittings=sittings
    )


@app.route("/members/<int:pid>/edit", methods=["GET", "POST"])
@perm_required("member.manage")
def member_edit(pid):
    mp = q("SELECT * FROM parliamentarians WHERE id=?", (pid,), one=True)
    if not mp:
        abort(404)
    spec = member_spec()
    vals = dict(mp)
    vals["user_id"] = str(mp["user_id"]) if mp["user_id"] else ""
    errs = {}

    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            uid = int(vals["user_id"]) if vals.get("user_id") else None
            ex(
                "UPDATE parliamentarians SET name=?,name_ne=?,house=?,province=?,election_type=?,"
                "pr_cluster=?,dal_role=?,district=?,constituency=?,committee=?,contact=?,pa_name=?,"
                "pa_contact=?,capital_address=?,blood_group=?,bio=?,user_id=? WHERE id=?",
                (vals["name"], vals["name_ne"], vals["house"], vals["province"], vals["election_type"],
                 vals["pr_cluster"], vals["dal_role"], vals["district"], vals["constituency"],
                 vals["committee"], vals["contact"], vals["pa_name"], vals["pa_contact"],
                 vals["capital_address"], vals["blood_group"], vals["bio"], uid, pid)
            )
            log("edited parliamentarian", "parliamentarian", pid, vals["name"])
            flash("Member profile updated.", "ok")
            return redirect(url_for("member_view", pid=pid))

    return render_form(f"Edit MP: {mp['name']}", spec, vals, errs,
                       url_for("member_view", pid=pid), "Save Changes")


# ----------------------------------------------------------------- Samsadiya Dal Office desk
@app.route("/office")
@login_required
def office_desk():
    strength = house_strength()
    leaders = q(
        "SELECT * FROM parliamentarians WHERE status='active' AND dal_role IN "
        "('Parliamentary Party Leader','Deputy Leader','Chief Whip','Whip') "
        "ORDER BY CASE dal_role WHEN 'Parliamentary Party Leader' THEN 1 WHEN 'Deputy Leader' THEN 2 "
        "WHEN 'Chief Whip' THEN 3 ELSE 4 END, name"
    )
    clusters = q(
        "SELECT COALESCE(pr_cluster,'None / Direct') cluster, COUNT(*) c "
        "FROM parliamentarians WHERE status='active' GROUP BY pr_cluster ORDER BY c DESC"
    )
    elections = q(
        "SELECT COALESCE(election_type,'FPTP') election_type, COUNT(*) c "
        "FROM parliamentarians WHERE status='active' GROUP BY election_type"
    )
    watch = absence_watchlist(3)
    letters = q("SELECT * FROM office_letters ORDER BY letter_date DESC, id DESC LIMIT 8")
    sittings = q("SELECT * FROM house_sittings ORDER BY sitting_date DESC, id DESC LIMIT 6")
    return render_template(
        "office.html", strength=strength, leaders=leaders, clusters=clusters,
        elections=elections, watch=watch, letters=letters, sittings=sittings
    )


# ----------------------------------------------------------------- House sittings (सदन बैठक हाजिरी)
@app.route("/sittings")
@login_required
def sittings_list():
    house = request.args.get("house", "").strip()
    sql = "SELECT * FROM house_sittings WHERE 1=1"
    args = []
    if house:
        sql += " AND house=?"
        args.append(house)
    sql += " ORDER BY sitting_date DESC, id DESC"
    sittings = q(sql, tuple(args))
    return render_template("sittings.html", sittings=sittings, sel_house=house)


def sitting_spec():
    return [
        dict(name="house", label="House / Assembly *", type="select", required=True,
             choices=[(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]),
        dict(name="sitting_date", label="Sitting date *", type="date", required=True),
        dict(name="sitting_no", label="Sitting number (बैठक संख्या)", help="e.g. 12th sitting of winter session"),
        dict(name="session_name", label="Session (अधिवेशन)", help="e.g. Winter Session 2081"),
        dict(name="agenda", label="Main business / agenda", type="textarea"),
        dict(name="status", label="Status *", type="select", required=True,
             choices=[(s, s) for s in SITTING_STATUSES]),
    ]


@app.route("/sittings/new", methods=["GET", "POST"])
@perm_required("sitting.manage")
def sitting_new():
    spec = sitting_spec()
    vals, errs = {"status": "Held", "sitting_date": today()}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            sid = ex(
                "INSERT INTO house_sittings(house,sitting_date,sitting_no,session_name,agenda,status,created_by,created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (vals["house"], vals["sitting_date"], vals["sitting_no"], vals["session_name"],
                 vals["agenda"], vals["status"], g.user["id"], now())
            )
            mps = q("SELECT id FROM parliamentarians WHERE status='active' AND house=?", (vals["house"],))
            for mp in mps:
                ex("INSERT INTO sitting_attendance(sitting_id,parliamentarian_id,status) VALUES(?,?,?)",
                   (sid, mp["id"], "Present"))
            log("recorded house sitting", "sitting", sid, f"{vals['house']} {vals['sitting_date']}")
            flash("Sitting recorded. Mark absences on the roll call.", "ok")
            return redirect(url_for("sitting_view", sid=sid))
    return render_form("Record house sitting (सदन बैठक)", spec, vals, errs,
                       url_for("sittings_list"), "Create sitting",
                       sub="Samsadiya Dal Office · attendance roll for Art. 89(d)")


@app.route("/sittings/<int:sid>")
@login_required
def sitting_view(sid):
    sitting = q("SELECT * FROM house_sittings WHERE id=?", (sid,), one=True)
    if not sitting:
        abort(404)
    roll = q(
        "SELECT sa.*, p.name, p.name_ne, p.constituency, p.dal_role "
        "FROM sitting_attendance sa JOIN parliamentarians p ON p.id=sa.parliamentarian_id "
        "WHERE sa.sitting_id=? ORDER BY p.name", (sid,)
    )
    present = sum(1 for r in roll if r["status"] == "Present")
    absent = sum(1 for r in roll if r["status"] == "Absent")
    leave = sum(1 for r in roll if r["status"] == "Leave")
    duty = sum(1 for r in roll if r["status"] == "Official Duty")
    return render_template("sitting.html", sitting=sitting, roll=roll,
                           present=present, absent=absent, leave=leave, duty=duty)


@app.route("/sittings/<int:sid>/attendance", methods=["POST"])
@perm_required("sitting.manage")
def sitting_attendance(sid):
    sitting = q("SELECT * FROM house_sittings WHERE id=?", (sid,), one=True)
    if not sitting:
        abort(404)
    roll = q("SELECT parliamentarian_id FROM sitting_attendance WHERE sitting_id=?", (sid,))
    for r in roll:
        pid = r["parliamentarian_id"]
        st = request.form.get(f"st_{pid}", "Present")
        if st not in SITTING_ATT_STATUSES:
            abort(400)
        rem = (request.form.get(f"rm_{pid}") or "").strip()
        ex("UPDATE sitting_attendance SET status=?, remarks=? WHERE sitting_id=? AND parliamentarian_id=?",
           (st, rem, sid, pid))
    log("updated sitting roll", "sitting", sid, sitting["house"])
    flash("Attendance roll saved.", "ok")
    return redirect(url_for("sitting_view", sid=sid))


# ----------------------------------------------------------------- Office correspondence (आगत / प्रेषित पत्र)
def letter_spec():
    return [
        dict(name="direction", label="Direction *", type="select", required=True,
             choices=[(d, LETTER_DIRECTION_LABELS[d]) for d in LETTER_DIRECTIONS]),
        dict(name="ref_no", label="Chalani / darta number *", required=True,
             help="e.g. स.द.आ.२०८१/०८९ or स.द.प्र.२०८१/०४२"),
        dict(name="letter_date", label="Letter date *", type="date", required=True),
        dict(name="subject", label="Subject *", required=True, minlen=4),
        dict(name="from_party", label="From (प्रेषक)"),
        dict(name="to_party", label="To (प्रापक)"),
        dict(name="house", label="Related house", type="select",
             choices=[("", "—")] + [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]),
        dict(name="category", label="Category", type="select",
             choices=[(c, c) for c in LETTER_CATEGORIES]),
        dict(name="status", label="Status *", type="select", required=True,
             choices=[(s, s) for s in LETTER_STATUSES]),
        dict(name="notes", label="Notes / action", type="textarea"),
    ]


@app.route("/letters")
@login_required
def letters_list():
    direction = request.args.get("direction", "").strip()
    sql = "SELECT * FROM office_letters WHERE 1=1"
    args = []
    if direction in LETTER_DIRECTIONS:
        sql += " AND direction=?"
        args.append(direction)
    sql += " ORDER BY letter_date DESC, id DESC"
    letters = q(sql, tuple(args))
    return render_template("letters.html", letters=letters, sel_direction=direction)


@app.route("/letters/new", methods=["GET", "POST"])
@perm_required("letter.manage")
def letter_new():
    spec = letter_spec()
    vals, errs = {"letter_date": today(), "status": "Registered", "direction": "Incoming"}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            lid = ex(
                "INSERT INTO office_letters(direction,ref_no,letter_date,subject,from_party,to_party,"
                "house,category,status,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["direction"], vals["ref_no"], vals["letter_date"], vals["subject"],
                 vals["from_party"], vals["to_party"], vals.get("house") or None,
                 vals["category"], vals["status"], vals["notes"], g.user["id"], now())
            )
            log("registered office letter", "letter", lid, vals["ref_no"])
            flash("Letter registered in Samsadiya Dal Office.", "ok")
            return redirect(url_for("letters_list"))
    return render_form("Register letter (पत्र दर्ता)", spec, vals, errs,
                       url_for("letters_list"), "Register",
                       sub="आगत / प्रेषित पत्र · संसदीय दलको कार्यालय")


# ----------------------------------------------------------------- whips (ह्वीप व्यवस्थापन)
@app.route("/whips")
@login_required
def whips_list():
    house = request.args.get("house", "").strip()
    whip_type = request.args.get("whip_type", "").strip()
    status = request.args.get("status", "").strip()

    sql = "SELECT w.*, u.name issuer_name, b.title bill_title FROM whips w " \
          "LEFT JOIN users u ON u.id=w.issued_by " \
          "LEFT JOIN bills b ON b.id=w.bill_id WHERE 1=1"
    args = []
    if house:
        sql += " AND w.house=?"
        args.append(house)
    if whip_type:
        sql += " AND w.whip_type=?"
        args.append(whip_type)
    if status:
        sql += " AND w.status=?"
        args.append(status)

    sql += " ORDER BY w.voting_date DESC, w.id DESC"
    whips = q(sql, tuple(args))

    stats = dict(
        total=q("SELECT COUNT(*) c FROM whips", one=True)["c"],
        active=q("SELECT COUNT(*) c FROM whips WHERE status IN ('Issued','Draft')", one=True)["c"],
        three_line=q("SELECT COUNT(*) c FROM whips WHERE whip_type='Three-line'", one=True)["c"],
        upcoming=q("SELECT COUNT(*) c FROM whips WHERE status='Issued' AND voting_date>=?", (today(),), one=True)["c"],
    )

    return render_template("whips.html", whips=whips, stats=stats,
                           sel_house=house, sel_type=whip_type, sel_status=status)


@app.route("/whips/new", methods=["GET", "POST"])
@perm_required("whip.issue")
def whip_new():
    house_opts = [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    type_opts = [(t, WHIP_TYPE_LABELS.get(t, t)) for t in WHIP_TYPES]
    dir_opts = [(d, WHIP_DIRECTIVE_LABELS.get(d, d)) for d in WHIP_DIRECTIVES]
    bill_opts = [("", "— None / General Motion —")] + [
        (str(b["id"]), b["title"]) for b in q("SELECT id, title FROM bills WHERE status!='Closed' ORDER BY title")
    ]

    errs, vals = {}, {}
    if request.method == "POST":
        vals = {
            "ref_no": (request.form.get("ref_no") or "").strip(),
            "title": (request.form.get("title") or "").strip(),
            "whip_type": (request.form.get("whip_type") or "").strip(),
            "house": (request.form.get("house") or "").strip(),
            "directive": (request.form.get("directive") or "").strip(),
            "voting_date": (request.form.get("voting_date") or "").strip(),
            "voting_time": (request.form.get("voting_time") or "").strip(),
            "bill_id": (request.form.get("bill_id") or "").strip(),
            "agenda": (request.form.get("agenda") or "").strip(),
            "legal_basis": (request.form.get("legal_basis") or "राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८").strip(),
            "notes": (request.form.get("notes") or "").strip(),
        }

        if not vals["ref_no"]:
            errs["ref_no"] = "चलानी नं. / Ref No is required."
        if not vals["title"]:
            errs["title"] = "Whip title is required."
        if not vals["whip_type"]:
            errs["whip_type"] = "Whip type is required."
        if not vals["house"]:
            errs["house"] = "Target House is required."
        if not vals["directive"]:
            errs["directive"] = "Directive is required."
        if not vals["voting_date"]:
            errs["voting_date"] = "Voting date is required."
        if not vals["agenda"]:
            errs["agenda"] = "Agenda / Instructions are required."

        if not errs:
            rbill = int(vals["bill_id"]) if vals["bill_id"] else None
            wid = ex(
                "INSERT INTO whips(ref_no,title,whip_type,house,directive,voting_date,voting_time,bill_id,"
                "agenda,legal_basis,status,issued_by,issued_at,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["ref_no"], vals["title"], vals["whip_type"], vals["house"], vals["directive"],
                 vals["voting_date"], vals["voting_time"], rbill, vals["agenda"], vals["legal_basis"],
                 "Issued", g.user["id"], now(), vals["notes"])
            )

            # Auto-populate whip_members for all party MPs in that House
            target_mps = q("SELECT id, user_id FROM parliamentarians WHERE status='active' AND house=?", (vals["house"],))
            for m in target_mps:
                ex(
                    "INSERT OR IGNORE INTO whip_members(whip_id,parliamentarian_id,served_status,served_at,"
                    "attendance_status,vote_cast,compliance_status,disciplinary_action,remarks) VALUES(?,?,?,?,?,?,?,?,?)",
                    (wid, m["id"], "Served", now(), "Present", "Pending", "Pending", "None", "Notice issued by Chief Whip Office")
                )
                if m["user_id"]:
                    notify(m["user_id"], "whip", f"Official Whip Issued: {vals['title']} ({vals['directive']})",
                           url_for("whip_view", wid=wid))

            log("issued party whip", "whip", wid, f"{vals['whip_type']} on {vals['title']}")
            flash(f"Party Whip '{vals['ref_no']}' issued successfully to {len(target_mps)} MPs.", "ok")
            return redirect(url_for("whip_view", wid=wid))

    default_ref = f"स.द.२०८१/{today().split('-')[1]}-{secrets.randbelow(899)+100}"
    return render_template(
        "whip_form.html", vals=vals, errs=errs, house_opts=house_opts,
        type_opts=type_opts, dir_opts=dir_opts, bill_opts=bill_opts, default_ref=default_ref
    )


@app.route("/whips/<int:wid>")
@login_required
def whip_view(wid):
    whip = q(
        "SELECT w.*, u.name issuer_name, b.title bill_title FROM whips w "
        "LEFT JOIN users u ON u.id=w.issued_by "
        "LEFT JOIN bills b ON b.id=w.bill_id WHERE w.id=?", (wid,), one=True
    )
    if not whip:
        abort(404)

    roll_call = q(
        "SELECT wm.*, p.name mp_name, p.name_ne, p.constituency, p.district, p.dal_role, p.contact "
        "FROM whip_members wm JOIN parliamentarians p ON p.id=wm.parliamentarian_id "
        "WHERE wm.whip_id=? ORDER BY CASE p.dal_role WHEN 'Parliamentary Party Leader' THEN 1 WHEN 'Deputy Leader' THEN 2 WHEN 'Chief Whip' THEN 3 WHEN 'Whip' THEN 4 ELSE 5 END, p.name",
        (wid,)
    )

    total_targeted = len(roll_call)
    complied_count = sum(1 for r in roll_call if r["compliance_status"] == "Complied")
    violated_count = sum(1 for r in roll_call if r["compliance_status"] == "Violated")
    exempted_count = sum(1 for r in roll_call if r["compliance_status"] == "Exempted")
    pending_count = sum(1 for r in roll_call if r["compliance_status"] == "Pending")
    cross_voted = sum(1 for r in roll_call if r["vote_cast"] == "Cross-voted")

    compliance_rate = round((complied_count / max(total_targeted - exempted_count, 1)) * 100)

    stats = dict(
        total=total_targeted,
        complied=complied_count,
        violated=violated_count,
        exempted=exempted_count,
        pending=pending_count,
        cross_voted=cross_voted,
        rate=compliance_rate
    )

    return render_template("whip.html", whip=whip, roll_call=roll_call, stats=stats)


@app.route("/whips/<int:wid>/rollcall", methods=["POST"])
@perm_required("whip.record")
def whip_rollcall(wid):
    whip = q("SELECT * FROM whips WHERE id=?", (wid,), one=True)
    if not whip:
        abort(404)

    wmid = int(request.form.get("wmid") or 0)
    attendance = request.form.get("attendance_status", "Present")
    vote_cast = request.form.get("vote_cast", "Pending")
    remarks = request.form.get("remarks", "")

    # Auto calculate compliance status
    if vote_cast == "In Line":
        compliance = "Complied"
    elif vote_cast == "Cross-voted":
        compliance = "Violated"
    elif attendance == "Absent with Leave":
        compliance = "Exempted"
    elif attendance == "Absent without Leave":
        compliance = "Violated"
    else:
        compliance = "Pending"

    ex(
        "UPDATE whip_members SET attendance_status=?, vote_cast=?, compliance_status=?, remarks=? WHERE id=? AND whip_id=?",
        (attendance, vote_cast, compliance, remarks, wmid, wid)
    )
    log("updated whip rollcall", "whip_member", wmid, f"Vote: {vote_cast}, Compliance: {compliance}")
    flash("Roll call vote record updated.", "ok")
    return redirect(url_for("whip_view", wid=wid))


@app.route("/whips/<int:wid>/disciplinary/<int:wmid>", methods=["POST"])
@perm_required("whip.issue")
def whip_disciplinary(wid, wmid):
    action = request.form.get("action", "Show-cause Issued")
    remarks = request.form.get("remarks", "")

    ex(
        "UPDATE whip_members SET disciplinary_action=?, remarks=? WHERE id=? AND whip_id=?",
        (action, remarks, wmid, wid)
    )

    wm = q("SELECT wm.*, p.name, p.user_id FROM whip_members wm JOIN parliamentarians p ON p.id=wm.parliamentarian_id WHERE wm.id=?", (wmid,), one=True)
    if wm and wm["user_id"]:
        notify(wm["user_id"], "disciplinary", f"Disciplinary Notice regarding Whip violation: {action}", url_for("whip_view", wid=wid))

    log("issued disciplinary action on whip", "whip_member", wmid, action)
    flash(f"Disciplinary action '{action}' recorded under Political Parties Act 2073 Sec 32.", "ok")
    return redirect(url_for("whip_view", wid=wid))


@app.route("/whips/<int:wid>/print")
@login_required
def whip_print(wid):
    whip = q(
        "SELECT w.*, u.name issuer_name, b.title bill_title FROM whips w "
        "LEFT JOIN users u ON u.id=w.issued_by "
        "LEFT JOIN bills b ON b.id=w.bill_id WHERE w.id=?", (wid,), one=True
    )
    if not whip:
        abort(404)
    mps = q(
        "SELECT p.*, wm.served_status FROM whip_members wm "
        "JOIN parliamentarians p ON p.id=wm.parliamentarian_id WHERE wm.whip_id=? ORDER BY p.name", (wid,)
    )
    return render_template("whip_print.html", whip=whip, mps=mps)


# ----------------------------------------------------------------- floor speaker rosters (सदन वक्ता तालिका)
@app.route("/rosters")
@login_required
def rosters_list():
    house = request.args.get("house", "").strip()
    session_date = request.args.get("session_date", "").strip()
    session_type = request.args.get("session_type", "").strip()

    sql = "SELECT r.*, p.name mp_name, p.name_ne, p.constituency, p.house mp_house, b.title bill_title, u.name creator_name " \
          "FROM speaker_rosters r JOIN parliamentarians p ON p.id=r.parliamentarian_id " \
          "LEFT JOIN bills b ON b.id=r.bill_id " \
          "LEFT JOIN users u ON u.id=r.created_by WHERE 1=1"
    args = []
    if house:
        sql += " AND r.house=?"
        args.append(house)
    if session_date:
        sql += " AND r.session_date=?"
        args.append(session_date)
    if session_type:
        sql += " AND r.session_type=?"
        args.append(session_type)

    sql += " ORDER BY r.session_date DESC, r.speaking_order ASC"
    rosters = q(sql, tuple(args))

    available_dates = [r[0] for r in q("SELECT DISTINCT session_date FROM speaker_rosters ORDER BY session_date DESC LIMIT 10")]

    return render_template("rosters.html", rosters=rosters, available_dates=available_dates,
                           sel_house=house, sel_date=session_date, sel_type=session_type)


@app.route("/rosters/new", methods=["GET", "POST"])
@perm_required("roster.manage")
def roster_new():
    house_opts = [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    type_opts = [(s, SESSION_TYPE_LABELS.get(s, s)) for s in SESSION_TYPES]
    bill_opts = [("", "— None / Zero-Special Hour —")] + [
        (str(b["id"]), b["title"]) for b in q("SELECT id, title FROM bills WHERE status!='Closed' ORDER BY title")
    ]
    mps = q("SELECT id, name, name_ne, constituency, house FROM parliamentarians WHERE status='active' ORDER BY house, name")

    errs, vals = {}, {}
    if request.method == "POST":
        vals = {
            "house": (request.form.get("house") or "").strip(),
            "session_date": (request.form.get("session_date") or "").strip(),
            "session_type": (request.form.get("session_type") or "").strip(),
            "parliamentarian_id": (request.form.get("parliamentarian_id") or "").strip(),
            "topic": (request.form.get("topic") or "").strip(),
            "allocated_minutes": (request.form.get("allocated_minutes") or "3").strip(),
            "speaking_order": (request.form.get("speaking_order") or "1").strip(),
            "talking_points": (request.form.get("talking_points") or "").strip(),
            "bill_id": (request.form.get("bill_id") or "").strip(),
        }

        if not vals["house"]:
            errs["house"] = "House is required."
        if not vals["session_date"]:
            errs["session_date"] = "Session date is required."
        if not vals["session_type"]:
            errs["session_type"] = "Session type is required."
        if not vals["parliamentarian_id"]:
            errs["parliamentarian_id"] = "MP must be selected."
        if not vals["topic"]:
            errs["topic"] = "Topic is required."

        if not errs:
            rbill = int(vals["bill_id"]) if vals["bill_id"] else None
            rid = ex(
                "INSERT INTO speaker_rosters(house,session_date,session_type,parliamentarian_id,topic,"
                "allocated_minutes,speaking_order,talking_points,bill_id,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["house"], vals["session_date"], vals["session_type"], int(vals["parliamentarian_id"]),
                 vals["topic"], int(vals["allocated_minutes"]), int(vals["speaking_order"]),
                 vals["talking_points"], rbill, "Scheduled", g.user["id"], now())
            )

            p = q("SELECT user_id, name FROM parliamentarians WHERE id=?", (vals["parliamentarian_id"],), one=True)
            if p and p["user_id"]:
                notify(p["user_id"], "roster", f"Floor Speaking Scheduled ({vals['session_type']}): {vals['topic']}", url_for("rosters_list"))

            log("scheduled floor speaker", "speaker_roster", rid, f"{p['name']} on {vals['topic']}")
            flash(f"Floor speaker '{p['name']}' scheduled successfully.", "ok")
            return redirect(url_for("rosters_list", session_date=vals["session_date"], house=vals["house"]))

    return render_template(
        "roster_form.html", vals=vals, errs=errs, house_opts=house_opts,
        type_opts=type_opts, bill_opts=bill_opts, mps=mps
    )


@app.route("/rosters/<int:rid>/status", methods=["POST"])
@perm_required("roster.manage")
def roster_status(rid):
    st = request.form.get("status")
    if st in ("Scheduled", "Submitted to Secretariat", "Delivered", "Cancelled"):
        ex("UPDATE speaker_rosters SET status=? WHERE id=?", (st, rid))
        log("updated roster status", "speaker_roster", rid, st)
        flash(f"Speaker roster status updated to '{st}'.", "ok")
    return redirect(request.referrer or url_for("rosters_list"))


@app.route("/rosters/<int:rid>/delete", methods=["POST"])
@perm_required("roster.manage")
def roster_delete(rid):
    ex("DELETE FROM speaker_rosters WHERE id=?", (rid,))
    log("deleted roster entry", "speaker_roster", rid)
    flash("Speaker roster entry removed.", "ok")
    return redirect(url_for("rosters_list"))


@app.route("/rosters/print")
@login_required
def roster_print():
    house = request.args.get("house", "House of Representatives").strip()
    session_date = request.args.get("session_date", today()).strip()

    rosters = q(
        "SELECT r.*, p.name mp_name, p.name_ne, p.constituency, p.district, p.contact "
        "FROM speaker_rosters r JOIN parliamentarians p ON p.id=r.parliamentarian_id "
        "WHERE r.house=? AND r.session_date=? ORDER BY r.session_type, r.speaking_order",
        (house, session_date)
    )
    return render_template("roster_print.html", rosters=rosters, house=house, session_date=session_date)


# ----------------------------------------------------------------- leaves (सांसद बिदा अनुगमन - Art. 89(d))
@app.route("/leaves")
@login_required
def leaves_list():
    status = request.args.get("status", "").strip()
    sql = "SELECT l.*, p.name mp_name, p.name_ne, p.constituency, p.house, u.name approver_name " \
          "FROM mp_leaves l JOIN parliamentarians p ON p.id=l.parliamentarian_id " \
          "LEFT JOIN users u ON u.id=l.approved_by WHERE 1=1"
    args = []
    if status:
        sql += " AND l.status=?"
        args.append(status)
    sql += " ORDER BY l.start_date DESC"
    leaves = q(sql, tuple(args))

    # Article 89(d) Consecutive Absence Risk Watchlist
    # In Nepal, 10 consecutive house absences without notice forfeits the seat.
    watchlist = q(
        "SELECT p.id, p.name, p.name_ne, p.house, p.constituency, "
        "COALESCE(SUM(l.days_count), 0) total_leave_days, "
        "COUNT(l.id) leaves_count "
        "FROM parliamentarians p "
        "LEFT JOIN mp_leaves l ON l.parliamentarian_id=p.id AND l.status='Approved' "
        "WHERE p.status='active' "
        "GROUP BY p.id ORDER BY total_leave_days DESC LIMIT 6"
    )

    stats = dict(
        total=q("SELECT COUNT(*) c FROM mp_leaves", one=True)["c"],
        active_today=q("SELECT COUNT(*) c FROM mp_leaves WHERE status='Approved' AND start_date<=? AND end_date>=?",
                       (today(), today()), one=True)["c"],
        pending=q("SELECT COUNT(*) c FROM mp_leaves WHERE status='Pending'", one=True)["c"],
    )

    return render_template("leaves.html", leaves=leaves, watchlist=watchlist, stats=stats, sel_status=status)


@app.route("/leaves/new", methods=["GET", "POST"])
@perm_required("leave.apply")
def leave_new():
    type_opts = [(t, LEAVE_TYPE_LABELS.get(t, t)) for t in LEAVE_TYPES]
    mps = q("SELECT id, name, name_ne, constituency, house FROM parliamentarians WHERE status='active' ORDER BY name")

    errs, vals = {}, {}
    if request.method == "POST":
        vals = {
            "parliamentarian_id": (request.form.get("parliamentarian_id") or "").strip(),
            "leave_type": (request.form.get("leave_type") or "").strip(),
            "start_date": (request.form.get("start_date") or "").strip(),
            "end_date": (request.form.get("end_date") or "").strip(),
            "reason": (request.form.get("reason") or "").strip(),
        }

        if not vals["parliamentarian_id"]:
            errs["parliamentarian_id"] = "MP selection is required."
        if not vals["leave_type"]:
            errs["leave_type"] = "Leave type is required."
        if not vals["start_date"]:
            errs["start_date"] = "Start date is required."
        if not vals["end_date"]:
            errs["end_date"] = "End date is required."
        if not vals["reason"]:
            errs["reason"] = "Reason for leave is required."

        days_count = 1
        try:
            d1 = dt.date.fromisoformat(vals["start_date"])
            d2 = dt.date.fromisoformat(vals["end_date"])
            days_count = max((d2 - d1).days + 1, 1)
        except Exception:
            errs["end_date"] = "Invalid date range."

        if not errs:
            status = "Approved" if is_whip_authority() else "Pending"
            approver = g.user["id"] if is_whip_authority() else None
            lid = ex(
                "INSERT INTO mp_leaves(parliamentarian_id,leave_type,start_date,end_date,days_count,reason,status,approved_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (int(vals["parliamentarian_id"]), vals["leave_type"], vals["start_date"], vals["end_date"],
                 days_count, vals["reason"], status, approver, now())
            )

            p = q("SELECT name FROM parliamentarians WHERE id=?", (vals["parliamentarian_id"],), one=True)
            log("submitted leave notice", "mp_leave", lid, f"{p['name']} ({days_count} days)")
            flash(f"Leave notice submitted for '{p['name']}' ({days_count} days) - Status: {status}.", "ok")
            return redirect(url_for("leaves_list"))

    return render_template("leave_form.html", vals=vals, errs=errs, type_opts=type_opts, mps=mps)


@app.route("/leaves/<int:lid>/approve", methods=["POST"])
@perm_required("leave.manage")
def leave_approve(lid):
    ex("UPDATE mp_leaves SET status='Approved', approved_by=? WHERE id=?", (g.user["id"], lid))
    l = q("SELECT l.*, p.user_id FROM mp_leaves l JOIN parliamentarians p ON p.id=l.parliamentarian_id WHERE l.id=?", (lid,), one=True)
    if l and l["user_id"]:
        notify(l["user_id"], "leave", "Your parliamentary leave application has been approved by the Chief Whip.", url_for("leaves_list"))
    log("approved leave", "mp_leave", lid)
    flash("Leave approved and recorded.", "ok")
    return redirect(url_for("leaves_list"))


@app.route("/leaves/<int:lid>/reject", methods=["POST"])
@perm_required("leave.manage")
def leave_reject(lid):
    ex("UPDATE mp_leaves SET status='Rejected', approved_by=? WHERE id=?", (g.user["id"], lid))
    log("rejected leave", "mp_leave", lid)
    flash("Leave rejected.", "ok")
    return redirect(url_for("leaves_list"))


# ----------------------------------------------------------------- bills & amendments
def bill_spec():
    house_opts = [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    return [
        dict(name="title", label="Title (English) *", required=True),
        dict(name="nepali_title", label="Title in Nepali (विधेयकको नेपाली नाम)", help="जस्तै: संघीय निजामती सेवा विधेयक, २०८१"),
        dict(name="house", label="Legislative Body / Assembly", type="select", choices=house_opts),
        dict(name="bill_type", label="Bill Type", type="select", choices=[("Government", "Government Bill (सरकारी विधेयक)"), ("Private Member", "Private Member Bill (गैर-सरकारी विधेयक)")]),
        dict(name="description", label="Short description", type="textarea"),
        dict(name="category", label="Category", type="select", choices=opts(CATEGORIES, "— select —")),
        dict(name="priority", label="Priority", type="select", required=True, choices=opts(PRIORITIES)),
        dict(name="status", label="Status", type="select", required=True, choices=opts(STATUSES)),
        dict(name="introduced_date", label="Introduced date", type="date"),
        dict(name="committee_id", label="Committee", type="select", choices=committee_choices()),
        dict(name="deadline", label="Deadline", type="date"),
        dict(name="next_action", label="Next action"),
    ]


@app.route("/bills")
@login_required
def bills_list():
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()
    house = request.args.get("house", "").strip()
    query = request.args.get("q", "").strip()

    frag, args = bill_scope()
    sql = f"SELECT b.*, c.name committee_name FROM bills b " \
          f"LEFT JOIN committees c ON c.id=b.committee_id WHERE 1=1{frag}"
    qargs = list(args)

    if status:
        sql += " AND b.status=?"
        qargs.append(status)
    if category:
        sql += " AND b.category=?"
        qargs.append(category)
    if priority:
        sql += " AND b.priority=?"
        qargs.append(priority)
    if house:
        sql += " AND b.house=?"
        qargs.append(house)
    if query:
        if query.upper().startswith("BILL-") and query[5:].isdigit():
            sql += " AND b.id=?"
            qargs.append(int(query[5:]))
        else:
            sql += " AND (b.title LIKE ? OR b.nepali_title LIKE ? OR b.description LIKE ?)"
            term = f"%{query}%"
            qargs.extend([term, term, term])

    sql += " ORDER BY b.id DESC"
    bills = q(sql, tuple(qargs))
    return render_template("bills.html", bills=bills, sel_status=status,
                           sel_category=category, sel_priority=priority,
                           sel_house=house, query=query, CATEGORIES=CATEGORIES,
                           HOUSES=HOUSES)


@app.route("/bills/new", methods=["GET", "POST"])
@perm_required("bill.create")
def bill_new():
    spec = bill_spec()
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            cid = int(vals["committee_id"]) if vals["committee_id"] else None
            bid = ex(
                "INSERT INTO bills(title,nepali_title,house,bill_type,description,category,priority,status,"
                "introduced_date,committee_id,deadline,next_action,created_by,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["title"], vals.get("nepali_title", ""), vals.get("house", "House of Representatives"),
                 vals.get("bill_type", "Government"), vals["description"], vals["category"], vals["priority"],
                 vals["status"], vals["introduced_date"] or None, cid,
                 vals["deadline"] or None, vals["next_action"] or None,
                 g.user["id"], now(), now())
            )
            log("created bill", "bill", bid, vals["title"])
            flash("Bill created.", "ok")
            return redirect(url_for("bill_view", bid=bid))
    return render_form("New bill", spec, vals, errs, url_for("bills_list"), "Create bill")


@app.route("/bills/<int:bid>/edit", methods=["GET", "POST"])
@perm_required("bill.edit")
def bill_edit(bid):
    b = get_bill(bid)
    spec = bill_spec()
    vals = dict(b)
    vals["committee_id"] = str(b["committee_id"]) if b["committee_id"] else ""
    errs = {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            cid = int(vals["committee_id"]) if vals["committee_id"] else None
            ex(
                "UPDATE bills SET title=?,nepali_title=?,house=?,bill_type=?,description=?,category=?,priority=?,"
                "status=?,introduced_date=?,committee_id=?,deadline=?,next_action=?,updated_at=? WHERE id=?",
                (vals["title"], vals.get("nepali_title", ""), vals.get("house", "House of Representatives"),
                 vals.get("bill_type", "Government"), vals["description"], vals["category"], vals["priority"],
                 vals["status"], vals["introduced_date"] or None, cid,
                 vals["deadline"] or None, vals["next_action"] or None,
                 now(), bid)
            )
            log("edited bill", "bill", bid, vals["title"])
            flash("Bill updated.", "ok")
            return redirect(url_for("bill_view", bid=bid))
    return render_form(f"Edit {b['title']}", spec, vals, errs, url_for("bill_view", bid=bid), "Save changes")


TABS = ["overview", "research", "position", "amendments", "assignments", "documents", "tasks", "timeline"]


@app.route("/bills/<int:bid>")
@login_required
def bill_view(bid):
    b = get_bill(bid)
    tab = request.args.get("tab", "overview")
    if tab not in TABS:
        tab = "overview"
    ctx = dict(b=b, tab=tab, TABS=TABS, POSITIONS=POSITIONS)
    ctx["assign"] = {r["assignment_type"]: r for r in q(
        "SELECT a.*, u.name FROM bill_assignments a JOIN users u ON u.id=a.user_id "
        "WHERE a.bill_id=? AND a.status='active'", (bid,))}

    if tab == "research":
        ctx["research"] = q("SELECT r.*, u.name author FROM bill_research r LEFT JOIN users u "
                            "ON u.id=r.researcher_id WHERE r.bill_id=? ORDER BY r.id DESC", (bid,))
    elif tab == "position":
        ctx["positions"] = q("SELECT p.*, u.name recorder FROM party_positions p LEFT JOIN users u "
                             "ON u.id=p.recorded_by WHERE p.bill_id=? ORDER BY p.id DESC", (bid,))
    elif tab == "amendments":
        ctx["amendments"] = q(
            "SELECT a.*, p.name mp_name, p.name_ne, p.constituency FROM bill_amendments a "
            "LEFT JOIN parliamentarians p ON p.id=a.parliamentarian_id WHERE a.bill_id=? ORDER BY a.id DESC", (bid,)
        )
        ctx["mps"] = q("SELECT id, name, name_ne, constituency FROM parliamentarians WHERE status='active' ORDER BY name")
    elif tab == "assignments":
        ctx["researchers"] = user_choices("researcher")
        ctx["mps"] = user_choices("mp")
    elif tab == "documents":
        docs = q("SELECT d.*, u.name uploader FROM documents d LEFT JOIN users u ON u.id=d.uploaded_by "
                 "WHERE d.related_type='bill' AND d.related_id=? ORDER BY d.id DESC", (bid,))
        ctx["docs"] = [d for d in docs if can_see_doc(d)]
        ctx["DOC_CATEGORIES"] = DOC_CATEGORIES
    elif tab == "tasks":
        ctx["tasks"] = q("SELECT t.*, u.name owner FROM tasks t LEFT JOIN users u ON u.id=t.owner_id "
                         "WHERE t.related_type='bill' AND t.related_id=? ORDER BY t.status='Done', t.deadline",
                         (bid,))
        ctx["users"] = user_choices(blank="— me —")
    elif tab == "timeline":
        ctx["logs"] = q("SELECT l.*, u.name actor FROM activity_logs l LEFT JOIN users u ON u.id=l.actor_id "
                        "WHERE l.entity_type='bill' AND l.entity_id=? ORDER BY l.id DESC", (bid,))

    counts = {
        "documents": q("SELECT COUNT(*) c FROM documents WHERE related_type='bill' AND related_id=?",
                       (bid,), one=True)["c"],
        "tasks": q("SELECT COUNT(*) c FROM tasks WHERE related_type='bill' AND related_id=? "
                   "AND status!='Done'", (bid,), one=True)["c"],
        "amendments": q("SELECT COUNT(*) c FROM bill_amendments WHERE bill_id=?", (bid,), one=True)["c"],
    }
    return render_template("bill.html", counts=counts, **ctx)


@app.route("/bills/<int:bid>/status", methods=["POST"])
@perm_required("bill.status")
def bill_status(bid):
    st = request.form.get("status")
    if st not in STATUSES:
        abort(400, "Invalid status.")
    ex("UPDATE bills SET status=?, updated_at=? WHERE id=?", (st, now(), bid))
    log("status change", "bill", bid, st)
    for uid in assigned_users(bid):
        notify(uid, "status", f"Bill status changed to {st}", url_for("bill_view", bid=bid))
    flash(f"Status changed to {st}.", "ok")
    return redirect(url_for("bill_view", bid=bid))


@app.route("/bills/<int:bid>/research", methods=["POST"])
@perm_required("bill.research")
def bill_research(bid):
    summary = (request.form.get("summary") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    if not summary:
        flash("Summary is required.", "err")
        return redirect(url_for("bill_view", bid=bid, tab="research"))
    ex("INSERT INTO bill_research(bill_id,researcher_id,summary,notes,created_at) VALUES(?,?,?,?,?)",
       (bid, g.user["id"], summary, notes, now()))
    ex("UPDATE bills SET updated_at=? WHERE id=?", (now(), bid))
    log("added research", "bill", bid, summary[:60])
    for uid in assigned_users(bid):
        notify(uid, "research", f"New research added to {bid}", url_for("bill_view", bid=bid, tab="research"))
    flash("Research note saved.", "ok")
    return redirect(url_for("bill_view", bid=bid, tab="research"))


@app.route("/bills/<int:bid>/position", methods=["POST"])
@perm_required("bill.position")
def bill_position(bid):
    pos = request.form.get("position")
    dec_by = (request.form.get("decided_by") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    if pos not in POSITIONS:
        abort(400, "Invalid position.")
    if not dec_by:
        flash("Deciding authority is required.", "err")
        return redirect(url_for("bill_view", bid=bid, tab="position"))
    d = today()
    ex("UPDATE bills SET party_position=?, decision_date=?, updated_at=? WHERE id=?",
       (pos, d, now(), bid))
    ex("INSERT INTO party_positions(bill_id,position,decision_date,decided_by,notes,recorded_by,created_at)"
       " VALUES(?,?,?,?,?,?,?)", (bid, pos, d, dec_by, notes, g.user["id"], now()))
    log("recorded party position", "bill", bid, f"{pos} (decided by {dec_by})")
    for uid in assigned_users(bid):
        notify(uid, "position", f"Party position recorded: {pos}", url_for("bill_view", bid=bid, tab="position"))
    flash(f"Position recorded: {pos}.", "ok")
    return redirect(url_for("bill_view", bid=bid, tab="position"))


@app.route("/bills/<int:bid>/assign", methods=["POST"])
@perm_required("bill.assign")
def bill_assign(bid):
    kind = request.form.get("kind")
    if kind not in ("researcher", "parliamentarian"):
        abort(400, "Invalid assignment type.")
    uid_str = request.form.get("user_id")
    target_role = "researcher" if kind == "researcher" else "mp"

    ex("UPDATE bill_assignments SET status='removed' WHERE bill_id=? AND assignment_type=?",
       (bid, kind))
    if uid_str:
        try:
            target_uid = int(uid_str)
        except ValueError:
            abort(400, "Invalid user id.")
        target_user = q("SELECT * FROM users WHERE id=? AND status='active'", (target_uid,), one=True)
        if not target_user or target_user["role"] != target_role:
            abort(400, f"Target user must have the {target_role} role.")
        ex("INSERT INTO bill_assignments(bill_id,user_id,assignment_type,status,assigned_at)"
           " VALUES(?,?,?,?,?)", (bid, target_uid, kind, "active", now()))
        log(f"assigned {kind}", "bill", bid, target_user["name"])
        notify(target_uid, "assignment", f"You were assigned to bill {bid}", url_for("bill_view", bid=bid))
        flash(f"Assigned {target_user['name']} as {kind}.", "ok")
    else:
        log(f"cleared {kind} assignment", "bill", bid)
        flash(f"Cleared {kind} assignment.", "ok")
    ex("UPDATE bills SET updated_at=? WHERE id=?", (now(), bid))
    return redirect(url_for("bill_view", bid=bid, tab="assignments"))


@app.route("/bills/<int:bid>/amendments/new", methods=["POST"])
@perm_required("amendment.manage")
def amendment_new(bid):
    b = get_bill(bid)
    sec = (request.form.get("section_clause") or "").strip()
    text = (request.form.get("proposed_text") or "").strip()
    rationale = (request.form.get("rationale") or "").strip()
    mp_id_str = request.form.get("parliamentarian_id")
    stance = request.form.get("party_stance", "Endorsed")

    if not sec or not text:
        flash("Section/Clause and Proposed Text are required.", "err")
        return redirect(url_for("bill_view", bid=bid, tab="amendments"))

    mp_id = int(mp_id_str) if mp_id_str else None
    aid = ex(
        "INSERT INTO bill_amendments(bill_id,parliamentarian_id,section_clause,proposed_text,rationale,party_stance,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (bid, mp_id, sec, text, rationale, stance, "Registered", g.user["id"], now())
    )
    log("registered party amendment", "bill", bid, f"{sec}: {text[:60]}")
    flash(f"Party amendment registered for {sec}.", "ok")
    return redirect(url_for("bill_view", bid=bid, tab="amendments"))


@app.route("/bills/<int:bid>/amendments/<int:aid>/status", methods=["POST"])
@perm_required("bill.edit")
def amendment_status(bid, aid):
    st = request.form.get("status", "Registered")
    ex("UPDATE bill_amendments SET status=? WHERE id=? AND bill_id=?", (st, aid, bid))
    flash(f"Amendment status updated to '{st}'.", "ok")
    return redirect(url_for("bill_view", bid=bid, tab="amendments"))


@app.route("/bills/<int:bid>/task", methods=["POST"])
@login_required
def bill_task(bid):
    get_bill(bid)
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Task title required.", "err")
        return redirect(url_for("bill_view", bid=bid, tab="tasks"))
    oid = request.form.get("owner_id")
    owner = int(oid) if oid else g.user["id"]
    dl = request.form.get("deadline") or None
    pr = request.form.get("priority") or "Medium"
    tid = ex("INSERT INTO tasks(title,owner_id,related_type,related_id,deadline,priority,status,notes,created_by,created_at)"
             " VALUES(?,?,?,?,?,?,?,?,?,?)",
             (title, owner, "bill", bid, dl, pr, "Open", "", g.user["id"], now()))
    log("created task", "bill", bid, title)
    notify(owner, "task", f"New task on bill {bid}: {title}", url_for("tasks_list"))
    flash("Task created.", "ok")
    return redirect(url_for("bill_view", bid=bid, tab="tasks"))


# ----------------------------------------------------------------- tasks
def task_spec():
    return [
        dict(name="title", label="Title", required=True),
        dict(name="owner_id", label="Owner", type="select", choices=user_choices(blank="— unassigned —")),
        dict(name="priority", label="Priority", type="select", required=True, choices=opts(PRIORITIES)),
        dict(name="deadline", label="Deadline", type="date"),
        dict(name="notes", label="Notes", type="textarea"),
    ]


@app.route("/tasks")
@login_required
def tasks_list():
    view = request.args.get("view", "mine")
    scope = ""
    args = []
    if view == "mine":
        scope = "WHERE t.owner_id=?"
        args = [g.user["id"]]
    elif view == "overdue":
        scope = "WHERE t.status!='Done' AND t.deadline<?"
        args = [today()]
        if not is_staff():
            scope += " AND t.owner_id=?"
            args.append(g.user["id"])
    elif view == "done":
        scope = "WHERE t.status='Done'"
        if not is_staff():
            scope += " AND t.owner_id=?"
            args.append(g.user["id"])
    else:
        if not is_staff():
            scope = "WHERE t.owner_id=?"
            args = [g.user["id"]]
    sql = f"SELECT t.*, u.name owner FROM tasks t LEFT JOIN users u ON u.id=t.owner_id {scope} " \
          f"ORDER BY t.status='Done', t.deadline IS NULL, t.deadline"
    tasks = q(sql, tuple(args))
    return render_template("tasks.html", tasks=tasks, view=view)


@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def task_new():
    spec = task_spec()
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            oid = int(vals["owner_id"]) if vals["owner_id"] else None
            tid = ex(
                "INSERT INTO tasks(title,owner_id,priority,deadline,notes,status,created_by,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (vals["title"], oid, vals["priority"], vals["deadline"] or None,
                 vals["notes"], "Open", g.user["id"], now())
            )
            log("created task", "task", tid, vals["title"])
            if oid:
                notify(oid, "task", f"New task: {vals['title']}", url_for("tasks_list"))
            flash("Task created.", "ok")
            return redirect(url_for("tasks_list"))
    return render_form("New task", spec, vals, errs, url_for("tasks_list"), "Create task")


@app.route("/tasks/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def task_edit(tid):
    t = q("SELECT * FROM tasks WHERE id=?", (tid,), one=True)
    if not t:
        abort(404)
    if not is_staff() and t["owner_id"] != g.user["id"] and t["created_by"] != g.user["id"]:
        abort(403)
    spec = task_spec() + [dict(name="status", label="Status", type="select", choices=opts(TASK_STATUSES))]
    vals = dict(t)
    vals["owner_id"] = str(t["owner_id"]) if t["owner_id"] else ""
    errs = {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            oid = int(vals["owner_id"]) if vals["owner_id"] else None
            ex(
                "UPDATE tasks SET title=?,owner_id=?,priority=?,deadline=?,notes=?,status=? WHERE id=?",
                (vals["title"], oid, vals["priority"], vals["deadline"] or None,
                 vals["notes"], vals["status"], tid)
            )
            log("edited task", "task", tid, vals["title"])
            flash("Task updated.", "ok")
            return redirect(url_for("tasks_list"))
    return render_form(f"Edit task", spec, vals, errs, url_for("tasks_list"), "Save changes")


@app.route("/tasks/<int:tid>/toggle", methods=["POST"])
@login_required
def task_toggle(tid):
    t = q("SELECT * FROM tasks WHERE id=?", (tid,), one=True)
    if not t:
        abort(404)
    if not is_staff() and t["owner_id"] != g.user["id"]:
        abort(403)
    nxt = "Open" if t["status"] == "Done" else "Done"
    ex("UPDATE tasks SET status=? WHERE id=?", (nxt, tid))
    log(f"marked task {nxt.lower()}", "task", tid, t["title"])
    return redirect(request.referrer or url_for("tasks_list"))


# ----------------------------------------------------------------- committees
def committee_spec():
    house_opts = [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    return [
        dict(name="name", label="Name *", required=True),
        dict(name="house", label="House / Legislative Body", type="select", choices=house_opts),
        dict(name="description", label="Description", type="textarea"),
    ]


@app.route("/committees")
@login_required
def committees_list():
    comms = q("SELECT c.*, (SELECT COUNT(*) FROM committee_members WHERE committee_id=c.id) members_count "
              "FROM committees c WHERE c.status='active' ORDER BY c.name")
    return render_template("committees.html", committees=comms)


@app.route("/committees/new", methods=["GET", "POST"])
@perm_required("committee.manage")
def committee_new():
    spec = committee_spec()
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if not errs:
            cid = ex("INSERT INTO committees(name,house,description,status) VALUES(?,?,?,?)",
                     (vals["name"], vals["house"], vals["description"], "active"))
            log("created committee", "committee", cid, vals["name"])
            flash("Committee created.", "ok")
            return redirect(url_for("committee_view", cid=cid))
    return render_form("New committee", spec, vals, errs, url_for("committees_list"), "Create committee")


@app.route("/committees/<int:cid>")
@login_required
def committee_view(cid):
    c = q("SELECT * FROM committees WHERE id=?", (cid,), one=True)
    if not c:
        abort(404)
    members = q("SELECT m.role, p.* FROM committee_members m JOIN parliamentarians p "
                "ON p.id=m.parliamentarian_id WHERE m.committee_id=? ORDER BY m.role='Chair' DESC, p.name",
                (cid,))
    bills = q("SELECT * FROM bills WHERE committee_id=? ORDER BY status!='Closed' DESC, title", (cid,))
    meetings = q("SELECT * FROM meetings WHERE committee_id=? ORDER BY date DESC", (cid,))
    candidates = q("SELECT id,name FROM parliamentarians WHERE status='active' AND id NOT IN "
                   "(SELECT parliamentarian_id FROM committee_members WHERE committee_id=?) ORDER BY name",
                   (cid,))
    return render_template("committee.html", c=c, members=members, bills=bills,
                           meetings=meetings, candidates=candidates)


@app.route("/committees/<int:cid>/members", methods=["POST"])
@perm_required("committee.manage")
def committee_member_add(cid):
    pid = request.form.get("parliamentarian_id")
    role = request.form.get("role") or "Member"
    if not pid:
        flash("Pick a parliamentarian.", "err")
        return redirect(url_for("committee_view", cid=cid))
    p = q("SELECT * FROM parliamentarians WHERE id=?", (pid,), one=True)
    if not p:
        abort(404)
    ex("INSERT OR REPLACE INTO committee_members(committee_id,parliamentarian_id,role) VALUES(?,?,?)",
       (cid, pid, role))
    log("added committee member", "committee", cid, f"{p['name']} ({role})")
    flash(f"Added {p['name']} to committee.", "ok")
    return redirect(url_for("committee_view", cid=cid))


@app.route("/committees/<int:cid>/members/<int:pid>/remove", methods=["POST"])
@perm_required("committee.manage")
def committee_member_remove(cid, pid):
    ex("DELETE FROM committee_members WHERE committee_id=? AND parliamentarian_id=?", (cid, pid))
    log("removed committee member", "committee", cid, f"parliamentarian {pid}")
    flash("Member removed from committee.", "ok")
    return redirect(url_for("committee_view", cid=cid))


# ----------------------------------------------------------------- questions
def question_spec():
    mps = [("", "— unassigned —")] + [(str(r["id"]), r["name"]) for r in
                                    q("SELECT id,name FROM parliamentarians WHERE status='active' ORDER BY name")]
    return [
        dict(name="question", label="Question *", type="textarea", required=True),
        dict(name="parliamentarian_id", label="Filing MP", type="select", choices=mps),
        dict(name="ministry", label="Target Ministry"),
        dict(name="subject", label="Subject / Topic"),
        dict(name="submitted_date", label="Submission date", type="date"),
        dict(name="status", label="Status", type="select", choices=opts(Q_STATUSES)),
        dict(name="response", label="Government response", type="textarea"),
        dict(name="follow_up", label="Follow-up notes", type="textarea"),
    ]


def can_see_question(qrow):
    if is_staff():
        return True
    if g.user["role"] == "mp":
        p = q("SELECT id FROM parliamentarians WHERE user_id=?", (g.user["id"],), one=True)
        return p and qrow["parliamentarian_id"] == p["id"]
    return False


def get_question_or_403(qid):
    row = q("SELECT pq.*, p.name mp_name, u.name creator FROM parliamentary_questions pq "
          "LEFT JOIN parliamentarians p ON p.id=pq.parliamentarian_id "
          "LEFT JOIN users u ON u.id=pq.created_by WHERE pq.id=?", (qid,), one=True)
    if not row:
        abort(404)
    if not can_see_question(row):
        abort(403)
    return row


@app.route("/questions")
@login_required
def questions_list():
    base = ("SELECT pq.*, p.name mp_name FROM parliamentary_questions pq "
           "LEFT JOIN parliamentarians p ON p.id=pq.parliamentarian_id WHERE 1=1")
    args = []
    if not is_staff():
        if g.user["role"] == "mp":
            p = q("SELECT id FROM parliamentarians WHERE user_id=?", (g.user["id"],), one=True)
            if not p:
                return render_template("questions.html", questions=[])
            base += " AND pq.parliamentarian_id=?"
            args.append(p["id"])
        else:
            return render_template("questions.html", questions=[])
    base += " ORDER BY pq.id DESC"
    questions = q(base, tuple(args))
    return render_template("questions.html", questions=questions)


@app.route("/questions/new", methods=["GET", "POST"])
@perm_required("question.create")
def question_new():
    spec = question_spec()
    vals, errs = {}, {}
    if g.user["role"] == "mp":
        mine = q("SELECT id FROM parliamentarians WHERE user_id=?", (g.user["id"],), one=True)
        vals["parliamentarian_id"] = str(mine["id"]) if mine else ""
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if g.user["role"] == "mp":
            mine = q("SELECT id FROM parliamentarians WHERE user_id=?", (g.user["id"],), one=True)
            if not mine or str(mine["id"]) != vals.get("parliamentarian_id"):
                errs["parliamentarian_id"] = "You may only file questions for yourself."
        if not errs:
            pid = int(vals["parliamentarian_id"]) if vals["parliamentarian_id"] else None
            qid = ex(
                "INSERT INTO parliamentary_questions(question,parliamentarian_id,ministry,subject,"
                "submitted_date,status,response,follow_up,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (vals["question"], pid, vals["ministry"], vals["subject"],
                 vals["submitted_date"] or None, vals["status"] or "Draft",
                 vals["response"], vals["follow_up"], g.user["id"], now())
            )
            log("filed question", "question", qid, vals["subject"] or vals["question"][:40])
            flash("Question filed.", "ok")
            return redirect(url_for("question_view", qid=qid))
    return render_form("File parliamentary question", spec, vals, errs,
                       url_for("questions_list"), "Submit question")


@app.route("/questions/<int:qid>")
@login_required
def question_view(qid):
    row = get_question_or_403(qid)
    return render_template("question.html", q=row)


@app.route("/questions/<int:qid>/edit", methods=["GET", "POST"])
@login_required
def question_edit(qid):
    row = get_question_or_403(qid)
    if not is_staff() and row["created_by"] != g.user["id"]:
        abort(403)
    spec = question_spec()
    vals = dict(row)
    vals["parliamentarian_id"] = str(row["parliamentarian_id"]) if row["parliamentarian_id"] else ""
    errs = {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if g.user["role"] == "mp":
            mine = q("SELECT id FROM parliamentarians WHERE user_id=?", (g.user["id"],), one=True)
            if not mine or str(mine["id"]) != vals.get("parliamentarian_id"):
                errs["parliamentarian_id"] = "You may only file questions for yourself."
        if not errs:
            pid = int(vals["parliamentarian_id"]) if vals["parliamentarian_id"] else None
            ex(
                "UPDATE parliamentary_questions SET question=?,parliamentarian_id=?,ministry=?,"
                "subject=?,submitted_date=?,status=?,response=?,follow_up=? WHERE id=?",
                (vals["question"], pid, vals["ministry"], vals["subject"],
                 vals["submitted_date"] or None, vals["status"] or "Draft",
                 vals["response"], vals["follow_up"], qid)
            )
            log("edited question", "question", qid)
            flash("Question updated.", "ok")
            return redirect(url_for("question_view", qid=qid))
    return render_form("Edit question", spec, vals, errs, url_for("question_view", qid=qid), "Save changes")


# ----------------------------------------------------------------- meetings
def meeting_spec():
    cat_opts = [(c, c) for c in MEETING_CATEGORIES]
    house_opts = [("", "— All / General —")] + [(h, HOUSE_LABELS.get(h, h)) for h in HOUSES]
    bills = [("", "— none —")] + [(str(r["id"]), r["title"]) for r in visible_bills()]
    return [
        dict(name="title", label="Title *", required=True),
        dict(name="meeting_category", label="Meeting Type", type="select", choices=cat_opts),
        dict(name="house", label="House / Assembly", type="select", choices=house_opts),
        dict(name="date", label="Date and time *", help="Format: YYYY-MM-DDTHH:MM", required=True),
        dict(name="location", label="Location (स्थान)"),
        dict(name="committee_id", label="Related committee", type="select", choices=committee_choices()),
        dict(name="bill_id", label="Related bill", type="select", choices=bills),
        dict(name="participants", label="Participants (सहभागीहरू)", help="Comma-separated or list of roles"),
        dict(name="agenda", label="Agenda (कार्यसूची)", type="textarea"),
        dict(name="decisions", label="Decisions / Resolutions (दलका निर्णयहरू)", type="textarea"),
        dict(name="minutes", label="Minutes (विस्तृत माइन्युट)", type="textarea"),
        dict(name="status", label="Status", type="select", choices=opts(MEETING_STATUSES)),
    ]


@app.route("/meetings")
@login_required
def meetings_list():
    meetings = q(
        "SELECT m.*, c.name committee_name, b.title bill_title FROM meetings m "
        "LEFT JOIN committees c ON c.id=m.committee_id "
        "LEFT JOIN bills b ON b.id=m.bill_id ORDER BY m.date DESC"
    )
    return render_template("meetings.html", meetings=meetings)


@app.route("/meetings/new", methods=["GET", "POST"])
@perm_required("meeting.manage")
def meeting_new():
    spec = meeting_spec()
    vals = {}
    if request.args.get("bill"):
        vals["bill_id"] = request.args.get("bill")
    if request.args.get("committee"):
        vals["committee_id"] = request.args.get("committee")
    errs = {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if vals.get("date"):
            try:
                dt.datetime.fromisoformat(vals["date"])
            except ValueError:
                errs["date"] = "Use YYYY-MM-DDTHH:MM (e.g. 2026-10-15T14:30)."
        if not errs:
            cid = int(vals["committee_id"]) if vals["committee_id"] else None
            bid = int(vals["bill_id"]) if vals["bill_id"] else None
            mid = ex(
                "INSERT INTO meetings(title,date,location,committee_id,bill_id,participants,agenda,"
                "decisions,minutes,status,meeting_category,house,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vals["title"], vals["date"], vals["location"], cid, bid, vals["participants"],
                 vals["agenda"], vals["decisions"], vals["minutes"], vals["status"] or "Scheduled",
                 vals.get("meeting_category", "Samsadiya Dal Meeting"), vals.get("house", None),
                 g.user["id"], now())
            )
            log("created meeting", "meeting", mid, vals["title"])
            flash("Meeting created.", "ok")
            return redirect(url_for("meeting_view", mid=mid))
    return render_form("Schedule meeting", spec, vals, errs, url_for("meetings_list"), "Schedule")


@app.route("/meetings/<int:mid>")
@login_required
def meeting_view(mid):
    m = q(
        "SELECT m.*, c.name committee_name, b.title bill_title FROM meetings m "
        "LEFT JOIN committees c ON c.id=m.committee_id "
        "LEFT JOIN bills b ON b.id=m.bill_id WHERE m.id=?", (mid,), one=True
    )
    if not m:
        abort(404)

    attendance = q(
        "SELECT ma.*, p.name mp_name, p.name_ne, p.constituency FROM meeting_attendance ma "
        "JOIN parliamentarians p ON p.id=ma.parliamentarian_id WHERE ma.meeting_id=? ORDER BY p.name",
        (mid,)
    )

    mps = q("SELECT id, name, name_ne, constituency FROM parliamentarians WHERE status='active' ORDER BY name")
    return render_template("meeting.html", m=m, attendance=attendance, mps=mps)


@app.route("/meetings/<int:mid>/attendance", methods=["POST"])
@perm_required("meeting.manage")
def meeting_attendance(mid):
    pid = request.form.get("parliamentarian_id")
    status = request.form.get("status", "Present")
    remarks = request.form.get("remarks", "")
    if pid:
        ex("INSERT OR REPLACE INTO meeting_attendance(meeting_id,parliamentarian_id,status,remarks) VALUES(?,?,?,?)",
           (mid, int(pid), status, remarks))
        flash("Attendance recorded.", "ok")
    return redirect(url_for("meeting_view", mid=mid))


@app.route("/meetings/<int:mid>/print")
@login_required
def meeting_print(mid):
    m = q(
        "SELECT m.*, c.name committee_name, b.title bill_title, u.name creator_name FROM meetings m "
        "LEFT JOIN committees c ON c.id=m.committee_id "
        "LEFT JOIN bills b ON b.id=m.bill_id "
        "LEFT JOIN users u ON u.id=m.created_by WHERE m.id=?", (mid,), one=True
    )
    if not m:
        abort(404)
    attendance = q(
        "SELECT ma.*, p.name mp_name, p.name_ne, p.constituency, p.dal_role "
        "FROM meeting_attendance ma JOIN parliamentarians p ON p.id=ma.parliamentarian_id "
        "WHERE ma.meeting_id=? ORDER BY p.name", (mid,)
    )
    return render_template("meeting_print.html", m=m, attendance=attendance)


@app.route("/meetings/<int:mid>/edit", methods=["GET", "POST"])
@perm_required("meeting.manage")
def meeting_edit(mid):
    m = q("SELECT * FROM meetings WHERE id=?", (mid,), one=True)
    if not m:
        abort(404)
    spec = meeting_spec()
    vals = dict(m)
    vals["committee_id"] = str(m["committee_id"]) if m["committee_id"] else ""
    vals["bill_id"] = str(m["bill_id"]) if m["bill_id"] else ""
    errs = {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        if vals.get("date"):
            try:
                dt.datetime.fromisoformat(vals["date"])
            except ValueError:
                errs["date"] = "Use YYYY-MM-DDTHH:MM."
        if not errs:
            cid = int(vals["committee_id"]) if vals["committee_id"] else None
            bid = int(vals["bill_id"]) if vals["bill_id"] else None
            ex(
                "UPDATE meetings SET title=?,date=?,location=?,committee_id=?,bill_id=?,"
                "participants=?,agenda=?,decisions=?,minutes=?,status=?,meeting_category=?,house=? WHERE id=?",
                (vals["title"], vals["date"], vals["location"], cid, bid, vals["participants"],
                 vals["agenda"], vals["decisions"], vals["minutes"], vals["status"],
                 vals.get("meeting_category", "Samsadiya Dal Meeting"), vals.get("house", None), mid)
            )
            log("edited meeting", "meeting", mid, vals["title"])
            flash("Meeting updated.", "ok")
            return redirect(url_for("meeting_view", mid=mid))
    return render_form("Edit meeting", spec, vals, errs, url_for("meeting_view", mid=mid), "Save changes")


# ----------------------------------------------------------------- documents
@app.route("/documents")
@login_required
def documents_list():
    docs = q("SELECT d.*, u.name uploader FROM documents d LEFT JOIN users u ON u.id=d.uploaded_by "
             "ORDER BY d.id DESC")
    visible = [d for d in docs if can_see_doc(d)]
    return render_template("documents.html", docs=visible)


@app.route("/documents/upload", methods=["GET", "POST"])
@login_required
def document_upload():
    related_type = request.args.get("type") or request.form.get("related_type")
    related_id = request.args.get("id") or request.form.get("related_id")
    if request.method == "POST":
        f = request.files.get("file")
        name = (request.form.get("name") or "").strip()
        cat = request.form.get("category")
        access = request.form.get("access_level") or "internal"
        if not f or not f.filename:
            flash("Select a file to upload.", "err")
            return render_template("document_upload.html", categories=DOC_CATEGORIES,
                                   related_type=related_type, related_id=related_id)
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_EXT:
            flash(f"Unsupported file type .{ext}.", "err")
            return render_template("document_upload.html", categories=DOC_CATEGORIES,
                                   related_type=related_type, related_id=related_id)
        if not is_staff():
            access = "internal"
        rid = int(related_id) if related_id else None
        if related_type == "bill" and rid:
            frag, args = bill_scope()
            if not q(f"SELECT 1 FROM bills b WHERE b.id=?{frag}", (rid,) + args, one=True):
                abort(403)
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(UPLOADS, stored_name))
        did = ex(
            "INSERT INTO documents(name,file_path,original_name,category,related_type,related_id,"
            "access_level,uploaded_by,uploaded_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (name or f.filename, stored_name, f.filename, cat, related_type, rid,
             access, g.user["id"], now())
        )
        log("uploaded document", related_type or "document", rid or did, name or f.filename)
        flash("Document uploaded.", "ok")
        if related_type == "bill" and rid:
            return redirect(url_for("bill_view", bid=rid, tab="documents"))
        return redirect(url_for("documents_list"))
    return render_template("document_upload.html", categories=DOC_CATEGORIES,
                           related_type=related_type, related_id=related_id)


@app.route("/documents/<int:did>/download")
@login_required
def document_download(did):
    d = q("SELECT * FROM documents WHERE id=?", (did,), one=True)
    if not d or not can_see_doc(d):
        abort(404)
    return send_from_directory(UPLOADS, d["file_path"], as_attachment=True,
                               download_name=d["original_name"])


# ----------------------------------------------------------------- notifications
@app.route("/notifications")
@login_required
def notifications():
    rows = q("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50",
             (g.user["id"],))
    return render_template("notifications.html", notifications=rows)


@app.route("/notifications/read", methods=["POST"])
@login_required
def notifications_read():
    ex("UPDATE notifications SET read_at=? WHERE user_id=? AND read_at IS NULL",
       (now(), g.user["id"]))
    return redirect(url_for("notifications"))


@app.route("/notifications/<int:nid>/go")
@login_required
def notification_go(nid):
    n = q("SELECT * FROM notifications WHERE id=? AND user_id=?", (nid, g.user["id"]), one=True)
    if not n:
        abort(404)
    ex("UPDATE notifications SET read_at=? WHERE id=?", (now(), nid))
    return redirect(n["link"] or url_for("notifications"))


# ----------------------------------------------------------------- audit & users
@app.route("/audit")
@perm_required("audit.view")
def audit():
    logs = q("SELECT l.*, u.name actor, u.email FROM activity_logs l LEFT JOIN users u "
             "ON u.id=l.actor_id ORDER BY l.id DESC LIMIT 100")
    return render_template("audit.html", logs=logs)


def user_spec():
    return [
        dict(name="name", label="Full name *", required=True),
        dict(name="email", label="Email address *", required=True),
        dict(name="password", label="Temporary password *", type="password", required=True, minlen=8),
        dict(name="role", label="Role *", type="select", required=True, choices=[(k, v) for k, v in ROLES.items()]),
    ]


@app.route("/users")
@perm_required("user.manage")
def users_list():
    users = q("SELECT * FROM users ORDER BY status='active' DESC, name")
    return render_template("users.html", users=users)


@app.route("/users/new", methods=["GET", "POST"])
@perm_required("user.manage")
def user_new():
    spec = user_spec()
    vals, errs = {}, {}
    if request.method == "POST":
        vals, errs = parse(spec, request.form)
        email = (vals.get("email") or "").strip().lower()
        if q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
            errs["email"] = "Already in use."
        if not errs:
            uid = ex(
                "INSERT INTO users(name,email,password_hash,role,status,created_at) VALUES(?,?,?,?,?,?)",
                (vals["name"], email, generate_password_hash(vals["password"]), vals["role"],
                 "active", now())
            )
            if vals["role"] == "mp":
                ex("INSERT INTO parliamentarians(name,house,status,user_id) VALUES(?,?,?,?)",
                   (vals["name"], "House of Representatives", "active", uid))
            log("created user", "user", uid, f"{vals['name']} ({vals['role']})")
            flash("User created.", "ok")
            return redirect(url_for("users_list"))
    return render_form("New user", spec, vals, errs, url_for("users_list"), "Create user")


@app.route("/users/<int:uid>/toggle", methods=["POST"])
@perm_required("user.manage")
def user_toggle(uid):
    if uid == g.user["id"]:
        flash("You cannot deactivate yourself.", "err")
        return redirect(url_for("users_list"))
    u = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not u:
        abort(404)
    nxt = "inactive" if u["status"] == "active" else "active"
    ex("UPDATE users SET status=? WHERE id=?", (nxt, uid))
    log(f"set user {nxt}", "user", uid, u["email"])
    flash(f"User {u['email']} is now {nxt}.", "ok")
    return redirect(url_for("users_list"))


@app.post("/admin/reset-demo")
@perm_required("demo.reset")
def reset_demo():
    if request.form.get("confirm") != "RESET":
        flash("Type RESET to confirm.", "err")
        return redirect(url_for("users_list"))
    db().close()
    g.pop("db", None)
    do_reset()
    preferred_language = session.get("language", "en")
    session.clear()
    session["language"] = preferred_language
    flash("Demo data reset. Log in again.", "ok")
    return redirect(url_for("login"))


# ----------------------------------------------------------------- bootstrap
def do_reset():
    from seed import reset_database
    reset_database(DATA, DB_PATH, UPLOADS, SCHEMA)


def init_db():
    if not os.path.exists(DB_PATH):
        do_reset()
        print("Created and seeded", DB_PATH)
    else:
        # Check and auto-migrate existing databases to ensure all tables/columns exist
        try:
            with sqlite3.connect(DB_PATH) as con:
                con.executescript("""
                CREATE TABLE IF NOT EXISTS whips(
                  id INTEGER PRIMARY KEY, ref_no TEXT NOT NULL, title TEXT NOT NULL,
                  whip_type TEXT NOT NULL, house TEXT NOT NULL, directive TEXT NOT NULL,
                  voting_date TEXT NOT NULL, voting_time TEXT, bill_id INTEGER REFERENCES bills(id),
                  agenda TEXT NOT NULL, legal_basis TEXT DEFAULT 'राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८',
                  status TEXT NOT NULL DEFAULT 'Issued', issued_by INTEGER REFERENCES users(id),
                  issued_at TEXT NOT NULL, notes TEXT);

                CREATE TABLE IF NOT EXISTS whip_members(
                  id INTEGER PRIMARY KEY, whip_id INTEGER NOT NULL REFERENCES whips(id) ON DELETE CASCADE,
                  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
                  served_status TEXT NOT NULL DEFAULT 'Served', served_at TEXT,
                  attendance_status TEXT NOT NULL DEFAULT 'Present',
                  vote_cast TEXT NOT NULL DEFAULT 'Pending',
                  compliance_status TEXT NOT NULL DEFAULT 'Pending',
                  disciplinary_action TEXT NOT NULL DEFAULT 'None',
                  remarks TEXT,
                  UNIQUE(whip_id, parliamentarian_id));

                CREATE TABLE IF NOT EXISTS speaker_rosters(
                  id INTEGER PRIMARY KEY, house TEXT NOT NULL, session_date TEXT NOT NULL,
                  session_type TEXT NOT NULL, parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
                  topic TEXT NOT NULL, allocated_minutes INTEGER NOT NULL DEFAULT 3,
                  speaking_order INTEGER NOT NULL DEFAULT 1, talking_points TEXT,
                  bill_id INTEGER REFERENCES bills(id), status TEXT NOT NULL DEFAULT 'Scheduled',
                  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

                CREATE TABLE IF NOT EXISTS mp_leaves(
                  id INTEGER PRIMARY KEY, parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
                  leave_type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                  days_count INTEGER NOT NULL, reason TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'Approved', approved_by INTEGER REFERENCES users(id),
                  created_at TEXT NOT NULL);

                CREATE TABLE IF NOT EXISTS bill_amendments(
                  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
                  parliamentarian_id INTEGER REFERENCES parliamentarians(id),
                  section_clause TEXT NOT NULL, proposed_text TEXT NOT NULL, rationale TEXT,
                  party_stance TEXT NOT NULL DEFAULT 'Endorsed',
                  status TEXT NOT NULL DEFAULT 'Registered',
                  created_by INTEGER REFERENCES users(id),
                  created_at TEXT NOT NULL);

                CREATE TABLE IF NOT EXISTS meeting_attendance(
                  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
                  status TEXT NOT NULL DEFAULT 'Present',
                  remarks TEXT,
                  PRIMARY KEY(meeting_id, parliamentarian_id));

                CREATE TABLE IF NOT EXISTS house_sittings(
                  id INTEGER PRIMARY KEY, house TEXT NOT NULL, sitting_date TEXT NOT NULL,
                  sitting_no TEXT, session_name TEXT, agenda TEXT,
                  status TEXT NOT NULL DEFAULT 'Held',
                  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);

                CREATE TABLE IF NOT EXISTS sitting_attendance(
                  sitting_id INTEGER NOT NULL REFERENCES house_sittings(id) ON DELETE CASCADE,
                  parliamentarian_id INTEGER NOT NULL REFERENCES parliamentarians(id),
                  status TEXT NOT NULL DEFAULT 'Present', remarks TEXT,
                  PRIMARY KEY(sitting_id, parliamentarian_id));

                CREATE TABLE IF NOT EXISTS office_letters(
                  id INTEGER PRIMARY KEY, direction TEXT NOT NULL, ref_no TEXT NOT NULL,
                  letter_date TEXT NOT NULL, subject TEXT NOT NULL, from_party TEXT,
                  to_party TEXT, house TEXT, category TEXT,
                  status TEXT NOT NULL DEFAULT 'Registered', notes TEXT,
                  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
                """)
                cols = [r[1] for r in con.execute("PRAGMA table_info(parliamentarians)").fetchall()]
                for c, col_def in [
                    ("name_ne", "TEXT"), ("province", "TEXT"), ("election_type", "TEXT"),
                    ("pr_cluster", "TEXT"), ("dal_role", "TEXT"), ("district", "TEXT"),
                    ("pa_name", "TEXT"), ("pa_contact", "TEXT"), ("capital_address", "TEXT"),
                    ("blood_group", "TEXT"), ("bio", "TEXT"), ("photo_url", "TEXT")
                ]:
                    if c not in cols:
                        con.execute(f"ALTER TABLE parliamentarians ADD COLUMN {c} {col_def}")
                u_cols = [r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()]
                if "language" not in u_cols:
                    con.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
                m_cols = [r[1] for r in con.execute("PRAGMA table_info(meetings)").fetchall()]
                if "meeting_category" not in m_cols:
                    con.execute("ALTER TABLE meetings ADD COLUMN meeting_category TEXT DEFAULT 'Samsadiya Dal Meeting'")
                if "house" not in m_cols:
                    con.execute("ALTER TABLE meetings ADD COLUMN house TEXT")
                b_cols = [r[1] for r in con.execute("PRAGMA table_info(bills)").fetchall()]
                if "nepali_title" not in b_cols:
                    con.execute("ALTER TABLE bills ADD COLUMN nepali_title TEXT")
                if "house" not in b_cols:
                    con.execute("ALTER TABLE bills ADD COLUMN house TEXT DEFAULT 'House of Representatives'")
                if "bill_type" not in b_cols:
                    con.execute("ALTER TABLE bills ADD COLUMN bill_type TEXT DEFAULT 'Government'")
                con.commit()
        except Exception as e:
            print("Auto-migration note:", e)


init_db()

if __name__ == "__main__":
    if "--reset" in sys.argv:
        do_reset()
        print("Database reset and re-seeded.")
    host = os.environ.get("PMS_HOST", "127.0.0.1")
    port = int(os.environ.get("PMS_PORT", "5000"))
    print(f"\n  Nepal Parliamentary Party Management System -> http://{host}:{port}\n")
    app.run(host=host, port=port, debug=os.environ.get("PMS_DEBUG") == "1")
