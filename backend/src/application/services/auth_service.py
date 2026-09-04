import jwt
from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError
from src.core.config import settings
from src.domain.entities.user import User, UserSession

class AuthService:
    def __init__(self):
        # We need SUPABASE_URL and SUPABASE_KEY (or SUPABASE_ANON_KEY) to be set
        # For tests, we might mock this, but in production it will use real values
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None # Or handle gracefully depending on requirement

    def signup(self, email: str, password: str) -> UserSession:
        if not self.supabase:
            raise ValueError("Supabase is not configured.")
        try:
            res = self.supabase.auth.sign_up({"email": email, "password": password})
            if res.user is None:
                raise ValueError("Signup failed, no user returned.")
            
            user = User(
                id=res.user.id,
                email=res.user.email,
                created_at=res.user.created_at
            )

            if res.session is None:
                return UserSession(
                    access_token=None,
                    refresh_token=None,
                    expires_in=None,
                    user=user,
                    message="Account created. Please check your email to confirm your account.",
                    confirmation_required=True
                )

            return UserSession(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
                expires_in=res.session.expires_in,
                user=user,
                confirmation_required=False
            )
        except AuthApiError as e:
            raise ValueError(e.message)


    def login(self, email: str, password: str) -> UserSession:
        if not self.supabase:
            raise ValueError("Supabase is not configured.")
        try:
            res = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user is None or res.session is None:
                raise ValueError("Login failed, no user or session returned.")
            
            user = User(
                id=res.user.id,
                email=res.user.email,
                created_at=res.user.created_at
            )
            return UserSession(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
                expires_in=res.session.expires_in,
                user=user
            )
        except AuthApiError as e:
            raise ValueError(e.message)

    def logout(self, token: str) -> None:
        if not self.supabase:
            raise ValueError("Supabase is not configured.")
        # We can sign out via supabase using the access token
        # To do this correctly, we might need a separate client instance authenticated with this token
        # Or simply rely on client-side logout. For now, we will attempt to sign out if we have the token
        try:
             # create a new client for the user's session to log out
             user_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
             user_client.auth.set_session(token, "")
             user_client.auth.sign_out()
        except Exception:
            pass # Ignore logout errors on backend

    def refresh_token(self, refresh_token: str) -> UserSession:
        if not self.supabase:
            raise ValueError("Supabase is not configured.")
        try:
            res = self.supabase.auth.refresh_session(refresh_token)
            if res.user is None or res.session is None:
                raise ValueError("Refresh failed.")
            user = User(
                id=res.user.id,
                email=res.user.email,
                created_at=res.user.created_at
            )
            return UserSession(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
                expires_in=res.session.expires_in,
                user=user
            )
        except AuthApiError as e:
            raise ValueError(e.message)

    def validate_token(self, token: str) -> dict:
        """
        Validates the JWT token using the Supabase JWT secret.
        Returns the decoded payload if valid.
        """
        if not settings.SUPABASE_JWT_SECRET:
            raise ValueError("SUPABASE_JWT_SECRET is not configured.")
        
        try:
            # Supabase tokens are signed with the JWT_SECRET
            # The audience is usually 'authenticated'
            payload = jwt.decode(
                token, 
                settings.SUPABASE_JWT_SECRET, 
                algorithms=["HS256"], 
                options={"verify_aud": False}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired.")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token.")

    def confirm_user_email(self, user_id: str) -> dict:
        """
        Development-only helper to manually confirm a user's email address in Supabase.
        Requires SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY with admin privileges.
        """
        is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
        if is_production:
            raise ValueError("Development user confirmation is disabled in production environments.")

        service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if not settings.SUPABASE_URL or not service_key:
            raise ValueError("Supabase URL or Service Role Key is not configured.")

        try:
            admin_client = create_client(settings.SUPABASE_URL, service_key)
            res = admin_client.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
            if res.user is None:
                raise ValueError("User email confirmation failed in Supabase.")
            return {"status": "success", "user_id": res.user.id, "email": res.user.email, "confirmed": True}
        except AuthApiError as e:
            raise ValueError(e.message)

    def reset_dev_user_password(self, user_id: str, new_password: str) -> dict:
        """
        Development-only helper to reset a user's password in Supabase using the admin API.
        Requires ENVIRONMENT != 'production' and DEV_AUTH_BYPASS == True.
        Never logs or outputs the password.
        """
        is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
        if is_production or not settings.DEV_AUTH_BYPASS:
            raise ValueError("Development password reset is disabled in production environments or when DEV_AUTH_BYPASS is disabled.")

        if not new_password or len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if not settings.SUPABASE_URL or not service_key:
            raise ValueError("Supabase URL or Service Role Key is not configured.")

        try:
            admin_client = create_client(settings.SUPABASE_URL, service_key)
            res = admin_client.auth.admin.update_user_by_id(user_id, {"password": new_password})
            if res.user is None:
                raise ValueError("User password update failed in Supabase.")
            return {
                "status": "success",
                "user_id": res.user.id,
                "email": res.user.email,
                "message": "Password updated successfully."
            }
        except AuthApiError as e:
            raise ValueError(e.message)


