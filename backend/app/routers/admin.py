"""API quản trị: /api/admin/... (chỉ ADMIN; kiểm tra quyền ở backend bằng require_admin).

- GET   /api/admin/seller-applications?status=PENDING|APPROVED|REJECTED
- PATCH /api/admin/seller-applications/{id}/approve
- PATCH /api/admin/seller-applications/{id}/reject    body: {"rejection_reason": "..."}
- GET   /api/admin/users?search=...
- PATCH /api/admin/users/{id}/lock
- PATCH /api/admin/users/{id}/unlock
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import admin as admin_crud
from app.crud.admin import AdminError
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.schemas.admin import (
    AdminRejectRequest,
    AdminSellerApplicationRead,
    AdminUserRead,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],  # chặn toàn bộ router với non-ADMIN
)


def _app_out(application, user) -> dict:
    return {
        "id": application.id,
        "user_id": application.user_id,
        "applicant": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
        },
        "proposed_shop_name": application.proposed_shop_name,
        "phone": application.phone,
        "description": application.description,
        "status": application.status,
        "rejection_reason": application.rejection_reason,
        "reviewed_by": application.reviewed_by,
        "reviewed_at": application.reviewed_at,
        "created_at": application.created_at,
    }


def _http(error: AdminError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("/seller-applications", response_model=list[AdminSellerApplicationRead])
def list_seller_applications(
    status: Literal["PENDING", "APPROVED", "REJECTED"] | None = None,
    db: Session = Depends(get_db),
):
    return [_app_out(a, u) for a, u in admin_crud.list_applications(db, status)]


@router.patch(
    "/seller-applications/{application_id}/approve",
    response_model=AdminSellerApplicationRead,
)
def approve_seller_application(
    application_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return _app_out(*admin_crud.approve_application(db, application_id, admin.id))
    except AdminError as e:
        raise _http(e)


@router.patch(
    "/seller-applications/{application_id}/reject",
    response_model=AdminSellerApplicationRead,
)
def reject_seller_application(
    application_id: int,
    data: AdminRejectRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return _app_out(
            *admin_crud.reject_application(
                db, application_id, admin.id, data.rejection_reason
            )
        )
    except AdminError as e:
        raise _http(e)


@router.get("/users", response_model=list[AdminUserRead])
def list_users(search: str | None = None, db: Session = Depends(get_db)):
    return admin_crud.list_users(db, search)


@router.patch("/users/{user_id}/lock", response_model=AdminUserRead)
def lock_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return admin_crud.set_user_status(db, user_id, admin.id, "LOCKED")
    except AdminError as e:
        raise _http(e)


@router.patch("/users/{user_id}/unlock", response_model=AdminUserRead)
def unlock_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return admin_crud.set_user_status(db, user_id, admin.id, "ACTIVE")
    except AdminError as e:
        raise _http(e)
