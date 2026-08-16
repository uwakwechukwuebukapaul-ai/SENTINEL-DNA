from dashboard.app import app
def test_hunting_dashboard_routes_are_registered():
    paths={str(r) for r in app.url_map.iter_rules()}; assert '/workspace/hunting-intelligence/overview' in paths and '/workspace/hunting-intelligence/gaps' in paths
