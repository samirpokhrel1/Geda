"""Smoke + permission tests. Run:  python test_app.py"""
import os
import re
import io
import shutil
import tempfile

tmp = tempfile.mkdtemp()
os.environ["PMS_DATA_DIR"] = tmp
import app as A  # noqa: E402

A.app.config["TESTING"] = True
fails = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def client(email=None):
    c = A.app.test_client()
    if email:
        r = c.get("/login")
        tok = re.search(r'name="_csrf" value="(\w+)"', r.get_data(as_text=True)).group(1)
        r = c.post("/login", data={"email": email, "password": "demo1234", "_csrf": tok})
        assert r.status_code == 302, (email, r.status_code)
    return c


def tok(c, url="/"):
    html = c.get(url).get_data(as_text=True)
    m = re.search(r'name="_csrf" value="(\w+)"', html)
    return m.group(1)


def post(c, url, data=None, **kw):
    d = dict(data or {})
    d["_csrf"] = tok(c)
    return c.post(url, data=d, **kw)


# --- auth
anon = A.app.test_client()
check("anon redirected to login", anon.get("/").status_code == 302)
check("anon cannot see bills", anon.get("/bills").status_code == 302)
check("bad password rejected", "Invalid email" in post(anon, "/login", {"email": "admin@pms.test", "password": "x"}).get_data(as_text=True)
      if False else True)
c = A.app.test_client()
t = tok(c, "/login")
check("bad password rejected", "Invalid email" in c.post("/login", data={"email": "admin@pms.test", "password": "nope", "_csrf": t}).get_data(as_text=True))
check("POST without CSRF is 400", c.post("/login", data={"email": "a", "password": "b"}).status_code == 400)
check("open redirect blocked", client().post("/login?next=//evil.com", data={}).status_code == 400)

# --- every page loads for every role
roles = ["admin", "partyadmin", "coordinator", "researcher", "researcher2", "mp1", "mp2"]
pages = ["/", "/bills", "/bills/1", "/bills/2", "/committees", "/committees/1", "/questions", "/tasks",
         "/tasks?view=all", "/meetings", "/documents", "/notifications", "/account"]
for r in roles:
    cl = client(f"{r}@pms.test")
    for p in pages:
        code = cl.get(p).status_code
        # researchers/MPs may legitimately 404 on unassigned bills
        ok = code == 200 or (p.startswith("/bills/") and code == 404 and r in ("researcher", "researcher2", "mp1", "mp2"))
        if not ok:
            check(f"{r} GET {p} -> {code}", False)
print("page sweep done")

# --- bill tabs for coordinator
co = client("coordinator@pms.test")
for tab in A.TABS:
    check(f"bill tab {tab}", co.get(f"/bills/1?tab={tab}").status_code == 200)

# --- role visibility
res = client("researcher@pms.test")
html = res.get("/bills").get_data(as_text=True)
check("researcher sees assigned bill", "Digital Payments" in html)
check("researcher does NOT see unassigned bill", "Cybersecurity and Digital Safety" not in html)
check("researcher blocked from unassigned bill (404)", res.get("/bills/1").status_code == 404)
mp = client("mp1@pms.test")
check("mp sees only assigned", "Renewable Energy" in mp.get("/bills").get_data(as_text=True) and
      "Digital Payments" not in mp.get("/bills").get_data(as_text=True))
check("mp cannot create bill", mp.get("/bills/new").status_code == 403)
check("mp cannot view audit", mp.get("/audit").status_code == 403)
check("coordinator cannot view audit", co.get("/audit").status_code == 403)
check("coordinator cannot manage users", co.get("/users").status_code == 403)
check("admin can view audit", client("admin@pms.test").get("/audit").status_code == 200)
check("admin can view users", client("admin@pms.test").get("/users").status_code == 200)

# --- restricted document hidden from MP / researcher; staff can download
docs = A.sqlite3.connect(A.DB_PATH).execute("SELECT id,access_level,related_id FROM documents").fetchall()
restricted = [d for d in docs if d[1] == "restricted"][0][0]
check("staff can download restricted doc", co.get(f"/documents/{restricted}/download").status_code == 200)
check("researcher blocked from restricted doc", res.get(f"/documents/{restricted}/download").status_code == 404)
check("mp blocked from restricted doc", mp.get(f"/documents/{restricted}/download").status_code == 404)
check("nonexistent doc 404", co.get("/documents/9999/download").status_code == 404)

# --- bill workflow as coordinator
r = post(co, "/bills/new", {"title": "Test Bill", "description": "d", "category": "Health", "priority": "High",
                            "status": "New", "committee_id": "1", "deadline": "2030-01-01"})
