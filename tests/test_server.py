"""Unit tests for Planka MCP server tool schemas and API calls."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

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
        "get_all_cards", "get_card", "get_card_details", "create_card",
        "create_card_with_tasks", "update_card", "move_card", "duplicate_card",
        "delete_card", "assign_parent_card", "attach_file_to_card",
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
async def test_create_card_sends_type():
    """Verify create_card sends the required 'type' field."""
    with patch("planka_mcp.server._get_client") as mock_get:
        client = AsyncMock()
        mock_get.return_value = client
        client.post.return_value = {"item": {"id": "123", "name": "test"}}

        from planka_mcp.server import create_card
        await create_card("list-1", "Test Card")

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

        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            tmp_path = f.name

        try:
            from planka_mcp.server import attach_file_to_card
            await attach_file_to_card("card-1", tmp_path)
            client.upload.assert_called_once()
            assert client.upload.call_args[0][0] == "cards/card-1/attachments"
        finally:
            os.unlink(tmp_path)


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
