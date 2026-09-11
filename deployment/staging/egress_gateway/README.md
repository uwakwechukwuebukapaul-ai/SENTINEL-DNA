# Gate4 dedicated egress gateway

This source-side gateway is the only component attached to both the internal
trusted-browser egress network and the injected external uplink. It resolves
destinations itself, validates the immutable policy digest, rejects private and
special-use addresses, and revalidates DNS immediately before connection.

The gateway intentionally exposes no generic HTTP proxy or CONNECT chaining
surface. A production transport adapter must call the explicit authorization
boundary and fail closed when policy, resolver, or gateway readiness fails.

All image, bind address, port, policy path, policy digest, and network identity
are deployment-injected.
