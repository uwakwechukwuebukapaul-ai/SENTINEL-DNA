import json,sqlite3
class AgentMemoryRepository:
 def __init__(self,database=":memory:"): self.db=sqlite3.connect(database); self.db.execute("create table if not exists experiences (id text primary key, tenant text, agent text, case_id text, payload text)"); self.db.commit()
 def save_experience(self,x): self.db.execute("insert or ignore into experiences values(?,?,?,?,?)",(x.experience_id,x.tenant_id,x.agent_id,x.case_id,json.dumps(x.to_dict()))); self.db.commit(); return x
 def get_experiences(self,tenant_id,agent_id=None):
  rows=self.db.execute("select payload from experiences where tenant=? and (? is null or agent=?)",(tenant_id,agent_id,agent_id)).fetchall(); return [json.loads(r[0]) for r in rows]
