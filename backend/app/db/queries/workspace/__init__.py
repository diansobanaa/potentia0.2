# File: backend/app/db/queries/workspace/__init__.py
# Export semua fungsi untuk backward compatibility

# CRUD Workspace
from .workspace_crud import (
    create_workspace,
    get_workspace_by_id,
    update_workspace,
    delete_workspace
)

# List/Paginasi Workspace
from .workspace_list import get_user_workspaces_paginated

# CRUD Workspace Members
from .workspace_members import (
    check_user_membership,
    add_member_to_workspace,
    list_workspace_members,
    update_workspace_member_role,
    remove_workspace_member
)

# Workspace Invitations
from .workspace_invitations import (
    create_workspace_invitation,
    respond_to_workspace_invitation
)

# Export semua fungsi untuk backward compatibility
# File lama workspace_queries.py dapat dihapus setelah semua import berfungsi
__all__ = [
    # CRUD Workspace
    "create_workspace",
    "get_workspace_by_id",
    "update_workspace",
    "delete_workspace",
    # List/Paginasi
    "get_user_workspaces_paginated",
    # CRUD Members
    "check_user_membership",
    "add_member_to_workspace",
    "list_workspace_members",
    "update_workspace_member_role",
    "remove_workspace_member",
    # Invitations
    "create_workspace_invitation",
    "respond_to_workspace_invitation",
]

