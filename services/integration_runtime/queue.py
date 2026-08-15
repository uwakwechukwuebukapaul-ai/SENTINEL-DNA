from collections import deque
class ExecutionQueue:
    def __init__(self): self.items = deque()
    def enqueue(self, execution): self.items.append(execution); return execution
    def dequeue(self): return self.items.popleft() if self.items else None
    def __len__(self): return len(self.items)
