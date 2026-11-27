"""Verify-after-write behavior for move_cards and update_cards.

Planka's card PATCH endpoint returns the post-write card, so success claims are
checked against the returned item instead of the mere absence of an HTTP error.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from planka_mcp.server import move_cards, update_cards


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the global client before each test."""
    import planka_mcp.server as srv

    srv._client = None
    yield


@pytest.mark.asyncio
async def test_move_applied_reports_succeeded():
    """A PATCH whose returned card shows the target list is reported as succeeded."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "card-1", "listId": "target-list"}}

        result = await move_cards(["card-1"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1"]
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_move_silently_dropped_reports_failed():
    """A 2xx PATCH that leaves the card in the old list is reported as failed."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "card-1", "listId": "old-list"}}

        result = await move_cards(["card-1"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["cardId"] == "card-1"
        assert "move not applied" in parsed["failed"][0]["error"]
        assert "old-list" in parsed["failed"][0]["error"]


@pytest.mark.asyncio
async def test_move_same_list_reports_succeeded():
    """Moving a card within its current list still counts as a successful move."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "card-1", "listId": "target-list"}}

        result = await move_cards(["card-1"], "target-list", position=1000)

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1"]
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_move_response_without_list_id_reports_failed():
    """A response without a verifiable listId must not be counted as a move."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {}}

        result = await move_cards(["card-1"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert parsed["failed"][0]["cardId"] == "card-1"
        assert "move not applied" in parsed["failed"][0]["error"]


@pytest.mark.asyncio
async def test_move_http_error_reports_failed():
    """Non-2xx PATCH responses are still classified as failed."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        result = await move_cards(["card-1"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["cardId"] == "card-1"
        assert "error" in parsed["failed"][0]


@pytest.mark.asyncio
async def test_move_continues_after_dropped_card():
    """A dropped move is reported per card without aborting the rest of the batch."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.side_effect = [
            {"item": {"id": "card-1", "listId": "target-list"}},
            {"item": {"id": "card-2", "listId": "old-list"}},
            {"item": {"id": "card-3", "listId": "target-list"}},
        ]

        result = await move_cards(["card-1", "card-2", "card-3"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1", "card-3"]
        assert parsed["failed"] == [
            {"cardId": "card-2", "error": "move not applied (card still in list 'old-list')"}
        ]
        assert client.patch.call_count == 3


@pytest.mark.asyncio
async def test_update_applied_reports_succeeded():
    """A PATCH whose returned card shows the new verifiable values is succeeded."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {
            "item": {"id": "card-1", "name": "Renamed", "isClosed": True}
        }

        result = await update_cards([
            {"id": "card-1", "name": "Renamed", "isClosed": True, "position": 2048}
        ])

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1"]
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_update_silently_dropped_reports_failed():
    """A 2xx PATCH whose returned card lacks the new values is reported as failed."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "card-1", "name": "Old Name"}}

        result = await update_cards([{"id": "card-1", "name": "New Name"}])

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["id"] == "card-1"
        assert "update not applied" in parsed["failed"][0]["error"]
        assert "name" in parsed["failed"][0]["error"]


@pytest.mark.asyncio
async def test_update_position_only_keeps_current_behavior():
    """Position is not verifiable (server may reposition); no false negatives."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "card-1"}}

        result = await update_cards([{"id": "card-1", "position": 2048}])

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1"]
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_update_due_date_not_verified():
    """dueDate is normalized server-side (ISO with time), so it is not verified."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {
            "item": {"id": "card-1", "dueDate": "2026-12-31T00:00:00.000Z"}
        }

        result = await update_cards([{"id": "card-1", "dueDate": "2026-12-31"}])

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1"]
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_update_http_error_reports_failed():
    """Non-2xx PATCH responses are still classified as failed."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        result = await update_cards([{"id": "card-1", "name": "New Name"}])

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["id"] == "card-1"
        assert "error" in parsed["failed"][0]


@pytest.mark.asyncio
async def test_update_continues_after_dropped_card():
    """A dropped update is reported per card without aborting the rest of the batch."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.side_effect = [
            {"item": {"id": "card-1", "name": "New Name"}},
            {"item": {"id": "card-2", "name": "Old Name"}},
            {"item": {"id": "card-3", "name": "New Name"}},
        ]

        result = await update_cards([
            {"id": "card-1", "name": "New Name"},
            {"id": "card-2", "name": "New Name"},
            {"id": "card-3", "name": "New Name"},
        ])

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1", "card-3"]
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["id"] == "card-2"
        assert "update not applied" in parsed["failed"][0]["error"]
        assert client.patch.call_count == 3
