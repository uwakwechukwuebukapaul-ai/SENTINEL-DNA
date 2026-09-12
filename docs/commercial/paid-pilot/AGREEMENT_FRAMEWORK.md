# Paid Pilot Agreement Framework

This framework is a drafting aid for legal review. It is not a contract or legal advice. Customer-specific terms, data-processing terms, service descriptions, and order forms must be approved by authorized legal and security reviewers.

## Agreement structure

1. Master agreement or applicable commercial terms.
2. Paid Pilot Order Form.
3. Pilot scope and success-criteria schedule.
4. Security and data-handling schedule.
5. Support and escalation schedule.
6. NDA or confidentiality terms, if not already incorporated.
7. Data-processing or privacy addendum, where required.

## Required provisions

### Parties, scope, and fees

Identify the contracting entities, customer tenant, authorized users, package, workflows, environments, integrations, duration, deliverables, fees, taxes, invoicing, and change-order process. The order form must say which limits are hard limits and what happens when they are reached.

### Data handling

Define approved data classes, purpose limitation, locations, access roles, retention, export, deletion, subprocessors, incident notification, and customer instructions. Synthetic or sanitized data is the default. Production data requires explicit approval and must not be introduced by implication.

Credentials, cookies, tokens, browser sessions, and authentication secrets must not be stored in the pilot artifacts. Any external authentication or browser capability remains subject to the approved trusted boundary and customer authorization.

### Confidentiality and publication

The NDA should identify confidential information, permitted recipients, compelled disclosure, exclusions, handling, return/deletion, and survival. No customer name, logo, quote, metric, case study, or result may be published without a separate written approval under the Customer Proof System.

### Security requirements

Specify identity and access controls, least privilege, tenant isolation, audit logging, evidence custody, vulnerability reporting, change control, origin or integration restrictions, and access revocation. The customer remains responsible for its own endpoint, identity, network, and incident-response controls unless expressly stated otherwise.

### AI limitations and human authority

The product may generate recommendations or structured analysis. The agreement must state that outputs can be incomplete or incorrect, require human review, and do not replace customer policy, analyst judgment, legal advice, or incident-response authority. Sentinel DNA must not be described as making a final security decision.

### Intellectual property and feedback

Each party retains pre-existing IP. The agreement should define ownership of customer data, customer-created work product, Sentinel DNA software, derived telemetry, and feedback. Any permitted use of de-identified feedback must exclude confidential content and be limited to the agreed purpose.

### Liability, warranties, and limitations

Legal review must define disclaimers, service commitments, liability allocation, consequential-damages treatment, indemnities if any, and the customer’s responsibilities. Do not promise detection coverage, risk reduction, compliance, uptime, or savings unless an approved agreement expressly supports the statement.

### Termination and access revocation

Define termination for convenience, breach, security event, non-payment, scope violation, or unsafe operation. On termination or expiry, Sentinel DNA and the customer must revoke access, stop data ingestion, export or delete artifacts as agreed, close integrations, and record the disposition.

### Pilot transition clauses

State that a paid pilot ends on the order-form date unless renewed or replaced. An annual subscription requires a new or converted order form, commercial approval, security review, and any required procurement steps. Unused pilot fees, credits, or implementation work are governed only by expressly approved terms.

## NDA relationship

An NDA protects confidential business and technical information; it does not authorize system access, data ingestion, production use, public claims, or a security exception. Access and data permissions belong in the pilot agreement and security schedule.

## Signature and approval checklist

- `[ ]` Business sponsor and authorized signatory confirmed.
- `[ ]` Security/privacy review complete.
- `[ ]` Data-processing terms complete where required.
- `[ ]` Scope, package, limits, fees, and dates approved.
- `[ ]` Success criteria and stop conditions approved.
- `[ ]` NDA/confidentiality coverage confirmed.
- `[ ]` Access, evidence custody, retention, and deletion confirmed.
- `[ ]` Human decision authority and AI limitations included.
- `[ ]` Legal approval reference recorded: `[Reference]`.
