"""Seed 19 tài khoản demo và 3 đơn đăng ký đã duyệt."""

import os
from getpass import getpass

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import SellerApplication, User
from app.models.user import utc_now


def seed_demo_data(password: str):
    Base.metadata.create_all(bind=engine)

    accounts = [("admin01", "ADMIN", "Quan tri vien")]

    accounts += [
        (f"seller{i:02d}", "SELLER", f"Nguoi ban {i:02d}")
        for i in range(1, 4)
    ]

    accounts += [
        (f"user{i:02d}", "USER", f"Nguoi dung {i:02d}")
        for i in range(1, 16)
    ]

    created = skipped = applications_created = 0

    with SessionLocal.begin() as db:
        users = {}

        for username, role, display_name in accounts:
            email = f"{username}@example.com"

            matches = db.scalars(
                select(User)
                .where(
                    or_(
                        User.email == email,
                        User.username == username,
                    )
                )
                .with_for_update()
            ).all()

            if matches:
                if len(matches) != 1:
                    raise RuntimeError(
                        f"Xung dot email/username: {username}"
                    )

                user = matches[0]

                if (
                    user.email.lower() != email
                    or user.username.lower() != username
                ):
                    raise RuntimeError(
                        f"Xung dot dinh danh: {username}"
                    )

                if user.role != role or user.status != "ACTIVE":
                    raise RuntimeError(
                        f"{username} da co role/status khac; "
                        "seed khong ghi de"
                    )

                skipped += 1

            else:
                user = User(
                    email=email,
                    username=username,
                    password_hash=hash_password(password),
                    display_name=display_name,
                    role=role,
                    status="ACTIVE",
                )

                db.add(user)
                db.flush()
                created += 1

            users[username] = user

        for i in range(1, 4):
            seller = users[f"seller{i:02d}"]

            application_id = db.scalar(
                select(SellerApplication.id)
                .where(
                    SellerApplication.user_id == seller.id,
                    SellerApplication.status == "APPROVED",
                )
                .limit(1)
            )

            if application_id is None:
                db.add(
                    SellerApplication(
                        user_id=seller.id,
                        proposed_shop_name=f"Shop demo {i:02d}",
                        phone=f"000000000{i}",
                        description="Cua hang mau phuc vu kiem thu",
                        status="APPROVED",
                        reviewed_by=users["admin01"].id,
                        reviewed_at=utc_now(),
                    )
                )

                applications_created += 1

    return created, skipped, applications_created


def main():
    try:
        password = os.environ.get("SEED_PASSWORD") or getpass(
            "Nhap mat khau demo (it nhat 8 ky tu): "
        )

        created, skipped, applications = seed_demo_data(password)

    except (ValueError, RuntimeError) as error:
        raise SystemExit(f"Seed dung: {error}") from None

    except SQLAlchemyError as error:
        args = getattr(getattr(error, "orig", None), "args", ())
        code = args[0] if args else "?"

        raise SystemExit(
            f"Loi DB {type(error).__name__}, ma {code}. "
            "Kiem tra ket noi va cau truc bang."
        ) from None

    except (KeyboardInterrupt, EOFError):
        raise SystemExit("Da huy seed.") from None

    print(f"Tai khoan tao moi: {created}; da ton tai: {skipped}")
    print(f"Don APPROVED tao moi: {applications}")
    print("Da co 19 tai khoan demo: 1 ADMIN, 3 SELLER, 15 USER.")


if __name__ == "__main__":
    main()