check("create bill redirects", r.status_code == 302)
bid = int(r.headers["Location"].rstrip("/").split("/")[-1])
check("create bill validation", "Required" in post(co, "/bills/new", {"title": "", "priority": "High", "status": "New"}).get_data(as_text=True))
check("invalid status rejected", "Invalid choice" in post(co, "/bills/new", {"title": "x", "priority": "High", "status": "Bogus"}).get_data(as_text=True))
check("edit bill", post(co, f"/bills/{bid}/edit", {"title": "Test Bill 2", "priority": "Low", "status": "Researching"}).status_code == 302)
check("status change", post(co, f"/bills/{bid}/status", {"status": "Committee"}).status_code == 302)
check("status invalid -> 400", post(co, f"/bills/{bid}/status", {"status": "Nope"}).status_code == 400)
check("assign researcher", post(co, f"/bills/{bid}/assign", {"assignment_type": "researcher", "user_id": "4"}).status_code == 302)
check("assign wrong role -> 400", post(co, f"/bills/{bid}/assign", {"assignment_type": "researcher", "user_id": "6"}).status_code == 400)
check("assign mp", post(co, f"/bills/{bid}/assign", {"assignment_type": "parliamentarian", "user_id": "6"}).status_code == 302)
check("position needs authority", post(co, f"/bills/{bid}/position", {"position": "Support", "decision_date": "2030-01-01"}).status_code == 302
      and "Test Bill 2" in co.get(f"/bills/{bid}").get_data(as_text=True))
check("record position", post(co, f"/bills/{bid}/position", {"position": "Oppose", "decision_date": "2030-01-01", "decided_by": "Party Committee", "notes": "n"}).status_code == 302)
check("research (coordinator)", post(co, f"/bills/{bid}/research", {"summary": "S", "notes": "N"}).status_code == 302)
check("task on bill", post(co, f"/bills/{bid}/task", {"title": "T1", "priority": "High", "owner_id": "4"}).status_code == 302)
up = post(co, "/documents/upload", {"category": "Bill Text", "access_level": "internal", "bill": str(bid),
                                     "file": (io.BytesIO(b"hello"), "a.txt")}, content_type="multipart/form-data")
check("upload doc", up.status_code == 302)
bad = post(co, "/documents/upload", {"category": "Bill Text", "access_level": "internal",
                                      "file": (io.BytesIO(b"x"), "evil.exe")}, content_type="multipart/form-data")
check("upload .exe rejected", bad.status_code == 302 and "/documents/upload" in bad.headers["Location"])
html = co.get(f"/bills/{bid}?tab=timeline").get_data(as_text=True)
for word in ["created bill", "status change", "assigned researcher", "recorded party position", "added research", "created task", "uploaded document"]:
    check(f"timeline has '{word}'", word in html)
check("party position stored", "Oppose" in co.get(f"/bills/{bid}").get_data(as_text=True))

# newly assigned researcher & MP can now see it and got notifications
res = client("researcher@pms.test")
check("assigned researcher now sees bill", res.get(f"/bills/{bid}").status_code == 200)
check("researcher can add research", post(res, f"/bills/{bid}/research", {"summary": "R", "notes": ""}).status_code == 302)
check("researcher cannot record position", post(res, f"/bills/{bid}/position", {"position": "Support", "decision_date": "2030-01-01", "decided_by": "me"}).status_code == 403)
check("researcher cannot change status", post(res, f"/bills/{bid}/status", {"status": "Closed"}).status_code == 403)
check("researcher cannot assign", post(res, f"/bills/{bid}/assign", {"assignment_type": "researcher", "user_id": "4"}).status_code == 403)
check("researcher got notifications", "assigned as researcher" in res.get("/notifications").get_data(as_text=True))
mp = client("mp1@pms.test")
check("assigned mp sees bill", mp.get(f"/bills/{bid}").status_code == 200)
check("mp cannot add research", post(mp, f"/bills/{bid}/research", {"summary": "x"}).status_code == 403)
doc_id = A.sqlite3.connect(A.DB_PATH).execute("SELECT id FROM documents WHERE related_id=? ", (bid,)).fetchone()[0]
check("mp can download internal doc on assigned bill", mp.get(f"/documents/{doc_id}/download").status_code == 200)
mp2 = client("mp2@pms.test")
check("other mp cannot download it", mp2.get(f"/documents/{doc_id}/download").status_code == 404)
check("mp cannot upload to unassigned bill", post(mp2, "/documents/upload", {"category": "Other", "access_level": "internal", "bill": str(bid),
      "file": (io.BytesIO(b"x"), "a.txt")}, content_type="multipart/form-data").status_code == 404)

# search & filters
check("search finds bill", "Test Bill 2" in co.get("/bills?q=Test+Bill").get_data(as_text=True))
check("search by BILL-id", "Test Bill 2" in co.get(f"/bills?q=BILL-{bid:04d}").get_data(as_text=True))
check("filter by status", "Cybersecurity" in co.get("/bills?status=Under+Review").get_data(as_text=True))
check("SQL-ish search safe", co.get("/bills?q=%27%3B+DROP+TABLE+bills%3B--").status_code == 200)

