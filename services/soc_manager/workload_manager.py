class WorkloadManager:
 def capacity(self,tasks,agents): return {"queue_size":len([x for x in tasks if x.status not in ("COMPLETED","FAILED")]),"agents":len(agents),"active_tasks":len([x for x in tasks if x.status=="RUNNING"])}
