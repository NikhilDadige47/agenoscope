import argparse
import getpass
import sys
from app.db.session import SessionLocal, engine, Base
import app.models  # ensure models are registered
from app.models.user import User
from app.models.workspace import Workspace
from app.core.security import get_password_hash


def create_user_and_workspace(email: str, password: str, workspace_name: str | None = None) -> None:
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email.strip().lower()).first()
        if existing_user:
            print(f"[-] Error: User with email '{email}' already exists.")
            sys.exit(1)

        hashed_password = get_password_hash(password)
        new_user = User(
            email=email.strip().lower(),
            password_hash=hashed_password,
        )
        db.add(new_user)
        db.flush()

        ws_name = workspace_name.strip() if workspace_name else f"{email.split('@')[0]}'s Workspace"
        new_workspace = Workspace(
            owner_user_id=new_user.id,
            name=ws_name,
        )
        db.add(new_workspace)
        db.commit()

        print("\n========================================================")
        print("  Superuser created successfully!")
        print(f"  Email:        {new_user.email}")
        print(f"  User ID:      {new_user.id}")
        print(f"  Workspace:    {new_workspace.name}")
        print(f"  Workspace ID: {new_workspace.id}")
        print("========================================================\n")

    except Exception as exc:
        db.rollback()
        print(f"[-] Failed to create superuser: {exc}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create a user and default workspace for agenoscope")
    parser.add_argument("--email", type=str, help="User email address")
    parser.add_argument("--password", type=str, help="User password")
    parser.add_argument("--workspace", type=str, help="Default workspace name")

    args = parser.parse_args()

    email = args.email
    password = args.password
    workspace_name = args.workspace

    print("\n--- agenoscope Admin User Creation ---")

    if not email:
        email = input("Enter email address: ").strip()
    
    if not email or "@" not in email:
        print("[-] Invalid email address.")
        sys.exit(1)

    if not password:
        password = getpass.getpass("Enter password (min 8 chars): ").strip()

    if len(password) < 8:
        print("[-] Password must be at least 8 characters long.")
        sys.exit(1)

    if not workspace_name and sys.stdin.isatty():
        ws_input = input(f"Enter workspace name [default: {email.split('@')[0]}'s Workspace]: ").strip()
        workspace_name = ws_input if ws_input else None

    create_user_and_workspace(email, password, workspace_name)


if __name__ == "__main__":
    main()
