from dashboard.app import app
def test_lifecycle_dashboard_registered():
    assert '/workspace/investigation-lifecycle' in {str(r) for r in app.url_map.iter_rules()}
