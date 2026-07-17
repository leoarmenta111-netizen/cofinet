from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanService:
    @staticmethod
    def get_active_plans(db: Session) -> Sequence[Plan]:
        return db.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.id)
        ).scalars().all()

    @staticmethod
    def get_active_plan(db: Session, plan_id: int) -> Plan:
        plan = db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.is_active.is_(True))
        ).scalar_one_or_none()
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )
        return plan

    @staticmethod
    def create_plan(db: Session, plan_data: PlanCreate) -> Plan:
        plan = Plan(**plan_data.model_dump())
        try:
            db.add(plan)
            db.commit()
            db.refresh(plan)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plan name already registered",
            ) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create plan",
            ) from exc
        return plan

    @staticmethod
    def update_plan(db: Session, plan_id: int, plan_data: PlanUpdate) -> Plan:
        plan = PlanService.get_active_plan(db, plan_id)
        for field, value in plan_data.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)

        try:
            db.commit()
            db.refresh(plan)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plan name already registered",
            ) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not update plan",
            ) from exc
        return plan

    @staticmethod
    def delete_plan(db: Session, plan_id: int) -> None:
        plan = PlanService.get_active_plan(db, plan_id)
        plan.is_active = False
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not delete plan",
            ) from exc

    @staticmethod
    def seed_default_plans(db: Session) -> None:
        """Insert the default plans once without overwriting existing records."""
        default_plans = (
            {
                "name": "Express",
                "description": "30 minutes of internet access.",
                "price": 25,
                "duration_minutes": 30,
            },
            {
                "name": "Focus",
                "description": "Two hours of internet access.",
                "price": 45,
                "duration_minutes": 120,
            },
            {
                "name": "Productivity",
                "description": "Eight hours of internet access.",
                "price": 80,
                "duration_minutes": 480,
            },
            {
                "name": "Unlimited Day",
                "description": "A full day of internet access.",
                "price": 120,
                "duration_minutes": 1440,
            },
        )
        existing_names = set(db.execute(select(Plan.name)).scalars())
        new_plans = [Plan(**plan) for plan in default_plans if plan["name"] not in existing_names]
        if not new_plans:
            return

        try:
            db.add_all(new_plans)
            db.commit()
        except IntegrityError:
            # A concurrent initialization may have inserted the same names.
            db.rollback()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not seed plans",
            ) from exc
