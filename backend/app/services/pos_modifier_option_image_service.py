from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models.pos_catalog import PosModifierOption
from app.services.pos_product_image_service import (
    ALLOWED_TYPES,
    IMAGE_DIR,
    MAX_DIMENSION,
    MAX_UPLOAD_BYTES,
    PUBLIC_PREFIX,
)


class PosModifierOptionImageService:
    @staticmethod
    def _get_option(
        db: Session,
        option_id: int,
    ) -> PosModifierOption:
        option = db.get(
            PosModifierOption,
            option_id,
        )

        if option is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="POS modifier option not found",
            )

        return option

    @staticmethod
    def _managed_path(
        image_url: str | None,
    ) -> Path | None:
        if not image_url:
            return None

        if not image_url.startswith(
            PUBLIC_PREFIX
        ):
            return None

        filename = image_url.removeprefix(
            PUBLIC_PREFIX
        )

        if not filename:
            return None

        if "/" in filename or "\\" in filename:
            return None

        return IMAGE_DIR / filename

    @classmethod
    async def upload(
        cls,
        db: Session,
        option_id: int,
        upload: UploadFile,
    ) -> PosModifierOption:
        option = cls._get_option(
            db,
            option_id,
        )

        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                ),
                detail=(
                    "Only JPG, PNG and WebP images "
                    "are supported"
                ),
            )

        raw = await upload.read(
            MAX_UPLOAD_BYTES + 1
        )

        if not raw:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="Image file is empty",
            )

        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                ),
                detail="Image exceeds the 5 MB limit",
            )

        try:
            image = Image.open(
                io.BytesIO(raw)
            )
            image.load()

        except (
            UnidentifiedImageError,
            OSError,
        ) as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="Invalid image file",
            ) from exc

        image = ImageOps.exif_transpose(
            image
        )

        if image.mode not in ("RGB", "RGBA"):
            if "A" in image.getbands():
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")

        image.thumbnail(
            (
                MAX_DIMENSION,
                MAX_DIMENSION,
            ),
            Image.Resampling.LANCZOS,
        )

        IMAGE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"modifier-{uuid.uuid4().hex}.webp"
        )

        target = IMAGE_DIR / filename

        try:
            image.save(
                target,
                format="WEBP",
                quality=88,
                method=6,
            )

        except Exception as exc:
            target.unlink(
                missing_ok=True
            )

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail="Could not process image",
            ) from exc

        old_path = cls._managed_path(
            option.image_url
        )

        option.image_url = (
            PUBLIC_PREFIX + filename
        )

        try:
            db.commit()
            db.refresh(option)

        except Exception:
            db.rollback()
            target.unlink(
                missing_ok=True
            )
            raise

        if old_path and old_path != target:
            old_path.unlink(
                missing_ok=True
            )

        return option

    @classmethod
    def delete(
        cls,
        db: Session,
        option_id: int,
    ) -> PosModifierOption:
        option = cls._get_option(
            db,
            option_id,
        )

        old_path = cls._managed_path(
            option.image_url
        )

        option.image_url = None

        try:
            db.commit()
            db.refresh(option)

        except Exception:
            db.rollback()
            raise

        if old_path:
            old_path.unlink(
                missing_ok=True
            )

        return option
