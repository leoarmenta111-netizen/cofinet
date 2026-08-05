from collections.abc import Sequence

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.admin_security import require_super_admin
from app.database.deps import get_db
from app.models.admin import Admin
from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanResponse, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("", response_model=list[PlanResponse])
def get_plans(db: Session = Depends(get_db)) -> Sequence[Plan]:
    """List active plans only."""
    return PlanService.get_active_plans(db)


@router.get(
    "/{plan_id}",
    response_model=PlanResponse,
    responses={404: {"description": "Plan not found"}},
)
def get_plan(plan_id: int, db: Session = Depends(get_db)) -> Plan:
    """Get one active plan by ID."""
    return PlanService.get_active_plan(db, plan_id)


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Plan name already registered"},
        500: {"description": "Database error"},
    },
)
def create_plan(
    plan: PlanCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Plan:
    """Create a plan."""
    return PlanService.create_plan(db, plan)


@router.put(
    "/{plan_id}",
    response_model=PlanResponse,
    responses={
        404: {"description": "Plan not found"},
        409: {"description": "Plan name already registered"},
        500: {"description": "Database error"},
    },
)
def update_plan(
    plan_id: int,
    plan: PlanUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Plan:
    """Update an active plan."""
    return PlanService.update_plan(db, plan_id, plan)


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Plan not found"},
        500: {"description": "Database error"},
    },
)
def delete_plan(
    plan_id: int,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Soft-delete an active plan."""
    PlanService.delete_plan(db, plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
