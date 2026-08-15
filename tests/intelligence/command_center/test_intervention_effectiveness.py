from services.intelligence.command_center.intervention_effectiveness_service import InterventionEffectivenessService
def test_effectiveness_is_noncausal_and_advisory():
    x=InterventionEffectivenessService().derive('a'); assert x['effectiveness']['assessment']=='insufficient_history'; assert x['advisory_only']
