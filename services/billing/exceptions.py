class BillingError(Exception): pass
class BillingConfigurationError(BillingError): pass
class PaymentProviderError(BillingError): pass
class InvalidStateTransition(BillingError): pass
class WebhookVerificationError(BillingError): pass
