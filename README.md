# 🧬 Sentinel DNA

<div align="center">

<img src="assets/sentinel-dna-banner.png" width="900"/>

### AI-Powered SOC Investigation Platform

**Turning security alerts into evidence-backed investigations**

[![Python](https://img.shields.io/badge/Python-3.14-blue)]()
[![Flask](https://img.shields.io/badge/Backend-Flask-black)]()
[![Docker](https://img.shields.io/badge/Deployment-Docker-blue)]()
[![Security](https://img.shields.io/badge/Focus-Cybersecurity-red)]()

</div>


---

# 🚨 What is Sentinel DNA?

Sentinel DNA is an AI SOC investigation platform designed to help security analysts investigate threats faster through:

- AI-assisted investigations
- Evidence collection and analysis
- IOC enrichment
- MITRE ATT&CK mapping
- Threat intelligence correlation
- Investigation reports
- Analyst decision support


---

# 🎯 Vision

Modern SOC teams face:

- Alert fatigue
- Slow investigations
- Too much manual correlation
- Limited analyst time

Sentinel DNA aims to become an **AI investigation layer for security operations**, helping analysts understand:

> "What happened, why it happened, and what should we do next?"


---

# 🧠 AI Investigator Workflow


```
Security Alert

      ↓

Evidence Collection

      ↓

IOC Intelligence

      ↓

Threat Analysis

      ↓

MITRE ATT&CK Mapping

      ↓

Attack Timeline Reconstruction

      ↓

AI Investigation Report

      ↓

Analyst Decision
```


---

# 🏗️ Architecture


```
                 SOC Alert
                    |
                    |
        Investigation Coordinator
                    |
                    |
        Investigation Orchestrator
                    |
     --------------------------------
     |              |               |
 Evidence       Intelligence     Timeline
 Engine         Engine           Engine

                    |

            Investigation Report

                    |

            Analyst Workspace

```


---

# 🔥 Current Features


## ✅ AI Investigation Engine

- Automated investigation workflow
- Evidence-driven reasoning
- Structured investigation context


## ✅ Threat Intelligence

- IOC enrichment
- Reputation analysis
- Threat context


## ✅ MITRE ATT&CK Integration

- Technique mapping
- Attack sequence reconstruction


## ✅ Analyst Workspace

- Investigation visibility
- Case intelligence
- Decision support


## ✅ Enterprise Foundation

- Tenant-aware architecture
- Security controls
- Modular services


---

# 📊 Project Status

## AI Investigator V1

Status:

🟢 Core Foundation Complete
🟢 Validation Passed
🟡 AI Investigator Demonstration Phase


Validation:

```
Validation:

✅ Automated test suite passing
✅ Python compilation checks passing
✅ Runtime validation completed
```


---

# 🛠️ Technology Stack


Backend:

- Python
- Flask
- SQLite
- Docker


Security:

- MITRE ATT&CK
- IOC Intelligence
- Threat Analysis


Frontend:

- HTML
- CSS
- JavaScript
- Bootstrap


---

# 🚀 Running Locally


Clone repository:

```bash
git clone https://github.com/YOUR_USERNAME/Sentinel-DNA.git
```


Development-only direct container run:

```bash
docker build -t sentinel-dna .

docker run --rm \
--env-file .env \
-p 5000:5000 \
sentinel-dna
```


Open:

```
http://localhost:5000
```

For production, use only `deployment/docker-compose.yml`. nginx publishes port 80 and the application port 5000 remains internal-only. Derive immutable image metadata with `deployment/scripts/release_metadata.py` and validate protected configuration before startup; never use the root Compose file for production.


---

# 🗺️ Roadmap


## Phase 1 ✅

Foundation

- Core architecture
- Investigation engine
- Evidence pipeline


## Phase 2 ✅

AI Investigator V1

- Investigation workflow
- Reports
- Analyst workspace


## Phase 3 🚧

Enterprise Expansion

- SIEM integrations
- EDR connectors
- SOAR automation
- Cloud deployment
- Multi-tenant SaaS


---

# 👨‍💻 Founder Note

Sentinel DNA focuses on reducing investigation time while keeping analysts in control of security decisions.

Founder / Product Owner: `Uwakwe chukwuebuka paul`

Repository namespace: `uwakwechukwuebukapaul-ai`

Repository and documentation maintainer: `Uwakwe chukwuebuka paul`

This identity covers founder/product direction and repository/documentation
custody only. It does not assign production database, monitoring, on-call,
incident response, backup, security approval, or independent review authority.


---

# Why Sentinel DNA?

Traditional security tools generate alerts.

Sentinel DNA focuses on the investigation process:

Alert → Evidence → Context → Reasoning → Decision

The goal is to help analysts move from detection to understanding faster.

___
# 🤝 Collaboration

Interested in:

- Cybersecurity engineering
- AI security
- SOC automation
- Threat intelligence

Open to discussions and collaboration.


---

⭐ Star the project if you believe AI can transform security operations.
