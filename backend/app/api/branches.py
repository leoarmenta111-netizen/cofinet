from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.branch import Branch
from app.schemas.branch import BranchResponse
from app.services.branch_service import BranchService


router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get(
    "",
    response_model=list[BranchResponse],
    summary="List active CofiCenter branches",
)
def get_branches(
    db: Session = Depends(get_db),
) -> Sequence[Branch]:
    return BranchService.get_active_branches(db)


@router.get(
    "/{branch_code}",
    response_model=BranchResponse,
    responses={404: {"description": "Branch not found"}},
    summary="Get one CofiCenter branch by code",
)
def get_branch(
    branch_code: str,
    db: Session = Depends(get_db),
) -> Branch:
    return BranchService.get_by_code(db, branch_code)
