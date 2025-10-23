from uuid import UUID
from app.db.queries.workspace_queries import create_workspace, add_member_to_workspace
from app.models.workspace import WorkspaceCreate, MemberRole

async def create_new_workspace(authed_client, workspace_data: WorkspaceCreate, user_id: UUID):
    
    new_workspace = create_workspace(
        authed_client, 
        name=workspace_data.name,
        workspace_type=workspace_data.type,
        owner_id=user_id  
    )
    
    if new_workspace:
        add_member_to_workspace(
            authed_client, 
            workspace_id=new_workspace["workspace_id"],
            user_id=user_id, 
            role=MemberRole.admin
        )
    return new_workspace