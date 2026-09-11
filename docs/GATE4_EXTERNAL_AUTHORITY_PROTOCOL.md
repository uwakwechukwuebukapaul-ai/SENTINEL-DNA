\# Gate 4 External Authority Protocol



\## Purpose



Defines external trust requirements required before Gate 4 authorization.



\## Authority Separation



The following identities must be independent:



Requester

!=

Builder

!=

Signer

!=

Evidence Producer

!=

Evidence Retriever

!=

EvidenceVerifier

!=

Approver

!=

Reviewer



\## EvidenceVerifier Requirements



The verifier must provide:



\- authenticated identity

\- public trust root

\- signed responses

\- revocation status

\- freshness validation



\## Response Requirements



Required fields:



\- request\_id

\- nonce

\- request\_hash

\- candidate\_tuple\_hash

\- evidence\_digest

\- verification\_result

\- verified\_at

\- expires\_at

\- verifier\_identity

\- signature



\## Replay Protection



Requirements:



\- unique request\_id

\- nonce generation

\- durable replay tracking

\- signed replay rejection



\## Evidence Digest Responsibility



Evidence bytes must be:



1\. Retrieved externally

2\. Hashed independently

3\. Compared against claimed digest



\## Approval Boundary



External authority may authorize evidence trust.



Sentinel DNA decides Gate 4 PASS/BLOCKED.



External authority does not deploy.

Sentinel DNA does not self-approve.



