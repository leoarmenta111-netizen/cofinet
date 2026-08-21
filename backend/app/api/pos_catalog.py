from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_catalog import PosCatalogResponse
from app.services.pos_catalog_service import PosCatalogService


router = APIRouter(
    prefix="/pos",
    tags=["POS"],
)


@router.get(
    "/catalog",
    response_model=PosCatalogResponse,
)
def get_pos_catalog(
    branch_code: str = Query(
        ...,
        min_length=1,
        max_length=50,
    ),
    db: Session = Depends(get_db),
) -> PosCatalogResponse:
    return PosCatalogService.get_catalog(
        db=db,
        branch_code=branch_code,
    )
