from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from src.application.services.auth_service import AuthService
from src.interfaces.api.dependencies import get_auth_service, get_current_user
from src.domain.entities.user import UserSession

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/signup", response_model=UserSession)
def signup(req: AuthRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        return auth_service.signup(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=UserSession)
def login(req: AuthRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        return auth_service.login(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/logout")
def logout(auth_service: AuthService = Depends(get_auth_service), current_user: dict = Depends(get_current_user)):
    # Since we can't easily get the raw token here without changing get_current_user to return both,
    # and Supabase logout on backend needs the access token, we will just return success 
    # and let the frontend clear its local state. 
    # A true logout would blacklist the token or use the client side supabase sign_out.
    return {"message": "Logged out successfully"}

@router.post("/refresh", response_model=UserSession)
def refresh_token(req: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        return auth_service.refresh_token(req.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

class ConfirmUserRequest(BaseModel):
    user_id: str

@router.post("/dev/confirm-user")
def dev_confirm_user(req: ConfirmUserRequest, auth_service: AuthService = Depends(get_auth_service)):
    from src.core.config import settings
    is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
    if is_production or not settings.DEV_AUTH_BYPASS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev endpoint disabled.")
    try:
        return auth_service.confirm_user_email(req.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

class DevResetPasswordRequest(BaseModel):
    user_id: str
    new_password: str

@router.post("/dev/reset-password")
def dev_reset_password(req: DevResetPasswordRequest, auth_service: AuthService = Depends(get_auth_service)):
    from src.core.config import settings
    is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
    if is_production or not settings.DEV_AUTH_BYPASS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev endpoint disabled.")
    try:
        return auth_service.reset_dev_user_password(req.user_id, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


