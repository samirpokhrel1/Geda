"""Focused smoke tests for locale switching and persistence. Run: python test_i18n.py"""
import os
import re
import shutil
import tempfile

tmp = tempfile.mkdtemp(prefix="pms-i18n-")
os.environ["PMS_DATA_DIR"] = tmp
import app as A  # noqa: E402

A.app.config["TESTING"] = True


def csrf(client, page="/login"):
    response = client.get(page)
    if response.status_code in (301, 302, 303, 307, 308):
        response = client.get(response.headers["Location"])
    match = re.search(r'name="_csrf" value="([^"]+)"', response.get_data(as_text=True))
    assert match, f"CSRF token not found on {page}"
    return match.group(1)


def post(client, path, data):
    return client.post(path, data={**data, "_csrf": csrf(client)})


try:
    guest = A.app.test_client()
    html = guest.get("/login").get_data(as_text=True)
    assert '<html lang="en">' in html
    assert post(guest, "/language/ne", {"next": "/login"}).status_code == 302
    html = guest.get("/login").get_data(as_text=True)
    assert '<html lang="ne">' in html
    assert "static/i18n.js" in html
    catalog = guest.get("/static/locales/ne.json").get_json()
    assert catalog["messages"]["Dashboard"] == "ड्यासबोर्ड"

    assert post(guest, "/language/en", {"next": "/login"}).status_code == 302
    token = csrf(guest)
    login = guest.post("/login", data={"email": "coordinator@pms.test", "password": "demo1234", "_csrf": token})
    assert login.status_code == 302
    assert post(guest, "/language/ne", {"next": "/"}).status_code == 302
    with A.app.app_context():
        user = A.q("SELECT language FROM users WHERE email=?", ("coordinator@pms.test",), one=True)
    assert user["language"] == "ne"
    dashboard = guest.get("/")
    assert dashboard.status_code == 200, dashboard.get_data(as_text=True)
    assert '<html lang="ne">' in dashboard.get_data(as_text=True)

    assert post(guest, "/logout", {}).status_code == 302
    token = csrf(guest)
    assert guest.post("/login", data={"email": "coordinator@pms.test", "password": "demo1234", "_csrf": token}).status_code == 302
    dashboard = guest.get("/")
    assert dashboard.status_code == 200, dashboard.get_data(as_text=True)
    assert '<html lang="ne">' in dashboard.get_data(as_text=True)

    assert post(guest, "/language/fr", {"next": "/"}).status_code == 404
    print("All bilingual language smoke checks passed.")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
