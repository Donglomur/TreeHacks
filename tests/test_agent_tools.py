import pytest

from faers_agent.agent import ClaudeFAERSAgent


@pytest.mark.asyncio
async def test_tool_definitions_include_screen_and_suggest():
    defs = ClaudeFAERSAgent.tool_definitions()
    names = {tool["name"] for tool in defs}
    assert ClaudeFAERSAgent.SCREEN_TOOL_NAME in names
    assert ClaudeFAERSAgent.SUGGEST_EVENTS_TOOL_NAME in names


@pytest.mark.asyncio
async def test_handle_tool_call_suggest_events_formats_output():
    agent = ClaudeFAERSAgent(api_key=None)

    async def fake_top_event_terms(*, drug, limit):
        assert drug == "metformin"
        assert limit == 5
        return [("Nausea", 123), ("Headache", 42)]

    agent.detector.client.top_event_terms = fake_top_event_terms

    result = await agent.handle_tool_call(
        ClaudeFAERSAgent.SUGGEST_EVENTS_TOOL_NAME,
        {"drug": "metformin", "limit": 5},
    )

    assert result["drug"] == "metformin"
    assert result["limit"] == 5
    assert result["events"] == [
        {"term": "Nausea", "count": 123},
        {"term": "Headache", "count": 42},
    ]


@pytest.mark.asyncio
async def test_handle_tool_call_unknown_name_raises():
    agent = ClaudeFAERSAgent(api_key=None)
    with pytest.raises(ValueError, match="Unknown tool"):
        await agent.handle_tool_call("does_not_exist", {})
