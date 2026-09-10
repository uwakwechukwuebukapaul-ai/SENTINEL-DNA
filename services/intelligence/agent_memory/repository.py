import json
from pathlib import Path

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection

class AgentMemoryRepository:
 def __init__(self,database: str | Path | DatabaseBackend = ":memory:"):
  self.backend = database if hasattr(database, "connect") else DatabaseConnection(database)
  self.db = self.backend.connect()
  self.db.execute("create table if not exists experiences (id text primary key, tenant text, agent text, case_id text, payload text)")
  self.db.commit()
 def save_experience(self,x):
  self.db.execute("insert into experiences(id,tenant,agent,case_id,payload) values(?,?,?,?,?) on conflict (id) do nothing",(x.experience_id,x.tenant_id,x.agent_id,x.case_id,json.dumps(x.to_dict())))
  self.db.commit()
  return x
 def get_experiences(self,tenant_id,agent_id=None):
  rows=self.db.execute("select payload from experiences where tenant=? and (? is null or agent=?)",(tenant_id,agent_id,agent_id)).fetchall(); return [json.loads(r["payload"]) for r in rows]
