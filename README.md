# planka-mcp

MCP server for [Planka](https://planka.app) project management. Provides tools for managing projects, boards, lists, cards, tasks, labels, comments, stopwatches, and memberships.

## Configuration

Set these environment variables:

- `PLANKA_BASE_URL` — The base URL of your Planka instance (e.g. `https://planka.example.com`)
- `PLANKA_API_TOKEN` — Your Planka API token (from Account → API Tokens)

## Development

```bash
# Install dependencies
uv sync

# Run the MCP server
uv run python -m planka_mcp
```

## Tools

This server exposes 50+ MCP tools covering:

- **Projects**: get/create/update/delete
- **Boards**: get/create/update/delete, summaries
- **Lists**: get/create/update/delete
- **Cards**: get/create_cards/update/move_cards/delete_cards/duplicate (all batch-aware), details, parent-child, file attachments
- **Tasks**: get/create/batch create/update/delete/toggle complete
- **Labels**: get/create/update/delete, add/remove from cards
- **Comments**: get/create/update/delete
- **Stopwatches**: start/stop/get/reset
- **Memberships**: get/create/update/delete
- **Users**: list users
