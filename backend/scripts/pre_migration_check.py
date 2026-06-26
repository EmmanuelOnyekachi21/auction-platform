"""Pre-migration safety check script.

Run this before every `alembic upgrade` on any environment, especially
production. It shows the current migration state, lists pending migrations,
and asks for explicit confirmation before you proceed.

Usage:
    python scripts/pre_migration_check.py

Then, if you choose to continue:
    alembic upgrade head
"""

import subprocess
import sys


def run(cmd: list[str]) -> tuple[str, int]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main():
    print("=" * 60)
    print("  KaraKaja — Pre-Migration Safety Check")
    print("=" * 60)

    # Current revision
    current, code = run(["alembic", "current"])
    if code != 0:
        print("\n[ERROR] Could not connect to database.")
        print("Check your DATABASE_URL and try again.")
        sys.exit(1)

    print(f"\nCurrent revision:\n  {current or '(none — fresh database)'}")

    # Pending migrations
    pending, _ = run(["alembic", "history", "--indicate-current"])
    print("\nMigration history (current marked with *):\n")
    for line in pending.splitlines():
        print(f"  {line}")

    # Check what would run
    check, _ = run(["alembic", "upgrade", "head", "--sql"])
    if not check.strip():
        print("\n✓ No pending migrations. Database is up to date.")
        sys.exit(0)

    print("\nPending SQL that would be applied:")
    print("-" * 40)
    # Show first 50 lines max to avoid flooding the terminal
    lines = check.splitlines()
    for line in lines[:50]:
        print(f"  {line}")
    if len(lines) > 50:
        print(f"  ... ({len(lines) - 50} more lines)")
    print("-" * 40)

    print("\n[CHECKLIST] Before proceeding, confirm:")
    print("  1. You have taken a database backup")
    print("  2. You have tested this migration on staging/local first")
    print("  3. You are running during a low-traffic window")
    print("  4. You have a rollback plan (alembic downgrade -1)")
    print()

    answer = input("Type 'yes' to confirm you have completed the checklist: ")
    if answer.strip().lower() != "yes":
        print("\nMigration cancelled. Run `alembic upgrade head` when ready.")
        sys.exit(0)

    print("\nChecklist confirmed. Run the migration now:")
    print("  alembic upgrade head")
    print()
    print("To rollback one step if needed:")
    print("  alembic downgrade -1")


if __name__ == "__main__":
    main()
