"""Planka MCP Server — FastMCP-based tools for Planka project management."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from .client import PlankaClient

mcp = FastMCP("planka-mcp")

_client: PlankaClient | None = None


def _get_client() -> PlankaClient:
    global _client
    if _client is None:
        _client = PlankaClient()
    return _client


def _format_error(e: Exception) -> str:
    return f"Planka API error: {type(e).__name__}: {e}"


# =============================================================================
# Projects
# =============================================================================


@mcp.tool()
async def get_projects(page: int = 1, perPage: int = 25) -> str:
    """List all projects the user has access to."""
    try:
        result = await _get_client().get("projects", params={"page": page, "perPage": perPage})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_project(id: str) -> str:
    """Get a single project by ID."""
    try:
        result = await _get_client().get(f"projects/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_project(name: str, description: str = "", type: str = "shared") -> str:
    """Create a new project. Type can be 'private' or 'shared'."""
    try:
        result = await _get_client().post(
            "projects", data={"name": name, "description": description, "type": type}
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_project(id: str, name: str = "", description: str = "") -> str:
    """Update a project's name and/or description."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        result = await _get_client().patch(f"projects/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_project(id: str) -> str:
    """Delete a project."""
    try:
        result = await _get_client().delete(f"projects/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Boards
# =============================================================================


@mcp.tool()
async def get_boards(projectId: str) -> str:
    """List all boards in a project."""
    try:
        result = await _get_client().get(f"projects/{projectId}/boards")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_board(id: str) -> str:
    """Get a single board by ID."""
    try:
        result = await _get_client().get(f"boards/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_board(projectId: str, name: str, position: int = 65536) -> str:
    """Create a new board in a project."""
    try:
        result = await _get_client().post(
            f"projects/{projectId}/boards",
            data={"name": name, "position": position},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_board(id: str, name: str = "") -> str:
    """Update a board's name."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        result = await _get_client().patch(f"boards/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_board(id: str) -> str:
    """Delete a board."""
    try:
        result = await _get_client().delete(f"boards/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_board_summary(boardId: str) -> str:
    """Get a board summary with its lists, card counts, and labels."""
    try:
        client = _get_client()
        board = await client.get(f"boards/{boardId}")
        board_data = board.get("item", board)
        included = board.get("included", {})

        # Planka v2 nests all data in the board response
        lists_data = included.get("lists", [])
        labels_data = included.get("labels", [])

        summary = {
            "board": board_data,
            "lists": [
                {"id": lst.get("id"), "name": lst.get("name"), "type": lst.get("type")}
                for lst in lists_data
            ],
            "labels": labels_data,
        }
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_project_summary(projectId: str) -> str:
    """Get a project summary with all boards, their lists, and card counts."""
    try:
        client = _get_client()
        project = await client.get(f"projects/{projectId}")
        project_data = project.get("item", project)

        boards_result = await client.get(f"projects/{projectId}/boards")
        boards_data = boards_result.get("items", [])

        boards_summary = []
        for board in boards_data:
            board_id = board.get("id", "")
            # Fetch the board to get its included data (lists, cards)
            board_full = await client.get(f"boards/{board_id}")
            board_included = board_full.get("included", {})
            lists_data = board_included.get("lists", [])
            cards_data = board_included.get("cards", [])

            # Map list IDs to card counts
            cards_by_list: dict[str, int] = {}
            for card in cards_data:
                list_id = card.get("listId", "")
                cards_by_list[list_id] = cards_by_list.get(list_id, 0) + 1

            lists_with_cards = []
            for lst in lists_data:
                list_id = lst.get("id", "")
                lists_with_cards.append(
                    {
                        "id": list_id,
                        "name": lst.get("name"),
                        "type": lst.get("type"),
                        "cardCount": cards_by_list.get(list_id, 0),
                    }
                )

            boards_summary.append(
                {
                    "id": board_id,
                    "name": board.get("name"),
                    "lists": lists_with_cards,
                }
            )

        summary = {"project": project_data, "boards": boards_summary}
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Lists
# =============================================================================


@mcp.tool()
async def get_all_lists(boardId: str) -> str:
    """List all lists on a board.

    Extracts from board response since Planka nests lists.
    """
    try:
        board = await _get_client().get(f"boards/{boardId}")
        lists = board.get("item", {}).get("lists", []) or board.get("included", {}).get(
            "lists", []
        )
        return json.dumps({"items": lists}, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_list(id: str) -> str:
    """Get a single list by ID."""
    try:
        result = await _get_client().get(f"lists/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_list(
    boardId: str,
    name: str,
    position: int = 65536,
    type: str = "active",
) -> str:
    """Create a new list on a board. Type can be 'active' or 'closed'."""
    try:
        result = await _get_client().post(
            f"boards/{boardId}/lists",
            data={"name": name, "position": position, "type": type},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_list(id: str, name: str = "", type: str = "") -> str:
    """Update a list's name and/or type ('active' or 'closed')."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if type:
            data["type"] = type
        result = await _get_client().patch(f"lists/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_list(id: str) -> str:
    """Delete a list."""
    try:
        result = await _get_client().delete(f"lists/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Cards
# =============================================================================


@mcp.tool()
async def get_all_cards(listId: str) -> str:
    """List all cards in a list.

    Extracts from list response since Planka nests cards.
    """
    try:
        list_data = await _get_client().get(f"lists/{listId}")
        cards = list_data.get("item", {}).get("cards", []) or list_data.get("included", {}).get(
            "cards", []
        )
        return json.dumps({"items": cards}, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_card(id: str) -> str:
    """Get a single card by ID."""
    try:
        result = await _get_client().get(f"cards/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_card_details(cardId: str) -> str:
    """Get a card with all its details: tasks, comments, labels, and attachments."""
    try:
        client = _get_client()
        card = await client.get(f"cards/{cardId}")
        card_data = card.get("item", card)
        included = card.get("included", {})

        # Planka v2 nests all data in the card response
        tasks = included.get("tasks", [])
        comments = included.get("comments", [])
        labels = included.get("labels", [])
        attachments = included.get("attachments", [])

        details = {
            "card": card_data,
            "tasks": tasks,
            "comments": comments,
            "labels": labels,
            "attachments": attachments,
        }
        return json.dumps(details, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_card(
    listId: str,
    name: str,
    description: str = "",
    dueDate: str = "",
    position: int = 65536,
) -> str:
    """Create a new card in a list. dueDate should be ISO 8601 format."""
    try:
        data: dict[str, Any] = {"name": name, "position": position, "type": "project"}
        if description:
            data["description"] = description
        if dueDate:
            data["dueDate"] = dueDate
        result = await _get_client().post(f"lists/{listId}/cards", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_card_with_tasks(
    listId: str,
    name: str,
    tasks: list[str],
    description: str = "",
) -> str:
    """Create a card with task checklist items. Provide task names as a list of strings."""
    try:
        client = _get_client()
        card_data: dict[str, Any] = {"name": name, "type": "project"}
        if description:
            card_data["description"] = description
        card_result = await client.post(f"lists/{listId}/cards", data=card_data)
        card_item = card_result.get("item", card_result)
        card_id = card_item.get("id")

        created_tasks = []
        for i, task_name in enumerate(tasks):
            task_result = await client.post(
                f"cards/{card_id}/tasks",
                data={"name": task_name, "position": 65536 * (i + 1)},
            )
            created_tasks.append(task_result.get("item", task_result))

        result = {"card": card_item, "tasks": created_tasks}
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_card(
    id: str,
    name: str = "",
    description: str = "",
    dueDate: str = "",
    isClosed: bool | None = None,
    position: int | None = None,
) -> str:
    """Update a card's fields. Only specified fields are updated."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        if dueDate:
            data["dueDate"] = dueDate
        if isClosed is not None:
            data["isClosed"] = isClosed
        if position is not None:
            data["position"] = position
        result = await _get_client().patch(f"cards/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def move_card(id: str, listId: str, position: int = 65536) -> str:
    """Move a card to another list at a specific position. Use 65535 for end of list."""
    try:
        result = await _get_client().patch(
            f"cards/{id}", data={"listId": listId, "position": position}
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def duplicate_card(id: str, listId: str, position: int = 65536) -> str:
    """Duplicate a card into another list (or the same list)."""
    try:
        result = await _get_client().post(
            f"cards/{id}/copy",
            data={"listId": listId, "position": position},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_card(id: str) -> str:
    """Delete a card."""
    try:
        result = await _get_client().delete(f"cards/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def assign_parent_card(id: str, parentCardId: str) -> str:
    """Set the parent card for a card, creating a parent-child (subtask) relationship."""
    try:
        result = await _get_client().patch(f"cards/{id}", data={"parentCardId": parentCardId})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def attach_file_to_card(cardId: str, file_path: str, name: str = "") -> str:
    """Upload a file attachment to a card. Provide the absolute file path."""
    try:
        import os

        if not os.path.isfile(file_path):
            return f"Error: File not found: {file_path}"
        if not name:
            name = os.path.basename(file_path)

        result = await _get_client().upload(
            f"cards/{cardId}/attachments",
            file_path=file_path,
            file_name=name,
            extra_fields={"type": "file", "name": name},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Tasks
# =============================================================================


@mcp.tool()
async def get_all_tasks(cardId: str) -> str:
    """List all tasks (checklist items) on a card. Extracts from card response."""
    try:
        card = await _get_client().get(f"cards/{cardId}")
        tasks = card.get("item", {}).get("tasks", []) or card.get("included", {}).get("tasks", [])
        return json.dumps({"items": tasks}, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


async def _ensure_task_list(client, card_id: str) -> str:
    """Get or create a task list for a card. Returns the task list ID."""
    card = await client.get(f"cards/{card_id}")
    included = card.get("included", {})
    task_lists = included.get("taskLists", [])

    # Find a task list matching this card
    for tl in task_lists:
        if tl.get("cardId") == card_id:
            return tl["id"]

    # No task list exists — create one
    result = await client.post(
        f"cards/{card_id}/task-lists",
        data={"name": "Tasks", "position": 65535},
    )
    tl_item = result.get("item", result)
    return tl_item["id"]


@mcp.tool()
async def create_task(cardId: str, name: str, position: int = 65536) -> str:
    """Create a single task on a card."""
    try:
        client = _get_client()
        task_list_id = await _ensure_task_list(client, cardId)
        result = await client.post(
            f"task-lists/{task_list_id}/tasks",
            data={"name": name, "position": position},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def batch_create_tasks(tasks: list[dict[str, str]]) -> str:
    """Create multiple tasks at once. Each item should have 'cardId' and 'name' keys.

    Example: [{"cardId": "123", "name": "Task 1"}, {"cardId": "123", "name": "Task 2"}]
    """
    try:
        client = _get_client()
        created = []
        for i, task in enumerate(tasks):
            card_id = task.get("cardId", "")
            task_name = task.get("name", "")
            if not card_id or not task_name:
                created.append({"error": f"Missing cardId or name at index {i}"})
                continue
            task_list_id = await _ensure_task_list(client, card_id)
            result = await client.post(
                f"task-lists/{task_list_id}/tasks",
                data={"name": task_name, "position": 65536 * (i + 1)},
            )
            created.append(result.get("item", result))
        return json.dumps({"items": created}, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_task(id: str) -> str:
    """Get a single task by ID."""
    try:
        result = await _get_client().get(f"tasks/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_task(id: str, name: str = "", isCompleted: bool | None = None) -> str:
    """Update a task's name or completion status."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if isCompleted is not None:
            data["isCompleted"] = isCompleted
        result = await _get_client().patch(f"tasks/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_task(id: str) -> str:
    """Delete a task."""
    try:
        result = await _get_client().delete(f"tasks/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def complete_task(id: str) -> str:
    """Toggle a task's completion status."""
    try:
        client = _get_client()
        task_result = await client.get(f"tasks/{id}")
        task_data = task_result.get("item", task_result)
        current = task_data.get("isCompleted", False)
        result = await client.patch(f"tasks/{id}", data={"isCompleted": not current})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Labels
# =============================================================================


@mcp.tool()
async def get_all_labels(boardId: str) -> str:
    """List all labels on a board."""
    try:
        result = await _get_client().get(f"boards/{boardId}/labels")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_label(boardId: str, name: str, color: str, position: int = 65536) -> str:
    """Create a new label on a board. Color should be a Planka color name like 'muddy-grey'."""
    try:
        result = await _get_client().post(
            f"boards/{boardId}/labels",
            data={"name": name, "color": color, "position": position},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_label(id: str, name: str = "", color: str = "") -> str:
    """Update a label's name and/or color."""
    try:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        result = await _get_client().patch(f"labels/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_label(id: str) -> str:
    """Delete a label."""
    try:
        result = await _get_client().delete(f"labels/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def add_label_to_card(cardId: str, labelId: str) -> str:
    """Add a label to a card."""
    try:
        result = await _get_client().post(
            f"cards/{cardId}/labels",
            data={"labelId": labelId},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def remove_label_from_card(cardId: str, labelId: str) -> str:
    """Remove a label from a card."""
    try:
        result = await _get_client().delete(f"cards/{cardId}/labels/{labelId}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Comments
# =============================================================================


@mcp.tool()
async def get_all_comments(cardId: str) -> str:
    """List all comments on a card."""
    try:
        result = await _get_client().get(f"cards/{cardId}/comments")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_comment(cardId: str, text: str) -> str:
    """Add a comment to a card."""
    try:
        result = await _get_client().post(
            f"cards/{cardId}/comments",
            data={"text": text},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_comment(id: str) -> str:
    """Get a single comment by ID."""
    try:
        result = await _get_client().get(f"comments/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_comment(id: str, text: str) -> str:
    """Update a comment's text."""
    try:
        result = await _get_client().patch(f"comments/{id}", data={"text": text})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_comment(id: str) -> str:
    """Delete a comment."""
    try:
        result = await _get_client().delete(f"comments/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Stopwatches
# =============================================================================


@mcp.tool()
async def start_stopwatch(id: str) -> str:
    """Start the stopwatch on a card."""
    try:
        result = await _get_client().patch(f"cards/{id}", data={"isEditingStopwatch": True})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def stop_stopwatch(id: str) -> str:
    """Stop the stopwatch on a card."""
    try:
        result = await _get_client().patch(f"cards/{id}", data={"isEditingStopwatch": False})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_stopwatch(id: str) -> str:
    """Get the stopwatch status for a card."""
    try:
        result = await _get_client().get(f"cards/{id}")
        card_data = result.get("item", result)
        stopwatch = {
            "cardId": id,
            "isEditingStopwatch": card_data.get("isEditingStopwatch", False),
            "stopwatchTotal": card_data.get("stopwatchTotal", 0),
            "stopwatchStartedAt": card_data.get("stopwatchStartedAt"),
        }
        return json.dumps(stopwatch, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def reset_stopwatch(id: str) -> str:
    """Reset the stopwatch on a card (clears accumulated time)."""
    try:
        result = await _get_client().patch(
            f"cards/{id}",
            data={
                "stopwatchTotal": 0,
            },
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Memberships
# =============================================================================


@mcp.tool()
async def get_all_memberships(boardId: str) -> str:
    """List all memberships on a board."""
    try:
        result = await _get_client().get(f"boards/{boardId}/memberships")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_membership(boardId: str, userId: str, role: str = "editor") -> str:
    """Add a member to a board. Role can be 'editor' or 'viewer'."""
    try:
        result = await _get_client().post(
            f"boards/{boardId}/memberships",
            data={"userId": userId, "role": role},
        )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_membership(id: str) -> str:
    """Get a single membership by ID."""
    try:
        result = await _get_client().get(f"memberships/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def update_membership(id: str, role: str = "") -> str:
    """Update a membership's role."""
    try:
        data: dict[str, Any] = {}
        if role:
            data["role"] = role
        result = await _get_client().patch(f"memberships/{id}", data=data)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_membership(id: str) -> str:
    """Remove a member from a board."""
    try:
        result = await _get_client().delete(f"memberships/{id}")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Users
# =============================================================================


@mcp.tool()
async def get_users() -> str:
    """List all users the current account can see."""
    try:
        result = await _get_client().get("users")
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _format_error(e)


# =============================================================================
# Entry point
# =============================================================================


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
