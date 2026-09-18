🧬 Sentinel DNA

<div align="center"><img src="assets/sentinel-dna-banner.png" width="900"/>Evidence-First AI Security Investigation Platform

Turn security alerts into evidence-backed investigations.

Collect evidence → correlate context → reconstruct attacks → explain reasoning → keep the analyst in control.

""Python" (https://img.shields.io/badge/Python-3.14-blue)"
""Flask" (https://img.shields.io/badge/Backend-Flask-black)"
""Docker" (https://img.shields.io/badge/Deployment-Docker-blue)"
""Security" (https://img.shields.io/badge/Focus-Cybersecurity-red)"

</div>---

🔎 What is Sentinel DNA?

Sentinel DNA is an AI security investigation platform built around an evidence-first approach to SOC investigations.

Instead of treating AI as a chatbot layered over security alerts, Sentinel DNA is designed around a structured investigation pipeline:

Security Alert
      ↓
Evidence Collection
      ↓
Investigation Orchestration
      ↓
Intelligence & IOC Enrichment
      ↓
Attack Reconstruction
      ↓
MITRE ATT&CK Mapping
      ↓
AI Reasoning
      ↓
Confidence & Evidence
      ↓
Investigation Report
      ↓
Analyst Decision

The objective is simple:

«Help security analysts move from an alert to an explainable understanding of what happened.»

Sentinel DNA is designed to support analyst decision-making — not replace analyst authority.

---

🧠 The Core Idea

Security operations generate enormous amounts of telemetry and alerts.

The difficult part is often not generating another alert.

It is answering:

- What actually happened?
- Which evidence supports that conclusion?
- What entities and indicators are connected?
- What attack sequence does the evidence suggest?
- Which MITRE ATT&CK techniques are relevant?
- What is known versus inferred?
- How confident should an analyst be in each conclusion?
- What should the analyst investigate next?

Sentinel DNA is being built around that investigation layer.

Alert
  ↓
Evidence
  ↓
Context
  ↓
Correlation
  ↓
Reasoning
  ↓
Confidence
  ↓
Analyst Decision

---

🏗️ Investigation Architecture

Sentinel DNA uses a modular investigation architecture designed to separate orchestration, evidence, intelligence, reasoning, and analyst interaction.

                    SECURITY ALERT
                          │
                          ▼
              InvestigationCoordinator
                          │
                          ▼
              InvestigationOrchestrator
                          │
                          ▼
                RuntimeTaskExecutor
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Evidence       Intelligence      Reasoning
      Services          Services         Services
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                InvestigationResult
                          │
                          ▼
                InvestigationReport
                          │
                          ▼
                 Analyst Workspace
                          │
                          ▼
                  Analyst Action

Investigation Context

Investigations operate around a tenant-scoped context containing the information required to preserve investigation boundaries and provenance.

Conceptually:

InvestigationContext
├── Tenant
├── Case
├── Alert
├── Evidence
├── IOCs
├── Timeline
├── Intelligence
└── Provenance

This architecture is intended to provide a foundation for increasingly sophisticated investigation capabilities without turning Sentinel DNA into a flat AI alert dashboard.

---

🔬 Evidence-First AI

A central design principle is that AI conclusions should remain connected to evidence.

Sentinel DNA is designed so that investigation output can distinguish between:

Evidence

Information directly observed or collected during an investigation.

Correlation

Relationships established between evidence, entities, indicators, events, and intelligence.

Inference

A conclusion derived from available evidence but not directly observed.

Confidence

A transparent indication of how strongly a claim is supported.

The intended analyst experience is therefore:

AI Claim
   │
   ├── Supporting Evidence
   ├── Investigation Context
   ├── Reasoning
   └── Confidence

Low-confidence conclusions should remain visible as conclusions requiring analyst review rather than being presented as established facts.

---

🛡️ Security & Trust Model

