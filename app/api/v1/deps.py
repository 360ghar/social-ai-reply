from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.saas_models import AccountUser, Membership, Workspace
from app.db.session import get_db
from app.services.product.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AccountUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    user = db.scalar(select(AccountUser).where(AccountUser.id == user_id, AccountUser.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


def get_current_workspace(
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == current_user.id).order_by(Membership.id.asc())
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace membership found.")
    workspace = db.scalar(select(Workspace).where(Workspace.id == membership.workspace_id))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return workspace
