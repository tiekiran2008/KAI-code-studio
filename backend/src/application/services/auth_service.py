import uuid
import jwt
from datetime import datetime, timezone
from typing import Optional
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError
from src.core.config import settings
from src.core.logger import logger
from src.domain.entities.user import User, UserSession

class AuthService:
    def __init__(self):
        # We need SUPABASE_URL and SUPABASE_KEY (or SUPABASE_ANON_KEY) to be set
        # For tests, we might mock this, but in production it will use real values
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY

        # Safe startup diagnostic — logs presence of config, never values
        config_status = settings.get_supabase_config_status()
        logger.info(
            "auth_service_init",
            supabase_url_configured=config_status["SUPABASE_URL"],
            anon_key_configured=config_status["SUPABASE_ANON_KEY"],
            jwt_secret_configured=config_status["SUPABASE_JWT_SECRET"],
        )

        if supabase_url and supabase_key:
            try:
                self.supabase: Optional[Client] = create_client(supabase_url, supabase_key)
            except Exception as exc:
                logger.warning("auth_service_supabase_client_init_failed", error=str(exc))
                self.supabase = None
        else:
            logger.warning(
                "auth_service_supabase_not_configured",
                missing=[k for k, v in config_status.items() if not v],
            )
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

        Validation order:
        1. dev-token bypass (non-production only)
        2. Local JWT decode with SUPABASE_JWT_SECRET (fast path, no network)
        3. Supabase Auth API get_user (reliable fallback for Google OAuth tokens)
           - Sends: apikey: <SUPABASE_ANON_KEY>, Authorization: Bearer <token>
           - Returns 403 if SUPABASE_URL or SUPABASE_ANON_KEY is wrong/missing
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
        #    The supabase-py client sends: apikey=<anon_key>, Authorization=Bearer <token>
        #    A 403 response means: wrong SUPABASE_URL, wrong/missing SUPABASE_ANON_KEY,
        #    or the token is invalid/expired.
        if self.supabase:
            supabase_error: Optional[str] = None
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
            except AuthApiError as exc:
                # Surface the real Supabase error (e.g. "Invalid JWT" or 403 forbidden)
                supabase_error = exc.message
                logger.warning(
                    "auth_supabase_get_user_failed",
                    status=getattr(exc, "status", None),
                    message=exc.message,
                    supabase_url_configured=bool(settings.SUPABASE_URL),
                    anon_key_configured=bool(settings.SUPABASE_ANON_KEY or settings.SUPABASE_KEY),
                )
            except Exception as exc:
                supabase_error = str(exc)
                logger.warning("auth_supabase_get_user_error", error=str(exc))

            if supabase_error:
                raise ValueError(f"Invalid token. Supabase auth error: {supabase_error}")

        if self._is_dev_bypass_active():
            dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
            dev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dev_email))
            return {"sub": dev_id, "email": dev_email}

        if not settings.SUPABASE_JWT_SECRET and not self.supabase:
            raise ValueError(
                "Supabase is not configured. Ensure SUPABASE_URL and SUPABASE_ANON_KEY "
                "environment variables are set on the server."
            )

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


