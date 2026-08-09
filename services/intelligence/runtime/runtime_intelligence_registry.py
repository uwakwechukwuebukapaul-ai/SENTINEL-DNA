"""
Runtime Intelligence Registry

Dependency registry for intelligence components.

Provides:
- component registration
- capability discovery
- provider lookup
- lifecycle management
- runtime status reporting
"""


class RuntimeIntelligenceRegistry:
    """
    Registry for runtime intelligence providers.
    """

    def __init__(self):

        self.components = {}


    # -------------------------------------------------
    # Registration
    # -------------------------------------------------

    def register(
        self,
        name: str,
        component,
    ):
        """
        Register intelligence component.
        """

        self.components[name] = component

        return component


    # -------------------------------------------------
    # Retrieval
    # -------------------------------------------------

    def get(
        self,
        name: str,
    ):
        """
        Retrieve component.
        """

        return self.components.get(name)


    def available(self):
        """
        Return registered provider names.
        """

        return list(
            self.components.keys()
        )


    # -------------------------------------------------
    # Compatibility API
    # -------------------------------------------------

    def count(self):
        """
        Return number of registered providers.
        """

        return len(
            self.components
        )


    def exists(
        self,
        name: str,
    ):
        """
        Check if provider exists.
        """

        return name in self.components


    def find_provider(
        self,
        capability: str,
    ):
        """
        Find provider implementing capability.

        Supports:
        - dict capability declarations
        - list/tuple/set declarations
        - string capability
        - object capabilities
        - metadata capabilities
        """

        for name, component in self.components.items():

            capabilities = []


            # Dictionary based provider
            if isinstance(
                component,
                dict,
            ):

                capabilities = component.get(
                    "capabilities",
                    [],
                )


            # List based provider
            elif isinstance(
                component,
                (list, tuple, set),
            ):

                capabilities = component


            # Single capability string
            elif isinstance(
                component,
                str,
            ):

                capabilities = [
                    component
                ]


            # Object capability
            elif hasattr(
                component,
                "capabilities",
            ):

                capabilities = component.capabilities


            # Metadata capability
            elif hasattr(
                component,
                "metadata",
            ):

                metadata = component.metadata


                if isinstance(
                    metadata,
                    dict,
                ):

                    capabilities = metadata.get(
                        "capabilities",
                        [],
                    )


                elif hasattr(
                    metadata,
                    "capabilities",
                ):

                    capabilities = metadata.capabilities


            if capability in capabilities:

                return name


        return None


    def unregister(
        self,
        name: str,
    ):
        """
        Remove provider.
        """

        return self.components.pop(
            name,
            None,
        )


    def remove(
        self,
        name: str,
    ):
        """
        Backward compatibility alias.
        """

        return self.unregister(name)


    def clear(self):
        """
        Remove all providers.
        """

        self.components.clear()


    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    def status(self):
        """
        Return registry health information.
        """

        modules = self.available()

        return {
            "healthy": True,
            "count": len(modules),
            "modules": modules,
            "components": modules,
            "registered": modules,
        }