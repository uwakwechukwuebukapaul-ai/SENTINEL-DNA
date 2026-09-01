"""FAVP operations platform.

This package is an opt-in, synthetic-data-only operations layer.  It is kept
separate from the existing pilot authorization and trusted-browser services so
program management cannot grant application access or alter production gates.
"""

from .models import (
    FAVP_PROGRAM_STATES,
    FAVP_VALIDATION_PHASES,
    FAVP_SCORES,
)
from .repository import FAVPOperationsRepository
from .scenarios import FAVP_SCENARIOS, get_scenario
from .service import FAVPOperationsError, FAVPOperationsService
from .execution_scenarios import FAVP_EXECUTION_SCENARIOS, get_execution_scenario
from .readiness import FAVPExecutionReadiness, READY_FOR_FAVP_EXECUTION
from .execution import EXECUTION_STATES, FAVPExecutionError, FAVPExecutionService
from .activation import FAVPActivationError, FAVPParticipantActivationService
from .launch_readiness import FAVP_LAUNCH_BLOCKED, FAVP_LAUNCH_READY, FAVPStagingLaunchReadiness

__all__ = [
    "FAVP_PROGRAM_STATES",
    "FAVP_VALIDATION_PHASES",
    "FAVP_SCORES",
    "FAVP_SCENARIOS",
    "FAVPOperationsError",
    "FAVPOperationsRepository",
    "FAVPOperationsService",
    "FAVP_EXECUTION_SCENARIOS",
    "FAVPExecutionReadiness",
    "READY_FOR_FAVP_EXECUTION",
    "EXECUTION_STATES",
    "FAVPExecutionError",
    "FAVPExecutionService",
    "FAVPActivationError",
    "FAVPParticipantActivationService",
    "FAVP_LAUNCH_BLOCKED",
    "FAVP_LAUNCH_READY",
    "FAVPStagingLaunchReadiness",
    "get_execution_scenario",
    "get_scenario",
]
