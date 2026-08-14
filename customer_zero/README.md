# Customer Zero SOC Simulation

Customer Zero provides deterministic synthetic alert scenarios for demonstrations and validation. It only produces API-shaped data; it never executes commands, sends network traffic, or touches production systems.

```python
from customer_zero import CustomerZeroSimulator

payload = CustomerZeroSimulator(seed=7).api_payload("phishing")
```

Send `payload` to the existing `POST /api/investigations` contract.
