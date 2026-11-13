"""Các hàm thao tác DB cho bảng seller_applications (đơn đăng ký bán hàng)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seller_application import SellerApplication
from app.models.user import User, utc_now
from app.schemas.seller_application import SellerApplicationCreate


def get_application(db: Session, application_id: int) -> SellerApplication | None:
    return db.get(SellerApplication, application_id)


def get_pending_application_by_user(
    db: Session, user_id: int
) -> SellerApplication | None:
    query = select(SellerApplication).where(
        SellerApplication.user_id == user_id,
        SellerApplication.status == "PENDING",
    )
    return db.scalar(query)


def get_approved_application_by_user(
    db: Session, user_id: int
) -> SellerApplication | None:
    query = select(SellerApplication).where(
        SellerApplication.user_id == user_id,
        SellerApplication.status == "APPROVED",
    )
    return db.scalar(query)


def get_applications_by_user(db: Session, user_id: int) -> list[SellerApplication]:
    query = (
        select(SellerApplication)
        .where(SellerApplication.user_id == user_id)
        .order_by(SellerApplication.id.desc())
    )
    return list(db.scalars(query))


def get_all_applications(
    db: Session, status_filter: str | None = None
) -> list[SellerApplication]:
    query = select(SellerApplication).order_by(SellerApplication.id.desc())
    if status_filter:
        query = query.where(SellerApplication.status == status_filter)
    return list(db.scalars(query))


def create_application(
    db: Session, user_id: int, data: SellerApplicationCreate
) -> SellerApplication:
    application = SellerApplication(
        user_id=user_id,
        proposed_shop_name=data.proposed_shop_name,
        phone=data.phone,
        description=data.description,
        status="PENDING",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def approve_application(
    db: Session, application: SellerApplication, admin_id: int
) -> SellerApplication:
    application.status = "APPROVED"
    application.rejection_reason = None
    application.reviewed_by = admin_id
    application.reviewed_at = utc_now()

    applicant = db.get(User, application.user_id)
    if applicant is not None and applicant.role == "USER":
        applicant.role = "SELLER"

    db.commit()
    db.refresh(application)
    return application


def reject_application(
    db: Session, application: SellerApplication, admin_id: int, reason: str
) -> SellerApplication:
    application.status = "REJECTED"
    application.rejection_reason = reason
    application.reviewed_by = admin_id
    application.reviewed_at = utc_now()

    db.commit()
    db.refresh(application)
    return application

