"""Server-owned onboarding states and transition validation."""

from __future__ import annotations


class OnboardingState:
    """Canonical state names for the account onboarding lifecycle.

    The browser may display these values, but it cannot advance them.  This
    module deliberately contains no persistence; AuthService owns persistence
    and calls these guards inside its database boundary.
    """

    NEW = "NEW"
    EMAIL_VERIFICATION_REQUIRED = "EMAIL_VERIFICATION_REQUIRED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    PHONE_VERIFICATION_REQUIRED = "PHONE_VERIFICATION_REQUIRED"
    PHONE_VERIFIED = "PHONE_VERIFIED"
    PROFILE_REQUIRED = "PROFILE_REQUIRED"
    PROFILE_COMPLETED = "PROFILE_COMPLETED"
    WORKSPACE_PROVISIONING = "WORKSPACE_PROVISIONING"
    PROVISIONING_FAILED = "PROVISIONING_FAILED"
    WORKSPACE_READY = "WORKSPACE_READY"
    AUTHENTICATED = "AUTHENTICATED"

    ALL = frozenset(
        {
            NEW,
            EMAIL_VERIFICATION_REQUIRED,
            EMAIL_VERIFIED,
            PHONE_VERIFICATION_REQUIRED,
            PHONE_VERIFIED,
            PROFILE_REQUIRED,
            PROFILE_COMPLETED,
            WORKSPACE_PROVISIONING,
            PROVISIONING_FAILED,
            WORKSPACE_READY,
            AUTHENTICATED,
        }
    )

    TRANSITIONS = {
        NEW: {EMAIL_VERIFICATION_REQUIRED},
        EMAIL_VERIFICATION_REQUIRED: {EMAIL_VERIFIED},
        EMAIL_VERIFIED: {PHONE_VERIFICATION_REQUIRED},
        PHONE_VERIFICATION_REQUIRED: {PHONE_VERIFIED},
        PHONE_VERIFIED: {PROFILE_REQUIRED},
        PROFILE_REQUIRED: {PROFILE_COMPLETED},
        PROFILE_COMPLETED: {WORKSPACE_PROVISIONING},
        WORKSPACE_PROVISIONING: {WORKSPACE_READY, PROVISIONING_FAILED},
        PROVISIONING_FAILED: {WORKSPACE_PROVISIONING},
        WORKSPACE_READY: {AUTHENTICATED},
        AUTHENTICATED: set(),
    }

    @classmethod
    def validate(cls, state: str) -> str:
        normalized = str(state or "").strip().upper()
        if normalized not in cls.ALL:
            raise ValueError("invalid_onboarding_state")
        return normalized

    @classmethod
    def next(cls, current: str, target: str) -> str:
        current = cls.validate(current)
        target = cls.validate(target)
        if current == target:
            return target
        if target not in cls.TRANSITIONS.get(current, set()):
            raise ValueError("invalid_onboarding_transition")
        return target


def initial_state(*, legacy_compatibility: bool = False) -> str:
    """Return the only initial state accepted for a new account.

    The compatibility value exists solely for the explicitly gated legacy
    non-production API path.  Browser/production registration starts before
    verification and must advance through server-side transitions.
    """

    return (
        OnboardingState.AUTHENTICATED
        if legacy_compatibility
        else OnboardingState.NEW
    )


__all__ = ["OnboardingState", "initial_state"]
