from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field

class AutonomyLevel(str, Enum):
    MANUAL = "manual"
    SUPERVISED = "supervised"
    ADVISORY = "advisory"

class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class PermissionStrategy(str, Enum):
    EARLY = "early"       # Ask before planning
    STANDARD = "standard" # Ask before execution
    LATE = "late"         # Ask just before the specific risky tool call

class RoleContext(BaseModel):
    role_name: str
    domain: str
    behavioral_goals: str
    priority_weights: Dict[str, float] = Field(default_factory=dict)
    communication_style: str
    autonomy_level: AutonomyLevel = Field(default=AutonomyLevel.SUPERVISED)
    risk_tolerance: RiskTolerance = Field(default=RiskTolerance.MEDIUM)
    permission_strategy: PermissionStrategy = Field(default=PermissionStrategy.STANDARD)
    memory_focus: str = Field(..., description="What this role should focus on remembering")

from typing import Callable, Awaitable, Any
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_ai import RunContext

PermissionCallback = Callable[[str, str, str], Awaitable[bool]] # command_summary, exact_operation, risk_level -> approved

class AgentDeps:
    def __init__(self, session: AsyncSession, role_context: Optional[RoleContext], permission_callback: Optional[PermissionCallback]):
        self.session = session
        self.role_context = role_context
        self.permission_callback = permission_callback

def requires_permission(risk_level: RiskTolerance, description: str):
    """
    Decorator to check permissions based on RoleContext.
    If role's risk_tolerance is lower than the tool's risk_level, it asks for permission.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx: RunContext[AgentDeps], *args, **kwargs):
            deps = ctx.deps
            role = deps.role_context
            
            # Default behavior if no role: Assume Standard/Medium semantics or just proceed?
            # Prompt says "Roles only modify...". Without role, maybe unlimited?
            # But let's assume if no role context, we act as a standard assistant.
            
            should_ask = False
            if role:
                # Logic:
                # If tool risk is HIGH, and tolerance is LOW or MEDIUM -> Ask
                # If tool risk is MEDIUM, and tolerance is LOW -> Ask
                # If tool risk is LOW -> Don't ask (unless paranoid mode?)
                
                tool_risk_value = {RiskTolerance.LOW: 1, RiskTolerance.MEDIUM: 2, RiskTolerance.HIGH: 3}[risk_level]
                role_tolerance_value = {RiskTolerance.LOW: 1, RiskTolerance.MEDIUM: 2, RiskTolerance.HIGH: 3}[role.risk_tolerance]
                
                if tool_risk_value > role_tolerance_value:
                    should_ask = True
                
                # Check permission strategy
                if role.permission_strategy == PermissionStrategy.EARLY:
                    # Early permissions might be handled at plan time, but if we are here, strict check.
                    pass 
            
            if should_ask and deps.permission_callback:
                # Convert args/kwargs to string for display
                op_details = f"Args: {args}, Kwargs: {kwargs}"
                approved = await deps.permission_callback(description, op_details, risk_level.value)
                if not approved:
                    raise Exception(f"Permission denied for {description}")
            
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator
