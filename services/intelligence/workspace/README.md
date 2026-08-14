# AI SOC analyst workspace foundation

The workspace layer is a read-only presentation boundary. It aggregates
existing investigation, evidence, threat intelligence, reasoning, detection,
attack-path, SOAR, and compliance outputs without owning those engines.

All repository reads can be tenant-scoped, services expose audit hooks, and
missing intelligence is represented as partial availability. Future Flask
routes can map directly to the service methods without granting mutation or
SOAR execution privileges.
