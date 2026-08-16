from dashboard.app import app
def test_investigation_dashboard_registered():
    assert '/workspace/investigation-intelligence' in {str(r) for r in app.url_map.iter_rules()}
