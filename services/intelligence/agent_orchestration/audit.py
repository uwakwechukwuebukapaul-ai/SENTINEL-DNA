import sqlite3
class AgentAuditLogger:
 def __init__(self,database=":memory:"): self.db=sqlite3.connect(database); self.db.execute("create table if not exists agent_audit (event text, agent_id text, payload text)"); self.db.commit()
 def record(self,event,agent_id="",payload=""): self.db.execute("insert into agent_audit values (?,?,?)",(event,agent_id,str(payload))); self.db.commit(); return {"event":event,"agent_id":agent_id,"payload":payload}
