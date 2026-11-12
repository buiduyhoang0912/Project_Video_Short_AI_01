
from fastapi import HTTPException


def get_current_user():
    raise HTTPException(
        status_code=501,
        detail="Module tương tác đang chờ tích hợp Auth JWT của nhóm",
    )
