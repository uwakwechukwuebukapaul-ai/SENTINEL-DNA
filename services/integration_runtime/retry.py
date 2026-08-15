class RetryPolicy:
    def __init__(self, max_attempts=3): self.max_attempts = max(1, int(max_attempts))
    def should_retry(self, execution): return execution.attempts < self.max_attempts