Sentinel DNA is being developed with security boundaries as part of the platform architecture.

Current security-oriented design includes:

- Tenant-aware application architecture
- Server-controlled authorization boundaries
- Analyst-role separation
- MFA enforcement before protected SOC access
- Server-side TOTP authentication
- Encrypted MFA secret storage
- TOTP replay protection
- Server-bound MFA sessions
- Authentication and security audit events
- Synthetic evaluation environments
- Evidence and provenance preservation
- Controlled investigation execution
- Production authorization boundaries

Security decisions are intended to remain explicit and auditable rather than being delegated blindly to an AI system.

---

👨‍💻 Analyst-First AI

Sentinel DNA is not designed around autonomous security authority.

The intended operating model is:

AI investigates
     ↓
AI explains
     ↓
AI exposes evidence
     ↓
AI communicates confidence
     ↓
Analyst evaluates
     ↓
Analyst decides

The analyst remains responsible for consequential security decisions.

This distinction is fundamental to the platform's design.

---

🧩 Investigation Capabilities

Evidence Collection

Structured collection and organization of investigation evidence.

IOC Intelligence

Enrichment and contextual analysis of indicators such as:

- IP addresses
- Domains
- URLs
- File hashes
- Other security observables

Threat Intelligence Correlation

Connect investigation evidence with available intelligence and reputation context.

MITRE ATT&CK Mapping

Map observed or inferred behavior to relevant MITRE ATT&CK techniques and attack patterns.

Attack Reconstruction

Transform individual observations into a chronological investigation narrative.

Event
  ↓
Evidence
  ↓
Relationship
  ↓
Technique
  ↓
Attack Sequence

AI Investigation Reports

Generate structured investigation results containing:

- Findings
- Evidence
- Reasoning
- Confidence
- Indicators
- Timeline
- ATT&CK context
- Analyst review points

Analyst Workspace

Provide analysts with a centralized investigation view rather than forcing them to reconstruct the case manually from disconnected alerts.

---

🧪 Validation & Development

Sentinel DNA follows a controlled engineering progression:

Build
  ↓
Test
  ↓
Harden
  ↓
Integrate
  ↓
Demonstrate
  ↓
Commercialize

The project currently prioritizes credibility engineering and external validation rather than uncontrolled feature expansion.

That means validating:

- Security boundaries
- Authentication
- Investigation behavior
- Evidence provenance
- Deployment integrity
- Release custody
- Analyst usability
- Independent evaluation

before making broader production claims.

---

🎯 Current Development Focus

AI Investigator V1

The current strategic foundation centers on:

Evidence-first investigation
        +
Explainable AI reasoning
        +
Confidence transparency
        +
Analyst control

The next major validation milestone is independent analyst evaluation using a controlled synthetic-data environment.

The intended evaluation model is:

Dedicated Evaluation Tenant
          ↓
Synthetic Investigation Cases
          ↓
Least-Privilege Analyst Access
          ↓
MFA
          ↓
Independent Investigation
          ↓
Structured Evaluation
          ↓
Preserved Evidence
          ↓
External Findings

No production customer data is required for this evaluation.

---

🗺️ Roadmap

V1 — Evidence-First AI Investigation

Current strategic foundation

- Investigation orchestration
- Evidence collection
- IOC enrichment
- Threat intelligence
- Attack reconstruction
- MITRE ATT&CK mapping
- Explainable reasoning
- Confidence-aware findings
- Investigation reporting
- Analyst workspace

---

V2.1 — Bounded Autonomous Investigation Runtime

Future work may introduce controlled autonomous investigation tasks with explicit boundaries.

The emphasis will remain on:

- Bounded execution
- Evidence requirements
- Permission boundaries
- Auditability
- Human oversight
- Failure containment

---

V2.2 — Organizational Cyber Memory

A governed organizational memory layer can eventually connect historical investigations and organizational knowledge.

This depends on establishing strong foundations for:

