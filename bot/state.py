from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class UserState:
    awaiting_custom_range: bool = False
    preview_message_id: Optional[int] = None

    sleep_start_dt: Optional[datetime] = None  # NEW


USER_STATE: dict[int, UserState] = {}


def get_state(user_id: int) -> UserState:
    if user_id not in USER_STATE:
        USER_STATE[user_id] = UserState()
    return USER_STATE[user_id]

