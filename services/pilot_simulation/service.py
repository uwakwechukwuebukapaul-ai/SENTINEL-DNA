from datetime import datetime,timezone
from uuid import uuid4
from .scenarios import PILOT_SCENARIOS, get_scenario
from .workflow import PilotDemoWorkflow
from .validation import PilotValidationService
class PilotSimulationService:
 def __init__(self): self.tenants={}; self.runs=[]; self.workflow=PilotDemoWorkflow(); self.validation=PilotValidationService()
 def scenarios(self): return [item.to_dict() for item in sorted(PILOT_SCENARIOS.values(), key=lambda item: item.scenario_id)]
 def scenario(self, scenario_id): return get_scenario(scenario_id).to_dict()
 def create_run(self, organization_id, scenario_id, case_id):
  get_scenario(scenario_id)
  item = {"run_id": f"PILOT-{uuid4().hex}", "organization_id": str(organization_id), "scenario_id": str(scenario_id), "case_id": str(case_id), "status": "created", "observations": [], "created_at": datetime.now(timezone.utc).isoformat()}
  self.runs.append(item); return dict(item)
 def run_investigation(self, **kwargs):
  item = self.get_run(kwargs["tenant_id"], kwargs.get("run_id")) if kwargs.get("run_id") else None
  if kwargs.get("run_id") and item is None: raise LookupError("pilot_run_not_found")
  if item is None: item = self.create_run(kwargs["tenant_id"], kwargs["scenario_id"], kwargs["case_id"])
  run_id = item["run_id"]
  stored = next(record for record in self.runs if record.get("run_id") == run_id and record.get("organization_id") == str(kwargs["tenant_id"]))
  item = stored
  if item.get("scenario_id") != str(kwargs["scenario_id"]) or item.get("case_id") != str(kwargs["case_id"]): raise ValueError("pilot_run_mismatch")
  if item.get("status") not in {"created", "failed"}: raise ValueError("pilot_run_not_executable")
  item["status"] = "running"
  try: result = self.workflow.execute(**kwargs); payload = result.to_dict()
  except Exception:
   item["status"] = "failed"
   raise
  item.update(payload, status="completed", organization_id=str(kwargs["tenant_id"]), observations=item["observations"])
  return dict(item)
 def get_run(self, organization_id, run_id):
  return next((dict(item) for item in self.runs if item.get("run_id") == str(run_id) and item.get("organization_id") == str(organization_id)), None)
 def record_observation(self, organization_id, run_id, observation):
  item = next((item for item in self.runs if item.get("run_id") == str(run_id) and item.get("organization_id") == str(organization_id)), None)
  if item is None: raise LookupError("pilot_run_not_found")
  allowed = {"investigation_usability", "evidence_usefulness", "finding_accuracy_feedback", "missing_information", "comment", "improvement_suggestion"}
  if not isinstance(observation, dict) or set(observation) - allowed: raise ValueError("invalid_pilot_observation")
  clean = {key: str(value).strip() for key, value in observation.items() if value not in (None, "")}
  if not clean: raise ValueError("pilot_observation_required")
  item["observations"].append(clean); return dict(item)
 def validation_report(self, organization_id, run_id, analyst_observations=None):
  run = next((item for item in self.runs if item.get("run_id") == str(run_id) and item.get("organization_id") == str(organization_id)), None)
  if run is None: raise LookupError("pilot_run_not_found")
  observations = [item.get("comment") for item in run.get("observations", []) if item.get("comment")] + list(analyst_observations or [])
  return self.validation.evaluate(run, observations)
 def configure_customer_pilot(self, organization_id, objectives=None):
  tenant = self.tenants.setdefault(str(organization_id), {"organization_id": str(organization_id), "created_at": datetime.now(timezone.utc).isoformat()})
  pilot = tenant.setdefault("customer_pilot", {"status": "created", "objectives": [], "checklist": {"deployment": False, "tenant_setup": False, "access": False, "first_investigation": False, "success_criteria": False}, "feedback": [], "history": []})
  if objectives is not None:
   if not isinstance(objectives, list) or not all(isinstance(value, str) and value.strip() for value in objectives): raise ValueError("invalid_pilot_objectives")
   pilot["objectives"] = sorted({value.strip() for value in objectives})
  return self.customer_pilot(organization_id)
 def advance_customer_pilot(self, organization_id, status, checklist=None):
  allowed = ("created", "customer_onboarding", "environment_verified", "scenarios_executed", "analyst_review", "outcome_assessment", "complete")
  if status not in allowed: raise ValueError("invalid_pilot_status")
  pilot = self.tenants.setdefault(str(organization_id), {}).setdefault("customer_pilot", {"status": "created", "objectives": [], "checklist": {"deployment": False, "tenant_setup": False, "access": False, "first_investigation": False, "success_criteria": False}, "feedback": [], "history": []})
  current = allowed.index(pilot["status"]); target = allowed.index(status)
  if target < current or target > current + 1: raise ValueError("invalid_pilot_transition")
  if checklist is not None:
   if not isinstance(checklist, dict) or set(checklist) - set(pilot["checklist"]): raise ValueError("invalid_onboarding_checklist")
   pilot["checklist"].update({key: bool(value) for key, value in checklist.items()})
  if status == "environment_verified" and not all(pilot["checklist"][key] for key in ("deployment", "tenant_setup", "access")): raise ValueError("environment_checklist_incomplete")
  if status == "scenarios_executed" and not any(item.get("status") == "completed" for item in self.runs if item.get("organization_id") == str(organization_id)): raise ValueError("completed_scenario_required")
  if status == "complete" and not any(item.get("status") == "completed" for item in self.runs if item.get("organization_id") == str(organization_id)): raise ValueError("completed_scenario_required")
  pilot["status"] = status; pilot["history"].append({"status": status, "recorded_at": datetime.now(timezone.utc).isoformat()})
  return self.customer_pilot(organization_id)
 def record_customer_feedback(self, organization_id, feedback):
  allowed = {"requested_improvement", "missing_integration", "workflow_friction", "useful_capability", "deployment_challenge", "comment"}
  if not isinstance(feedback, dict) or set(feedback) - allowed: raise ValueError("invalid_customer_feedback")
  clean = {key: str(value).strip() for key, value in feedback.items() if value not in (None, "")}
  if not clean: raise ValueError("customer_feedback_required")
  pilot = self.tenants.setdefault(str(organization_id), {}).setdefault("customer_pilot", {"status": "created", "objectives": [], "checklist": {"deployment": False, "tenant_setup": False, "access": False, "first_investigation": False, "success_criteria": False}, "feedback": [], "history": []})
  pilot["feedback"].append(clean); return self.customer_pilot(organization_id)
 def customer_pilot(self, organization_id):
  tenant = self.tenants.get(str(organization_id), {}); pilot = dict(tenant.get("customer_pilot") or {"status": "created", "objectives": [], "checklist": {"deployment": False, "tenant_setup": False, "access": False, "first_investigation": False, "success_criteria": False}, "feedback": [], "history": []})
  runs = [dict(item) for item in self.runs if item.get("organization_id") == str(organization_id) and item.get("run_id")]
  completed = [item for item in runs if item.get("status") == "completed"]
  pilot.update({"organization_id": str(organization_id), "scenario_progress": {"executed": len(completed), "available": len(PILOT_SCENARIOS), "completed_scenarios": sorted({item.get("scenario_id") for item in completed})}, "outcome_ready": bool(completed) and pilot.get("status") in {"outcome_assessment", "complete"}})
  return pilot
 def onboard(self,org,name="Enterprise Pilot"):
  x={"id":str(uuid4()),"organization_id":org,"name":name,"synthetic":True,"status":"ONBOARDED","users":[{"role":"SOC_ANALYST","name":"Demo Analyst"},{"role":"CISO","name":"Demo CISO"}],"assets":[{"name":"Finance Database","criticality":"CRITICAL"},{"name":"Corporate Laptop","criticality":"HIGH"}],"policies":["MFA required","Privileged access review"],"detection_rules":["Suspicious login","Ransomware behavior"],"threat_feeds":["Synthetic ATT&CK feed"],"investigation_history":[],"created_at":datetime.now(timezone.utc).isoformat()}; self.tenants[org]=x; return x
 def run(self,org,scenario):
  if org not in self.tenants:self.onboard(org)
  x={"id":str(uuid4()),"organization_id":org,"scenario":scenario,"synthetic":True,"incident_state":"RESOLVED","detection":"TRIGGERED","investigation":"COMPLETED","executive_summary":"Synthetic pilot scenario completed","created_at":datetime.now(timezone.utc).isoformat()}; self.runs.append(x); self.tenants[org]["investigation_history"].append(x); return x
 def view(self,org,mode): return {"mode":mode,"tenant":self.tenants.get(org),"runs":[x for x in self.runs if x["organization_id"]==org],"synthetic_only":True}
