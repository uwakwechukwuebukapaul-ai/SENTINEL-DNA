"""
Sentinel DNA Runtime Package

Compatibility facade for runtime architecture.

Maintains backward compatibility while exposing
new intelligence runtime components.
"""


__version__ = "1.0.0"


#
# Legacy Runtime Compatibility
#

from .execution_context import (
    ExecutionContext as RuntimeContext,
)


from .execution_result import (
    ExecutionResult as RuntimeResult,
)



#
# Investigation Runtime
#

from .investigation_runtime import (
    InvestigationRuntime,
)



#
# Intelligence Runtime
#

from .runtime_intelligence_context import (
    RuntimeIntelligenceContext,
)


from .runtime_intelligence_result import (
    RuntimeIntelligenceResult,
)


from .runtime_intelligence_service import (
    RuntimeIntelligenceService,
)


from .runtime_intelligence_controller import (
    RuntimeIntelligenceController,
)



#
# Compatibility aliases
#

IntelligenceContext = RuntimeIntelligenceContext

IntelligenceResult = RuntimeIntelligenceResult



__all__ = [

    # Legacy
    "RuntimeContext",
    "RuntimeResult",

    # Investigation
    "InvestigationRuntime",

    # Intelligence
    "RuntimeIntelligenceContext",
    "RuntimeIntelligenceResult",
    "RuntimeIntelligenceService",
    "RuntimeIntelligenceController",

    # Aliases
    "IntelligenceContext",
    "IntelligenceResult",

]