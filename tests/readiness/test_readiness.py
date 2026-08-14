from services.readiness.readiness_service import ReadinessService
def test_readiness_scores_all_pass_when_dependencies_are_present():
    names = {name for name, _, _ in __import__('services.readiness.checks', fromlist=['CHECK_DEFINITIONS']).CHECK_DEFINITIONS}; report = ReadinessService({"ENVIRONMENT": "test", "VERSION": "1.0", **{name.upper(): True for name in names}}).execute(); assert report.overall_score == 100; assert report.ready
def test_readiness_report_separates_failed_checks_and_recommendations():
    report = ReadinessService({"ENVIRONMENT": "test", "VERSION": "1.0"}).execute(); assert report.failed_checks; assert report.recommendations
def test_readiness_score_is_percentage():
    report = ReadinessService({"ENVIRONMENT": "test", "VERSION": "1.0"}).execute(); assert 0 <= report.overall_score <= 100; assert all(0 <= score.score <= 100 for score in report.scores)
