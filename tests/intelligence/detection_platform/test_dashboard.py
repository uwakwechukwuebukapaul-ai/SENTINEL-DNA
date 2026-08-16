from flask import Flask
from dashboard.app import app
def test_detection_dashboard_routes_are_registered():
    paths={str(rule) for rule in app.url_map.iter_rules()}; assert '/workspace/detection-intelligence/overview' in paths; assert '/workspace/detection-intelligence/gaps' in paths
