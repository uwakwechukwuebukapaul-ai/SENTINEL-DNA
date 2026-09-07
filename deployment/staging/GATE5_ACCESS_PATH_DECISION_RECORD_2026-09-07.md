\# Sentinel DNA Gate 5 Access Path Decision Record



Date:

2026-09-07



Branch:

gate5-controlled-analyst-pilot-preparation



Status:

DECISION\_RECORDED\_PREPARATION\_ONLY



\## Decision



Selected first analyst access path:



Tailscale controlled private access



\## Rationale



The first analyst access path must provide:



\- private connectivity only

\- no public exposure

\- explicit device identity

\- bounded access scope

\- easy revocation

\- auditable operator control



Cloudflare Zero Trust path:



Status:

PAUSED



Reason:



Reserved for future reviewed deployment.

Not selected for first analyst login.



\## Current Boundary



Access:



NOT\_ACTIVATED



Analyst:



NOT\_ONBOARDED



Production:



NOT\_DEPLOYED



Customer Access:



NOT\_AVAILABLE



\## Required Before Activation



The following must exist:



\- approved analyst identity

\- approved synthetic tenant

\- access expiry window

\- rollback owner

\- backup validation

\- runtime health validation

\- browser authentication validation

\- analyst evidence capture plan



\## Security Restrictions



Do not:



\- expose public hostname

\- modify application security controls

\- weaken TLS validation

\- bypass RBAC

\- bypass tenant isolation

\- create artificial analyst evidence



\## Final State



Gate 5 remains:



PREPARATION\_ONLY



No analyst access is authorized.

