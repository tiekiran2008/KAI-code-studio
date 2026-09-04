import sys
import argparse
from src.application.services.auth_service import AuthService
from src.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Confirm development user email in Supabase.")
    parser.add_argument("--user-id", default="defd75bb-cb1c-473a-b920-466035872214", help="User UID to confirm")
    args = parser.parse_args()

    print(f"Attempting to confirm user email for UID: {args.user_id}...")
    try:
        service = AuthService()
        res = service.confirm_user_email(args.user_id)
        print("Confirmation successful!")
        print(f"User ID: {res.get('user_id')}")
        print(f"Confirmed: {res.get('confirmed')}")
    except Exception as e:
        print(f"Error confirming user email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
