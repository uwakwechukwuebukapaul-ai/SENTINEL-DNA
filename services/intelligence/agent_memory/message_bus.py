class AgentMessageBus:
 def __init__(self): self.messages=[]
 def publish(self,message): self.messages.append(message); return message
 def receive(self,recipient,tenant_id): return [m for m in self.messages if m.recipient==recipient and m.tenant_id==tenant_id]
