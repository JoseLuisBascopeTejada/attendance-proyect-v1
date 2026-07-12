from datetime import datetime, timedelta


def _backdate_all_attendance(temp_db_path, minutes_ago=10):
    old_ts = (datetime.utcnow() - timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    import sqlite3

    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("UPDATE attendance SET timestamp = ?", (old_ts,))
        conn.commit()
    finally:
        conn.close()


def test_report_pdf_returns_pdf(client):
    resp = client.get("/api/report/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 100


def test_report_pdf_content(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path)

    resp = client.get("/api/report/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    content = resp.content
    assert content[:5] == b"%PDF-"
    assert len(content) > 200


def test_report_pdf_empty(client):
    resp = client.get("/api/report/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 50


def test_report_pdf_with_date_filter(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path, minutes_ago=10)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    resp = client.get(f"/api/report/pdf?date_from={today}&date_to={tomorrow}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 100


def test_report_pdf_content_disposition(client):
    resp = client.get("/api/report/pdf")
    assert "Content-Disposition" in resp.headers
    assert "attendance_report.pdf" in resp.headers["Content-Disposition"]
