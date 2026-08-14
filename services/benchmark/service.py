from time import perf_counter
class BenchmarkService:
    def run(self, operation, workload, handler):
        started = perf_counter(); result = [handler(item) for item in workload]; elapsed = (perf_counter() - started) * 1000; return {"operation": operation, "items": len(workload), "elapsed_ms": round(elapsed, 2), "throughput_per_second": round(len(workload) / (elapsed / 1000), 2) if elapsed else 0, "result_count": len(result)}
    def ingestion(self, events, handler): return self.run("ingestion", events, handler)
    def detection(self, events, handler): return self.run("detection", events, handler)
    def investigation(self, alerts, handler): return self.run("investigation", alerts, handler)
    def ai_response(self, prompts, handler): return self.run("ai_response", prompts, handler)
    def api_load(self, requests, handler): return self.run("api_load", requests, handler)
