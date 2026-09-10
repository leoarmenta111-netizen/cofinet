import asyncio
import io
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from openpyxl import Workbook
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.main import app
from app.models.pos_catalog import PosCategory, PosProduct
from app.services.admin_pos_bulk_import_service import (
    AdminPosBulkImportService,
)
import app.services.pos_product_image_service as image_service_module
from app.services.pos_product_image_service import (
    PosProductImageService,
)


def create_category(db_session):
    suffix = uuid4().hex[:8]

    category = PosCategory(
        name=f"Bebidas {suffix}",
        slug=f"bebidas-{suffix}",
        sort_order=0,
        is_active=True,
    )

    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    return category


def create_product(db_session):
    category = create_category(db_session)

    product = PosProduct(
        category_id=category.id,
        name=f"Producto {uuid4().hex[:8]}",
        sku=f"IMG-{uuid4().hex[:8]}",
        base_price=Decimal("55.00"),
        sort_order=0,
        is_active=True,
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def csv_content(category_name):
    sku = f"LAT-{uuid4().hex[:8]}"

    return (
        "Nombre,Categoria,SKU,Precio Base,"
        "Descripcion,Orden,Activo\n"
        f"Latte Importado,{category_name},{sku},"
        "75.50,Cafe con leche,1,SI\n"
    ).encode("utf-8")


def xlsx_content(category_name):
    workbook = Workbook()
    sheet = workbook.active

    sheet.append(
        [
            "Nombre",
            "Categoria",
            "SKU",
            "Precio Base",
            "Descripcion",
            "Orden",
            "Activo",
        ]
    )

    sheet.append(
        [
            "Americano Importado",
            category_name,
            f"AME-{uuid4().hex[:8]}",
            65.25,
            "Cafe americano",
            2,
            "SI",
        ]
    )

    buffer = io.BytesIO()
    workbook.save(buffer)

    return buffer.getvalue()


def png_content():
    image = Image.new(
        "RGB",
        (1200, 600),
        (255, 255, 255),
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def upload_file(
    filename,
    content,
    content_type,
):
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers(
            {
                "content-type": content_type,
            }
        ),
    )


def test_catalog_bulk_and_image_routes_are_registered():
    paths = app.openapi()["paths"]

    expected = {
        "/admin/pos/catalog/products/bulk/preview",
        "/admin/pos/catalog/products/bulk/import",
        "/admin/pos/catalog/products/{product_id}/image",
    }

    assert expected.issubset(paths)

    assert (
        "post"
        in paths[
            "/admin/pos/catalog/products/bulk/preview"
        ]
    )

    assert (
        "post"
        in paths[
            "/admin/pos/catalog/products/bulk/import"
        ]
    )

    image_path = paths[
        "/admin/pos/catalog/products/{product_id}/image"
    ]

    assert "post" in image_path
    assert "delete" in image_path


def test_bulk_preview_and_import_csv(
    db_session,
):
    category = create_category(db_session)

    content = csv_content(category.name)

    before = (
        db_session.query(PosProduct)
        .count()
    )

    preview = AdminPosBulkImportService.preview(
        db_session,
        "productos.csv",
        content,
    )

    assert isinstance(preview, dict)

    db_session.expire_all()

    after_preview = (
        db_session.query(PosProduct)
        .count()
    )

    assert after_preview == before

    result = AdminPosBulkImportService.import_file(
        db_session,
        "productos.csv",
        content,
    )

    assert isinstance(result, dict)

    db_session.expire_all()

    after_import = (
        db_session.query(PosProduct)
        .count()
    )

    assert after_import == before + 1

    product = (
        db_session.query(PosProduct)
        .filter(
            PosProduct.name
            == "Latte Importado"
        )
        .one()
    )

    assert product.category_id == category.id
    assert product.base_price == Decimal("75.50")
    assert product.is_active is True


def test_bulk_preview_accepts_xlsx(
    db_session,
):
    category = create_category(db_session)

    result = AdminPosBulkImportService.preview(
        db_session,
        "productos.xlsx",
        xlsx_content(category.name),
    )

    assert isinstance(result, dict)


def test_bulk_rejects_unsupported_file(
    db_session,
):
    with pytest.raises(HTTPException) as exc:
        AdminPosBulkImportService.preview(
            db_session,
            "productos.txt",
            b"hello",
        )

    assert exc.value.status_code == 422


def test_product_image_upload_and_delete(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        image_service_module,
        "IMAGE_DIR",
        tmp_path,
    )

    product = create_product(db_session)

    upload = upload_file(
        "producto.png",
        png_content(),
        "image/png",
    )

    stored = asyncio.run(
        PosProductImageService.upload(
            db_session,
            product.id,
            upload,
        )
    )

    assert stored.image_url is not None
    assert stored.image_url.startswith(
        "/media/pos-products/"
    )
    assert stored.image_url.endswith(".webp")

    filename = stored.image_url.removeprefix(
        "/media/pos-products/"
    )

    image_path = tmp_path / filename

    assert image_path.exists()

    with Image.open(image_path) as image:
        assert image.width <= 800
        assert image.height <= 800
        assert image.format == "WEBP"

    stored = PosProductImageService.delete(
        db_session,
        product.id,
    )

    assert stored.image_url is None
    assert not image_path.exists()


def test_product_image_rejects_invalid_type(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        image_service_module,
        "IMAGE_DIR",
        tmp_path,
    )

    product = create_product(db_session)

    upload = upload_file(
        "producto.txt",
        b"not-an-image",
        "text/plain",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            PosProductImageService.upload(
                db_session,
                product.id,
                upload,
            )
        )

    assert exc.value.status_code == 415


def test_product_image_rejects_empty_file(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        image_service_module,
        "IMAGE_DIR",
        tmp_path,
    )

    product = create_product(db_session)

    upload = upload_file(
        "producto.png",
        b"",
        "image/png",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            PosProductImageService.upload(
                db_session,
                product.id,
                upload,
            )
        )

    assert exc.value.status_code == 422