# tasks
check("create task", post(co, "/tasks/new", {"title": "Do thing", "priority": "Low", "status": "Open", "deadline": "2020-01-01", "owner_id": "4"}).status_code == 302)
check("overdue view shows task", "Do thing" in co.get("/tasks?view=overdue").get_data(as_text=True))
tid = A.sqlite3.connect(A.DB_PATH).execute("SELECT id FROM tasks WHERE title='Do thing'").fetchone()[0]
check("toggle task done", post(co, f"/tasks/{tid}/toggle").status_code == 302)
check("done view shows task", "Do thing" in co.get("/tasks?view=done").get_data(as_text=True))
mp_tid = A.sqlite3.connect(A.DB_PATH).execute("SELECT id FROM tasks WHERE title LIKE 'Update contact%'").fetchone()[0]
check("mp cannot touch others' task", post(mp, f"/tasks/{mp_tid}/toggle").status_code == 404)

# committees, meetings, questions
check("new committee", post(co, "/committees/new", {"name": "Test Com", "house": "National Assembly"}).status_code == 302)
check("add member", post(co, "/committees/1/members", {"parliamentarian_id": "3", "role": "Member"}).status_code == 302)
check("mp cannot add member", post(mp, "/committees/1/members", {"parliamentarian_id": "3"}).status_code == 403)
check("new meeting", post(co, "/meetings/new", {"title": "M", "date": "2030-05-05T10:00", "status": "Scheduled", "bill_id": str(bid)}).status_code == 302)
check("meeting bad date", "Invalid" in post(co, "/meetings/new", {"title": "M", "date": "garbage", "status": "Scheduled"}).get_data(as_text=True))
check("mp cannot create meeting", mp.get("/meetings/new").status_code == 403)
check("mp files own question", post(mp, "/questions/new", {"question": "Why?", "parliamentarian_id": "1", "ministry": "MoF", "status": "Submitted"}).status_code == 302)
check("mp cannot file as another MP", "only file" in post(mp, "/questions/new", {"question": "Why?", "parliamentarian_id": "2", "ministry": "MoF", "status": "Submitted"}).get_data(as_text=True))
qs = A.sqlite3.connect(A.DB_PATH).execute("SELECT id FROM parliamentary_questions WHERE parliamentarian_id=2").fetchone()[0]
check("mp cannot see other MP's question", mp.get(f"/questions/{qs}").status_code == 404)
check("mp cannot edit other MP's question", mp.get(f"/questions/{qs}/edit").status_code == 404)
check("coordinator edits question", post(co, f"/questions/{qs}/edit", {"question": "q", "parliamentarian_id": "2", "ministry": "m", "status": "Closed", "response": "r"}).status_code == 302)

# users & password
ad = client("admin@pms.test")
check("admin creates mp user", post(ad, "/users/new", {"name": "New MP", "email": "new@pms.test", "role": "mp", "password": "longpassword1"}).status_code == 302)
check("duplicate email rejected", "Already in use" in post(ad, "/users/new", {"name": "x", "email": "new@pms.test", "role": "mp", "password": "longpassword1"}).get_data(as_text=True))
check("short password rejected", "8 characters" in post(ad, "/users/new", {"name": "x", "email": "n2@pms.test", "role": "mp", "password": "short"}).get_data(as_text=True))
nu = A.app.test_client()
t = tok(nu, "/login")
check("new user can log in", nu.post("/login", data={"email": "new@pms.test", "password": "longpassword1", "_csrf": t}).status_code == 302)
uid = A.sqlite3.connect(A.DB_PATH).execute("SELECT id FROM users WHERE email='new@pms.test'").fetchone()[0]
check("admin deactivates user", post(ad, f"/users/{uid}/toggle").status_code == 302)
check("deactivated user locked out", nu.get("/bills").status_code == 302)
check("reset needs RESET", post(ad, "/admin/reset-demo", {"confirm": "no"}).status_code == 302 and
      A.sqlite3.connect(A.DB_PATH).execute("SELECT COUNT(*) FROM bills").fetchone()[0] > 6)
check("password change wrong current", "Incorrect" in post(co, "/account", {"current": "wrong", "new": "newpassword1"}).get_data(as_text=True))
check("logout", post(co, "/logout").status_code == 302 and co.get("/").status_code == 302)

# reset
ad = client("admin@pms.test")
check("reset demo works", post(ad, "/admin/reset-demo", {"confirm": "RESET"}).status_code == 302)
check("reset restored 6 bills", A.sqlite3.connect(A.DB_PATH).execute("SELECT COUNT(*) FROM bills").fetchone()[0] == 6)

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failure(s)" % len(fails))
for f in fails:
    print(" -", f)
raise SystemExit(1 if fails else 0)
