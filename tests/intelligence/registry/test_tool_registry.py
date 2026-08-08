from services.intelligence.registry import (
    ToolRegistry,
)



def fake_tool(data):

    return {
        "result": data
    }



def test_register_tool():

    registry = ToolRegistry()


    registry.register(
        "ioc_lookup",
        fake_tool,
    )


    assert (
        registry.exists(
            "ioc_lookup"
        )
    )



def test_execute_tool():

    registry = ToolRegistry()


    registry.register(
        "ioc_lookup",
        fake_tool,
    )


    result = registry.execute(
        "ioc_lookup",
        "8.8.8.8",
    )


    assert (
        result["result"]
        == "8.8.8.8"
    )



def test_list_tools():

    registry = ToolRegistry()


    registry.register(
        "mitre",
        fake_tool,
    )


    assert (
        "mitre"
        in registry.list_tools()
    )



def test_unknown_tool():

    registry = ToolRegistry()


    assert (
        registry.get(
            "missing"
        )
        is None
    )