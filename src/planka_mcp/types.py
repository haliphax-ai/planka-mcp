"""Shared types and enums for the Planka MCP server."""

from enum import Enum


class MembershipRole(str, Enum):
    """Board membership roles."""

    EDITOR = "editor"
    VIEWER = "viewer"


class AttachmentType(str, Enum):
    """Attachment types."""

    FILE = "file"
    LINK = "link"
