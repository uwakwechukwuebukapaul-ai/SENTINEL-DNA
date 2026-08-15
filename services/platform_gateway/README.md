# Enterprise Platform Gateway

`platform_gateway` is the access boundary for Sentinel DNA. It authenticates requests, validates tenant and permission scope, delegates to already-registered domain services, records audit events, and exposes health information.

It intentionally contains no investigation, intelligence, connector, or response logic. JWT/OAuth integration is provided through `TokenAuthenticationProvider`; development authentication is disabled unless explicitly enabled. Missing tenant context is denied and never upgraded to a privileged fallback.

`PlatformGateway.dispatch()` is suitable for future Flask routes and other adapters. All domain handlers should accept `tenant_id` and enforce their own service contracts as well.
