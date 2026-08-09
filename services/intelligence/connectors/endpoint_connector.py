"""
Endpoint Response Connector.

Future integrations:

- CrowdStrike Falcon
- SentinelOne
- Defender
"""

from __future__ import annotations

from typing import Any

from .base_connector import BaseConnector



class EndpointConnector(BaseConnector):

    name = "endpoint"



    def execute(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:


        return {

            "connector":
                self.name,


            "action":
                action,


            "endpoint":
                payload.get(
                    "endpoint"
                ),


            "status":
                "executed",
        }