- Evidence provenance
- Tenant isolation
- Confidence
- Time validity
- Governance
- Access control

---

V3 — Organizational Cyber Intelligence Platform

Longer-term expansion may connect:

Investigations
      +
Evidence
      +
Organizational Knowledge
      +
Threat Intelligence
      +
Security Operations

into a governed organizational cyber-intelligence platform.

---

🏢 Enterprise Direction

Sentinel DNA is being designed with enterprise security operations in mind.

Potential integration areas include:

- SIEM platforms
- EDR/XDR platforms
- Cloud security systems
- Threat intelligence providers
- Identity systems
- Security data platforms
- SOAR workflows
- Enterprise APIs

The architecture is intentionally being developed so integrations can expand without changing the core investigation model.

---

🛠️ Technology Stack

Backend

- Python
- Flask
- SQLite
- PostgreSQL-compatible deployment architecture
- Redis
- Docker

Frontend

- HTML
- CSS
- JavaScript
- Bootstrap

Security & Intelligence

- MFA / TOTP
- MITRE ATT&CK
- IOC intelligence
- Threat analysis
- Audit logging
- Evidence provenance

---

🚀 Running Locally

Clone the repository:

git clone https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA.git

cd SENTINEL-DNA

Development Container

docker build -t sentinel-dna .

docker run --rm \
  --env-file .env \
  -p 5000:5000 \
  sentinel-dna

Open:

http://localhost:5000

Staging / Integration

For self-contained staging and integration validation:

docker-compose.yml
        │
        ├── Sentinel DNA
        ├── PostgreSQL
        ├── Redis
        └── Nginx edge

The application port remains internal to the composed environment.

Operators should provide required secrets and configuration through the environment rather than committing them to the repository.

For controlled production deployment, use the dedicated production deployment configuration under:

deployment/docker-compose.yml

Immutable release metadata and protected configuration should be validated before startup.

---

🔐 Security Principles

Sentinel DNA follows several core principles:

Evidence over assertion

AI conclusions should be connected to supporting evidence.

Transparency over false certainty

Confidence and uncertainty should be visible.

Analyst authority

AI assists investigations; analysts retain decision authority.

Least privilege

Users and services should receive only the permissions required for their role.

Tenant isolation

Investigation data must remain bounded by the appropriate tenant and authorization context.

Auditability

Security-sensitive actions should produce appropriate audit evidence.

Controlled autonomy

Future autonomous capabilities must operate within explicit technical and authorization boundaries.

---

📈 Product Thesis

Traditional security platforms are highly effective at collecting telemetry, generating detections, and presenting alerts.

Sentinel DNA is focused on the layer that follows:

Detection
   ↓
Investigation
   ↓
Understanding
   ↓
Decision

The product thesis is that AI can make this investigation layer substantially more structured and efficient without hiding the evidence or removing the analyst from the decision loop.

---

👨‍💻 Founder

Uwakwe chukwuebuka paul

Founder / Product Owner

Repository namespace:

uwakwechukwuebukapaul-ai

Repository and documentation maintainer:

Uwakwe chukwuebuka paul

This identity covers founder/product direction and repository/documentation custody only.

It does not assign production database, monitoring, on-call, incident response, backup, security approval, or independent review authority.

---

🤝 Collaboration

Sentinel DNA is open to discussions around:

- Cybersecurity engineering
- AI security
- SOC investigation
- Threat intelligence
- Security automation
- Detection engineering
- Enterprise security architecture
- AI-assisted security operations

---

⭐ Sentinel DNA

Security alerts tell analysts that something happened.

Sentinel DNA is being built to help investigate what happened — with evidence, context, reasoning, and analyst control.

ALERT
  ↓
EVIDENCE
  ↓
CONTEXT
  ↓
REASONING
  ↓
CONFIDENCE
  ↓
DECISION

Evidence-first AI investigation for modern security operations.