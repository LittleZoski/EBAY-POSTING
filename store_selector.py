"""
Interactive Store Selector
Prompts user to confirm/select which eBay account to use before processing
"""

import os
from pathlib import Path
from typing import Tuple

# Store configuration
STORES = {
    1: {
        "name": "savvy_market",
        "owner": "Your Store",
        "color": "\033[94m"  # Blue
    },
    2: {
        "name": "miniemart",
        "owner": "Wife's Store",
        "color": "\033[95m"  # Magenta
    }
}

RESET_COLOR = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def get_current_active_account() -> int:
    """Read the current ACTIVE_ACCOUNT from .env file"""
    env_path = Path(".env")
    if not env_path.exists():
        return 1  # Default to account 1

    with open(env_path, 'r') as f:
        for line in f:
            if line.strip().startswith("ACTIVE_ACCOUNT="):
                try:
                    return int(line.split("=")[1].strip())
                except (ValueError, IndexError):
                    return 1
    return 1


def update_env_active_account(account: int) -> None:
    """Update ACTIVE_ACCOUNT in .env file"""
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError(".env file not found")

    # Read all lines
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Update the ACTIVE_ACCOUNT line
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("ACTIVE_ACCOUNT="):
            lines[i] = f"ACTIVE_ACCOUNT={account}\n"
            updated = True
            break

    # Write back
    if updated:
        with open(env_path, 'w') as f:
            f.writelines(lines)


def display_store_info(account: int) -> None:
    """Display colorful store information"""
    store = STORES[account]
    color = store["color"]
    print(f"\n{color}{'='*70}")
    print(f"  ACTIVE STORE: {store['name'].upper()}")
    print(f"  Owner: {store['owner']}")
    print(f"  Account Number: {account}")
    print(f"{'='*70}{RESET_COLOR}\n")


def confirm_or_select_store() -> int:
    """
    Interactive prompt to confirm or select store.
    Returns the selected account number (1 or 2)
    """
    current_account = get_current_active_account()
    current_store = STORES[current_account]

    print("\n" + "="*70)
    print("🏪  STORE SELECTION")
    print("="*70)

    # Show current store
    print(f"\n📍 Currently configured store: {current_store['color']}{current_store['name'].upper()}{RESET_COLOR} ({current_store['owner']})")

    # Show all available stores
    print(f"\n📋 Available stores:")
    for num, store in STORES.items():
        marker = "👉" if num == current_account else "  "
        print(f"  {marker} [{num}] {store['name']} ({store['owner']})")

    # Prompt for selection
    print(f"\n{YELLOW}⚠️  WARNING: Listing fees will be charged to the selected account!{RESET_COLOR}")

    while True:
        print(f"\n{'─'*70}")
        response = input(f"Select store [1 for savvy_market / 2 for miniemart] (default={current_account}): ").strip()

        # If empty, use current account
        if not response:
            selected_account = current_account
            print(f"{GREEN}✓ Using current store: {STORES[selected_account]['name']}{RESET_COLOR}")
            break

        # Validate input
        try:
            selected_account = int(response)
            if selected_account in STORES:
                if selected_account != current_account:
                    print(f"{YELLOW}⚠️  Switching from {STORES[current_account]['name']} → {STORES[selected_account]['name']}{RESET_COLOR}")
                else:
                    print(f"{GREEN}✓ Confirmed: {STORES[selected_account]['name']}{RESET_COLOR}")
                break
            else:
                print(f"{RED}❌ Invalid selection. Please enter 1 or 2.{RESET_COLOR}")
        except ValueError:
            print(f"{RED}❌ Invalid input. Please enter 1 or 2.{RESET_COLOR}")

    # Final confirmation with clear warning
    print(f"\n{'='*70}")
    print(f"{STORES[selected_account]['color']}  You selected: {STORES[selected_account]['name'].upper()} ({STORES[selected_account]['owner']}){RESET_COLOR}")
    print(f"{'='*70}")

    final_confirm = input(f"\n{YELLOW}Type 'YES' to confirm and proceed with this store:{RESET_COLOR} ").strip().upper()

    if final_confirm != 'YES':
        print(f"\n{RED}❌ Cancelled by user. Please restart and select the correct store.{RESET_COLOR}")
        exit(0)

    # Update .env if account changed
    if selected_account != current_account:
        print(f"\n{GREEN}✓ Updating .env file...{RESET_COLOR}")
        update_env_active_account(selected_account)
        print(f"{GREEN}✓ ACTIVE_ACCOUNT updated to {selected_account}{RESET_COLOR}")

    # Display final active store
    display_store_info(selected_account)

    return selected_account


def get_store_name(account: int) -> str:
    """Get the store name for a given account number"""
    return STORES.get(account, {}).get("name", "Unknown")


if __name__ == "__main__":
    # For testing
    selected = confirm_or_select_store()
    print(f"Selected account: {selected}")
