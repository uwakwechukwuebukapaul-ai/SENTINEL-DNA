\# Sentinel DNA Gate 5 Tailscale Access Architecture Record



Date:

2026-09-07



Branch:

gate5-controlled-analyst-pilot-preparation



Status:

ARCHITECTURE\_PREPARATION\_ONLY



\## Selected Access Model



Private analyst access:



Tailscale controlled private network access



Purpose:



Provide one bounded analyst connectivity path for a future controlled synthetic analyst pilot.



\## Architecture Boundary



Approved future path:



Analyst Device

&#x20;       |

&#x20;       | Tailscale encrypted private network

&#x20;       |

&#x20;       v

Approved staging access boundary

&#x20;       |

&#x20;       v

Sentinel DNA HTTPS edge

&#x20;       |

&#x20;       v

Sentinel DNA application





\## Explicitly Excluded



The access path must not expose:



\- public internet hostname

\- PostgreSQL

\- Redis

\- Docker daemon

\- SSH administration

\- repository access

\- production infrastructure

\- internal management interfaces



\## Security Requirements



Before activation:



\- approved analyst identity exists

\- device identity is approved

\- access expiry is defined

\- owner and rollback contact exist

\- staging backup validation exists

\- TLS validation exists

\- browser authentication validation exists



\## Sentinel DNA Controls Preserved



No changes are permitted to:



\- RBAC

\- tenant isolation

\- authentication flow

\- CSRF controls

\- audit logging

\- provenance tracking

\- AI authorization boundaries



\## Evidence Rule



A successful network connection is not analyst acceptance evidence.



Required future evidence:



\- analyst authentication

\- authorization verification

\- tenant isolation validation

\- investigation workflow execution

\- audit/provenance capture

\- revocation verification



\## Current State



Tailscale:



NOT\_CONFIGURED



Analyst:



NOT\_ACTIVATED



Pilot:



NOT\_STARTED



Production:



NOT\_DEPLOYED



Certification:



NOT\_GRANTED



\## Final Boundary



This document records architecture preparation only.



It does not authorize:



\- access creation

\- analyst onboarding

\- production deployment

\- external usage

