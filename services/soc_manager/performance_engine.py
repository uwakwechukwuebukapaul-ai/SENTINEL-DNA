class PerformanceEngine:
 def metrics(self,tasks): return {"alert_volume":len(tasks),"completed":len([x for x in tasks if x.status=="COMPLETED"]),"automation_rate":0}
