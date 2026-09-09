"""Unit tests for Planka MCP server tool schemas and API calls."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from planka_mcp.server import mcp


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the global client before each test."""
    import planka_mcp.server as srv
    srv._client = None
    yield


def test_tool_count():
    """Verify all expected tools are registered."""
    tools = asyncio.run(mcp.list_tools())
    tool_names = {t.name for t in tools}
    expected = {
        "get_projects", "get_project", "create_project", "update_project",
        "delete_project", "get_boards", "get_board", "create_board",
        "update_board", "delete_board", "get_board_summary", "get_project_summary",
        "get_all_lists", "get_list", "create_list", "update_list", "delete_list",
        "get_all_cards", "get_card", "get_card_details", "create_cards",
        "create_card_with_tasks", "update_card", "move_cards", "duplicate_card",
        "delete_cards", "assign_parent_card", "attach_file_to_card",
        "get_all_tasks", "create_task", "batch_create_tasks", "get_task",
        "update_task", "delete_task", "complete_task",
        "get_all_labels", "create_label", "update_label", "delete_label",
        "add_label_to_card", "remove_label_from_card",
        "get_all_comments", "create_comment", "get_comment", "update_comment",
        "delete_comment", "start_stopwatch", "stop_stopwatch", "get_stopwatch",
        "reset_stopwatch", "get_all_memberships", "create_membership",
        "get_membership", "update_membership", "delete_membership", "get_users",
    }
    missing = expected - tool_names
    assert not missing, f"Missing tools: {missing}"



@pytest.mark.asyncio
async def test_create_cards_sends_type():
    """Verify create_cards sends the required 'type' field."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.return_value = {"item": {"id": "123", "name": "test"}}

        from planka_mcp.server import create_cards
        await create_cards("list-1", [{"name": "Test Card"}])

        post_data = client.post.call_args[1]["data"]
        assert post_data["type"] == "project"
        assert post_data["name"] == "Test Card"


@pytest.mark.asyncio
async def test_create_project_sends_type():
    """Verify create_project sends the required 'type' field."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.return_value = {"item": {"id": "123"}}

        from planka_mcp.server import create_project
        await create_project("Test Project", project_type="private")

        post_data = client.post.call_args[1]["data"]
        assert post_data["type"] == "private"


@pytest.mark.asyncio
async def test_create_list_sends_type():
    """Verify create_list sends 'type' field using list_type param."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.return_value = {"item": {"id": "1"}}

        from planka_mcp.server import create_list
        await create_list("board-1", "My List", list_type="closed")

        post_data = client.post.call_args[1]["data"]
        assert post_data["type"] == "closed"


@pytest.mark.asyncio
async def test_create_task_uses_task_list_endpoint():
    """Verify create_task goes through task lists, not cards/{id}/tasks."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.get.return_value = {
            "item": {"id": "card-1"},
            "included": {"taskLists": [{"id": "tl-1", "cardId": "card-1"}]},
        }
        client.post.return_value = {"item": {"id": "task-1", "name": "My Task"}}

        from planka_mcp.server import create_task
        await create_task("card-1", "My Task")

        assert client.post.call_count == 1
        post_path = client.post.call_args[0][0]
        assert post_path == "task-lists/tl-1/tasks", f"Got: {post_path}"


@pytest.mark.asyncio
async def test_create_task_creates_task_list_if_needed():
    """Verify create_task creates a task list when none exists."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.get.return_value = {
            "item": {"id": "card-1"},
            "included": {"taskLists": []},
        }
        client.post.side_effect = [
            {"item": {"id": "new-tl-1"}},
            {"item": {"id": "task-1"}},
        ]

        from planka_mcp.server import create_task
        await create_task("card-1", "New Task")

        first_path = client.post.call_args_list[0][0][0]
        assert "cards/card-1/task-lists" in first_path
        second_path = client.post.call_args_list[1][0][0]
        assert "task-lists/new-tl-1/tasks" in second_path


@pytest.mark.asyncio
async def test_get_all_tasks_extracts_from_included():
    """Verify get_all_tasks reads from included.tasks."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.get.return_value = {
            "item": {"id": "card-1"},
            "included": {
                "tasks": [
                    {"id": "t1", "name": "Task 1"},
                    {"id": "t2", "name": "Task 2"},
                ],
            },
        }

        from planka_mcp.server import get_all_tasks
        result = await get_all_tasks("card-1")

        parsed = json.loads(result)
        assert len(parsed["items"]) == 2
        assert parsed["items"][0]["name"] == "Task 1"


@pytest.mark.asyncio
async def test_get_all_cards_extracts_from_included():
    """Verify get_all_cards reads from list included.cards."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.get.return_value = {
            "item": {"id": "list-1"},
            "included": {
                "cards": [
                    {"id": "c1", "name": "Card 1"},
                    {"id": "c2", "name": "Card 2"},
                ],
            },
        }

        from planka_mcp.server import get_all_cards
        result = await get_all_cards("list-1")

        parsed = json.loads(result)
        assert len(parsed["items"]) == 2


@pytest.mark.asyncio
async def test_assign_parent_card():
    """Verify assign_parent_card patches with parentCardId."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {"id": "child-1"}}

        from planka_mcp.server import assign_parent_card
        await assign_parent_card("child-1", "parent-1")

        post_data = client.patch.call_args[1]["data"]
        assert post_data["parentCardId"] == "parent-1"


