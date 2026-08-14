# SOC Command Center API

This read-only blueprint exposes `SOCWorkspaceService` to dashboards and analyst clients. Routes are thin API adapters; authentication uses the existing security context and no investigation or intelligence logic is duplicated. Future clients include React, WebSocket, mobile, external integrations, and MSSP tenant APIs.
