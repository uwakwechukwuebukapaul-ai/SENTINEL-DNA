from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class PaymentStatus(str, Enum): PENDING="PENDING"; SUCCESS="SUCCESS"; FAILED="FAILED"; CANCELLED="CANCELLED"; REFUNDED="REFUNDED"; DISPUTED="DISPUTED"
class SubscriptionStatus(str, Enum): TRIAL="TRIAL"; ACTIVE="ACTIVE"; PAST_DUE="PAST_DUE"; CANCELLED="CANCELLED"; EXPIRED="EXPIRED"
@dataclass(frozen=True)
class Plan: plan_id: str; amount_minor: int; currency: str; interval: str; capabilities: frozenset[str]
@dataclass(frozen=True)
class PaymentInitialization: tenant_id: str; transaction_reference: str; plan_id: str; amount_minor: int; currency: str; authorization_url: str
@dataclass(frozen=True)
class PaymentVerificationResult: transaction_reference: str; provider_reference: str; status: PaymentStatus; amount_minor: int; currency: str; paid_at: str|None=None
@dataclass(frozen=True)
class Subscription: tenant_id: str; plan_id: str; status: SubscriptionStatus
@dataclass(frozen=True)
class Entitlement: tenant_id: str; plan_id: str; capabilities: frozenset[str]
PLANS: Mapping[str, Plan] = {
 "FREE": Plan("FREE", 0, "NGN", "monthly", frozenset()),
 "PRO": Plan("PRO", 0, "NGN", "monthly", frozenset({"investigations", "hunting"})),
 "BUSINESS": Plan("BUSINESS", 0, "NGN", "monthly", frozenset({"investigations", "hunting", "copilot"})),
 "ENTERPRISE": Plan("ENTERPRISE", 0, "NGN", "monthly", frozenset({"investigations", "hunting", "copilot", "sso"})),
}