@pytest.mark.asyncio
async def test_attach_file_calls_upload():
    """Verify attach_file_to_card calls the upload method."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.upload.return_value = {"item": {"id": "att-1"}}

        import os
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            tmp_path = f.name

        try:
            from planka_mcp.server import attach_file_to_card
            await attach_file_to_card("card-1", tmp_path)
            client.upload.assert_called_once()
        finally:
            os.unlink(tmp_path)


@pytest.mark.asyncio

@pytest.mark.asyncio
async def test_move_cards_all_succeed():
    """Verify move_cards moves all cards and reports success."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.return_value = {"item": {}}

        from planka_mcp.server import move_cards
        result = await move_cards(["card-1", "card-2", "card-3"], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1", "card-2", "card-3"]
        assert parsed["failed"] == []
        assert client.patch.call_count == 3
        for call in client.patch.call_args_list:
            assert call[1]["data"]["listId"] == "target-list"


@pytest.mark.asyncio
async def test_move_cards_partial_failure():
    """Verify move_cards reports errors without aborting."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.patch.side_effect = [
            {"item": {}},
            httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            ),
            {"item": {}},
        ]

        from planka_mcp.server import move_cards
        result = await move_cards(["card-1", "card-2", "card-3"], "target-list")

        parsed = json.loads(result)
        assert "card-1" in parsed["succeeded"]
        assert "card-3" in parsed["succeeded"]
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["cardId"] == "card-2"
        assert "error" in parsed["failed"][0]


@pytest.mark.asyncio
async def test_move_cards_empty_list():
    """Verify move_cards with empty input returns empty results."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client

        from planka_mcp.server import move_cards
        result = await move_cards([], "target-list")

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_delete_cards_all_succeed():
    """Verify delete_cards deletes all cards and reports success."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.delete.return_value = {"item": {}}

        from planka_mcp.server import delete_cards
        result = await delete_cards(["card-1", "card-2", "card-3"])

        parsed = json.loads(result)
        assert parsed["succeeded"] == ["card-1", "card-2", "card-3"]
        assert parsed["failed"] == []
        assert client.delete.call_count == 3
        for call in client.delete.call_args_list:
            assert call[0][0].startswith("cards/")


@pytest.mark.asyncio
async def test_delete_cards_partial_failure():
    """Verify delete_cards reports errors without aborting."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.delete.side_effect = [
            {"item": {}},
            httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            ),
            {"item": {}},
        ]

        from planka_mcp.server import delete_cards
        result = await delete_cards(["card-1", "card-2", "card-3"])

        parsed = json.loads(result)
        assert "card-1" in parsed["succeeded"]
        assert "card-3" in parsed["succeeded"]
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["cardId"] == "card-2"
        assert "error" in parsed["failed"][0]


@pytest.mark.asyncio
async def test_delete_cards_empty_list():
    """Verify delete_cards with empty input returns empty results."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client

        from planka_mcp.server import delete_cards
        result = await delete_cards([])

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert parsed["failed"] == []


@pytest.mark.asyncio
async def test_create_cards_all_succeed():
    """Verify create_cards creates all cards and reports success."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.return_value = {"item": {"id": "new-card"}}

        from planka_mcp.server import create_cards
        result = await create_cards("list-1", [
            {"name": "Card A"},
            {"name": "Card B", "description": "desc"},
            {"name": "Card C", "dueDate": "2026-12-31"},
        ])

        parsed = json.loads(result)
        assert len(parsed["succeeded"]) == 3
        assert parsed["failed"] == []
        assert client.post.call_count == 3
        for call in client.post.call_args_list:
            assert call[0][0].startswith("lists/list-1/cards")
            assert call[1]["data"]["type"] == "project"


@pytest.mark.asyncio
async def test_create_cards_partial_failure():
    """Verify create_cards reports errors without aborting."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.side_effect = [
            {"item": {"id": "card-1"}},
            httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400),
            ),
            {"item": {"id": "card-3"}},
        ]

        from planka_mcp.server import create_cards
        result = await create_cards("list-1", [
            {"name": "Card A"},
            {"name": "Card B"},
            {"name": "Card C"},
        ])

        parsed = json.loads(result)
        assert len(parsed["succeeded"]) == 2
        assert parsed["succeeded"][0]["name"] == "Card A"
        assert parsed["succeeded"][1]["name"] == "Card C"
        assert len(parsed["failed"]) == 1
        assert parsed["failed"][0]["name"] == "Card B"
        assert "error" in parsed["failed"][0]


@pytest.mark.asyncio
async def test_create_cards_empty_list():
    """Verify create_cards with empty input returns empty results."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client

        from planka_mcp.server import create_cards
        result = await create_cards("list-1", [])

        parsed = json.loads(result)
        assert parsed["succeeded"] == []
        assert parsed["failed"] == []
        client.post.assert_not_called()



@pytest.mark.asyncio
async def test_batch_create_tasks():
    """Verify batch_create_tasks processes multiple tasks through task lists."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.get.return_value = {
            "item": {"id": "card-1"},
            "included": {"taskLists": [{"id": "tl-1", "cardId": "card-1"}]},
        }
        client.post.return_value = {"item": {"id": "task-1"}}

        from planka_mcp.server import batch_create_tasks
        result = await batch_create_tasks([
            {"cardId": "card-1", "name": "Task A"},
            {"cardId": "card-1", "name": "Task B"},
        ])

        parsed = json.loads(result)
        assert len(parsed["items"]) == 2
        for call in client.post.call_args_list:
            assert "task-lists/tl-1/tasks" in call[0][0]
