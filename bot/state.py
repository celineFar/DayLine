import json
import logging
import os
import atexit
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


# =========================
# User state model
# =========================

@dataclass
class UserState:
    # Preview / UI
    awaiting_custom_range: bool = False
    preview_message_id: Optional[int] = None

    # Sleep tracking
    sleep_start_dt: Optional[datetime] = None
    sleep_reminder_job_id: Optional[str] = None

    # Sleep resolution input modes
    awaiting_wake_time: bool = False
    awaiting_sleep_duration: bool = False
    awaiting_sleep_start_time: bool = False

    pending_action: Optional[str] = None

    def clear_input_flags(self) -> None:
        """Reset all awaiting_* flags to ensure mutual exclusivity."""
        self.awaiting_custom_range = False
        self.awaiting_wake_time = False
        self.awaiting_sleep_duration = False
        self.awaiting_sleep_start_time = False

# =========================
# Storage configuration
# =========================

STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "user_state.json")

os.makedirs(STATE_DIR, exist_ok=True)

# In-memory cache
_USER_STATE_CACHE: Dict[int, UserState] = {}


# =========================
# Serialization helpers
# =========================

def _serialize_state(state: UserState) -> dict:
    data = asdict(state)
    if data["sleep_start_dt"]:
        data["sleep_start_dt"] = data["sleep_start_dt"].isoformat()
    return data


def _deserialize_state(data: dict) -> UserState:
    if data.get("sleep_start_dt"):
        data["sleep_start_dt"] = datetime.fromisoformat(data["sleep_start_dt"])
    return UserState(**data)


# =========================
# Disk I/O
# =========================

def load_state_from_disk() -> None:
    """Load all user states from disk into memory."""
    global _USER_STATE_CACHE

    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Corrupted state file, starting clean: %s", e)
        return

    for user_id, state_data in raw.items():
        try:
            _USER_STATE_CACHE[int(user_id)] = _deserialize_state(state_data)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("Skipping malformed state for user %s: %s", user_id, e)
            continue


def save_state_to_disk() -> None:
    """Persist all user states to disk."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {uid: _serialize_state(state) for uid, state in _USER_STATE_CACHE.items()},
            f,
            indent=2,
        )


# Ensure state is saved on clean shutdown
atexit.register(save_state_to_disk)


# =========================
# Public API (use these)
# =========================

def get_state(user_id: int) -> UserState:
    """
    Retrieve the user's state.
    Creates a new state if one does not exist.
    """
    if user_id not in _USER_STATE_CACHE:
        _USER_STATE_CACHE[user_id] = UserState()
        save_state_to_disk()
    return _USER_STATE_CACHE[user_id]


def update_state(user_id: int, state: UserState) -> None:
    """Update and persist a user's state."""
    _USER_STATE_CACHE[user_id] = state
    save_state_to_disk()


def clear_state(user_id: int) -> None:
    """Remove a user's state entirely."""
    if user_id in _USER_STATE_CACHE:
        del _USER_STATE_CACHE[user_id]
        save_state_to_disk()


# =========================
# Initialize on import
# =========================

load_state_from_disk()


# =========================
# Example usage
# =========================

if __name__ == "__main__":
    uid = 12345

    state = get_state(uid)
    state.awaiting_custom_range = True
    state.preview_message_id = 99
    state.sleep_start_dt = datetime.now()

    update_state(uid, state)

    print("Saved state:", get_state(uid))
