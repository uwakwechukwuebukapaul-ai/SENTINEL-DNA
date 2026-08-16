from .exceptions import InvalidStateTransition
from .models import PaymentStatus, SubscriptionStatus

PAYMENT_TRANSITIONS = {
    "PENDING": {"SUCCESS", "FAILED", "CANCELLED"},
    "SUCCESS": {"REFUNDED", "DISPUTED"},
    "FAILED": set(), "CANCELLED": set(), "REFUNDED": set(), "DISPUTED": set(),
}
SUBSCRIPTION_TRANSITIONS = {
    "PENDING": {"ACTIVE", "CANCELLED", "EXPIRED"},
    "ACTIVE": {"PAST_DUE", "CANCELLED", "EXPIRED"},
    "PAST_DUE": {"ACTIVE", "CANCELLED", "EXPIRED"},
    "CANCELLED": set(), "EXPIRED": set(),
}
def require_transition(table, current, target):
    if target not in table.get(current, set()): raise InvalidStateTransition("billing_transition_not_allowed")
