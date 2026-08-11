# Sentinel DNA Engineering Phase 001 Migration Map

## Audit Result

The referenced AI SOC Analyst prototype files were not present in the current local workspace during audit. The migration below treats the previously named files as the source system of record and preserves their responsibilities in the new Sentinel DNA v0.1 architecture.

## Old File → New Sentinel DNA Component

| Old prototype file | New file path | Sentinel DNA component | Migration decision |
|---|---|---|---|
| `gmail_analyzer.py` | `src/sentinel_dna/integrations/gmail_analyzer.py` | Evidence Engine | Converts Gmail/security email signals into normalized evidence records. |
| `incident_logger.py` | `src/sentinel_dna/case_management/case_store.py` | Case Management Engine | Becomes durable JSON case storage and event logging. |
| `slack_alert.py` | `src/sentinel_dna/integrations/slack_alert.py` | Analyst Workspace | Becomes notification adapter for investigation summaries. |
| `dashboard.py` | `src/sentinel_dna/workspace/cli.py` | Analyst Workspace | Becomes command-line analyst workflow. |
| `web_dashboard.py` | `src/sentinel_dna/workspace/web_app.py` | Analyst Workspace | Becomes Flask web analyst workspace. |

## New Sentinel DNA v0.1 Components

| Component | Files |
|---|---|
| Case Management Engine | `src/sentinel_dna/case_management/models.py`, `src/sentinel_dna/case_management/case_store.py` |
| Evidence Engine | `src/sentinel_dna/evidence/models.py`, `src/sentinel_dna/evidence/evidence_engine.py` |
| Risk Engine | `src/sentinel_dna/risk/risk_engine.py` |
| AI Investigation Engine | `src/sentinel_dna/ai_investigation/investigation_engine.py` |
| Analyst Workspace | `src/sentinel_dna/workspace/cli.py`, `src/sentinel_dna/workspace/web_app.py` |
| Integrations | `src/sentinel_dna/integrations/gmail_analyzer.py`, `src/sentinel_dna/integrations/slack_alert.py` |

