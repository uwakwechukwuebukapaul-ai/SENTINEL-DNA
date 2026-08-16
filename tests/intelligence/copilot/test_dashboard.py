from dashboard.app import app
def test_copilot_dashboard_is_registered():
    assert '/workspace/copilot' in {str(r) for r in app.url_map.iter_rules()}
