import sqlite3
from services.hunting import HuntEngine, HuntQuery, HuntRepository

def test_ioc_hunting_and_persistence(tmp_path):
    path = tmp_path / "hunt.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE iocs (case_id TEXT, ioc_type TEXT, value TEXT)")
        db.execute("INSERT INTO iocs VALUES ('CASE-1','domain','evil.example')")
    result = HuntEngine(str(path)).execute(HuntQuery("evil.example"))
    assert result.status.value == "completed" and result.findings[0].case_id == "CASE-1"
    repo = HuntRepository(str(path)); repo.save(result)
    assert repo.get(result.hunt_id)["findings"][0]["value"] == "evil.example"

def test_behavior_hunting(tmp_path):
    path = tmp_path / "hunt.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE cases (case_id TEXT,title TEXT,severity TEXT,status TEXT)")
        db.execute("INSERT INTO cases VALUES ('CASE-2','Suspicious login','high','open')")
    assert HuntEngine(str(path)).execute(HuntQuery("suspicious", "behavior")).findings
