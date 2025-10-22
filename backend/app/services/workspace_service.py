from uuid import UUID
from app.db.queries.workspace_queries import create_workspace, add_member_to_workspace
from app.models.workspace import WorkspaceCreate, MemberRole

async def create_new_workspace(workspace_data: WorkspaceCreate, owner_id: UUID):
    new_workspace = create_workspace(
        name=workspace_data.name,
        workspace_type=workspace_data.type,
        owner_id=owner_id
    )
    if new_workspace:
        add_member_to_workspace(
            workspace_id=new_workspace["workspace_id"],
            user_id=owner_id,
            role=MemberRole.admin
        )
    return new_workspace