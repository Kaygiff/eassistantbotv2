from safety.rate_limiter import is_rate_limited, get_remaining, reset_rate_limit
from safety.user_ban import is_banned, ban_user, lift_ban
from safety.content_moderation import moderate_text


async def check_user_access(user, action: str = "message") -> tuple[bool, str | None]:
    """
    Единая точка проверки доступа перед передачей в Brain.
    Проверяет: бан → rate limit.
    Возвращает (allowed, reason).
    """
    # 1. Проверка бана
    if await is_banned(user):
        return False, "banned"

    # 2. Проверка rate limit
    if await is_rate_limited(str(user.id), action):
        return False, "rate_limit"

    return True, None
