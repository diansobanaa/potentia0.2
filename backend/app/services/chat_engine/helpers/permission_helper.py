"""
User permission management based on subscription tier.
"""
import logging
from typing import List

from app.models.user import User, SubscriptionTier

logger = logging.getLogger(__name__)


class PermissionHelper:
    """Helper class for managing user permissions."""
    
    @staticmethod
    def get_user_permissions(user: User) -> List[str]:
        """
        Get list of permissions (scopes) based on user's subscription tier.
        
        Args:
            user: User model instance
            
        Returns:
            List[str]: List of permission strings (e.g., "tool:search_online")
        """
        base_permissions = ["tool:search_online"]
        
        tier = user.subscription_tier
        
        # Pro & Admin users get additional tools
        if tier in (SubscriptionTier.pro, SubscriptionTier.admin):
            base_permissions.extend([
                "tool:create_schedule_tool",
                "tool:create_canvas_block"
            ])
        
        # Admin users get admin access
        if tier == SubscriptionTier.admin:
            base_permissions.append("tool:admin_access")
        
        logger.debug(f"Permissions for user {user.id} (tier: {tier}): {base_permissions}")
        return base_permissions
