from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.branch import Branch


DEFAULT_BRANCH_CODE = "principal"


class BranchService:
    @staticmethod
    def get_active_branches(db: Session) -> Sequence[Branch]:
        """Return every active CofiCenter branch."""
        return db.execute(
            select(Branch)
            .where(Branch.is_active.is_(True))
            .order_by(Branch.name.asc(), Branch.id.asc())
        ).scalars().all()

    @staticmethod
    def get_by_code(
        db: Session,
        branch_code: str,
        *,
        active_only: bool = True,
    ) -> Branch:
        """Resolve one branch from its public code."""
        normalized_code = branch_code.strip().lower()

        query = select(Branch).where(
            func.lower(Branch.code) == normalized_code
        )

        if active_only:
            query = query.where(Branch.is_active.is_(True))

        branch = db.execute(query).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        return branch

    @staticmethod
    def get_default(db: Session) -> Branch:
        """Return the legacy/default branch during multi-branch transition."""
        return BranchService.get_by_code(
            db,
            DEFAULT_BRANCH_CODE,
            active_only=True,
        )

    @staticmethod
    def resolve(
        db: Session,
        branch_code: str | None,
    ) -> Branch:
        """
        Resolve an explicit branch or fall back to the existing principal
        branch for backwards compatibility.
        """
        if branch_code is None or not branch_code.strip():
            return BranchService.get_default(db)

        return BranchService.get_by_code(db, branch_code)
