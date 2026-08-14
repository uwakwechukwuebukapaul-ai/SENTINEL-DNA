from datetime import datetime, timezone
class WorkerReliability:
    def __init__(self): self.workers = {}; self.retry_queue = []; self.dead_letter_queue = []
    def register(self, worker_id, worker_type): self.workers[worker_id] = {"worker_id": worker_id, "type": worker_type, "status": "registered", "last_heartbeat": None, "restarts": 0}; return self.workers[worker_id]
    def heartbeat(self, worker_id):
        if worker_id not in self.workers: raise LookupError("worker_not_registered")
        self.workers[worker_id].update(status="healthy", last_heartbeat=datetime.now(timezone.utc).isoformat()); return self.workers[worker_id]
    def retry(self, event, attempts=0):
        if attempts >= 3: self.dead_letter_queue.append(event); return "dead_letter"
        self.retry_queue.append({"event": event, "attempts": attempts + 1}); return "retry"
    def recover(self, worker_id): self.workers[worker_id]["restarts"] += 1; self.workers[worker_id]["status"] = "recovering"; return self.workers[worker_id]
