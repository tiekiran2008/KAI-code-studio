import sys
import os
import argparse
import getpass

# Ensure backend root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import settings
from src.application.services.auth_service import AuthService


DEFAULT_USER_ID = "defd75bb-cb1c-473a-b920-466035872214"

def main():
    parser = argparse.ArgumentParser(description="Development-only Supabase Password Reset CLI")
    parser.add_argument(
        "--user-id",
        type=str,
        default=DEFAULT_USER_ID,
        help=f"Target Supabase User ID (default: {DEFAULT_USER_ID})"
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="New password (if omitted, you will be prompted securely without echo)"
    )

    args = parser.parse_args()

    # Safety checks
    is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
    if is_production or not settings.DEV_AUTH_BYPASS:
        print("ERROR: Development password reset is disabled in production environments or when DEV_AUTH_BYPASS is disabled.", file=sys.stderr)
        sys.exit(1)

    user_id = args.user_id.strip()
    if not user_id:
        print("ERROR: User ID cannot be empty.", file=sys.stderr)
        sys.exit(1)

    password = args.password
    if not password:
        password = getpass.getpass("Enter new password for development user: ")
        confirm_password = getpass.getpass("Confirm new password: ")
        if password != confirm_password:
            print("ERROR: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 6:
        print("ERROR: Password must be at least 6 characters long.", file=sys.stderr)
        sys.exit(1)

    auth_service = AuthService()
    try:
        res = auth_service.reset_dev_user_password(user_id=user_id, new_password=password)
        print(f"SUCCESS: {res.get('message', 'Password updated successfully.')}")
        print(f"  User ID: {res.get('user_id')}")
        print(f"  Email:   {res.get('email')}")
    except ValueError as e:
        print(f"ERROR: Failed to update password: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
