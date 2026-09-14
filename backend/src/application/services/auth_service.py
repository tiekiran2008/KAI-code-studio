import uuid
import jwt
from datetime import datetime, timezone
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
            try:
                self.supabase: Optional[Client] = create_client(supabase_url, supabase_key)
            except Exception:
                self.supabase = None
        else:
            self.supabase = None

    def _is_dev_bypass_active(self) -> bool:
        is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
        return bool(settings.DEV_AUTH_BYPASS and not is_production)

    def _create_dev_session(self, email: str) -> UserSession:
        dev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        user = User(
            id=dev_id,
            email=email,
            created_at=datetime.now(timezone.utc),
        )
        return UserSession(
            access_token=f"dev-token-{dev_id}",
            refresh_token=f"dev-refresh-{dev_id}",
            expires_in=86400 * 30,
            expires_at=int(datetime.now(timezone.utc).timestamp()) + (86400 * 30),
            user=user,
            confirmation_required=False,
        )

    def signup(self, email: str, password: str) -> UserSession:
        if not self.supabase:
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
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
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
            raise ValueError(e.message)
        except Exception as e:
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
            raise ValueError(f"Authentication service error: {str(e)}")

    def login(self, email: str, password: str) -> UserSession:
        if not self.supabase:
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
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
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
            raise ValueError(e.message)
        except Exception as e:
            if self._is_dev_bypass_active():
                return self._create_dev_session(email)
            raise ValueError(f"Authentication service error: {str(e)}")

    def logout(self, token: str) -> None:
        if not self.supabase:
            return
        try:
            user_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            user_client.auth.set_session(token, "")
            user_client.auth.sign_out()
        except Exception:
            pass

    def refresh_token(self, refresh_token: str) -> UserSession:
        if not self.supabase:
            if self._is_dev_bypass_active():
                dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
                return self._create_dev_session(dev_email)
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
        except (AuthApiError, Exception) as e:
            if self._is_dev_bypass_active():
                dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
                return self._create_dev_session(dev_email)
            raise ValueError(str(e))

    def validate_token(self, token: str) -> dict:
        """
        Validates the JWT token using the Supabase JWT secret or Supabase Auth API.
        Returns the decoded payload if valid.
        """
        if token.startswith("dev-token-") and self._is_dev_bypass_active():
            dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
            dev_id = token.replace("dev-token-", "") or str(uuid.uuid5(uuid.NAMESPACE_DNS, dev_email))
            return {"sub": dev_id, "email": dev_email}

        # 1. Fast path: validate locally if SUPABASE_JWT_SECRET is configured
        if settings.SUPABASE_JWT_SECRET:
            try:
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
                # Token might be signed by Supabase asymmetric keys; proceed to Supabase API fallback
                pass

        # 2. Reliable fallback: validate directly against Supabase Auth API
        if self.supabase:
            try:
                res = self.supabase.auth.get_user(jwt=token)
                if res and res.user:
                    return {
                        "sub": res.user.id,
                        "email": res.user.email or "",
                        "role": getattr(res.user, "role", "authenticated") or "authenticated",
                        "user_metadata": getattr(res.user, "user_metadata", {}) or {},
                        "app_metadata": getattr(res.user, "app_metadata", {}) or {},
                    }
            except Exception:
                pass

        if self._is_dev_bypass_active():
            dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
            dev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dev_email))
            return {"sub": dev_id, "email": dev_email}

        if not settings.SUPABASE_JWT_SECRET and not self.supabase:
            raise ValueError("SUPABASE_JWT_SECRET is not configured.")

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


