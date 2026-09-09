"""Shared types and enums for the Planka MCP server."""

from enum import StrEnum


class MembershipRole(StrEnum):
    """Board membership roles."""

    EDITOR = "editor"
    VIEWER = "viewer"


class AttachmentType(StrEnum):
    """Attachment types."""

    FILE = "file"
    LINK = "link"
