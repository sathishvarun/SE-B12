"""Password rules shared by sign-up, reset, change and invitations: at least 8 characters and not an easy guess."""

COMMON = {
    "password",
    "password1",
    "password123",
    "passw0rd",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty123",
    "qwertyuiop",
    "11111111",
    "00000000",
    "abcd1234",
    "abc12345",
    "iloveyou",
    "admin123",
    "welcome1",
    "welcome123",
    "letmein1",
    "india123",
    "chennai123",
    "coimbatore",
    "virundhu",
    "virundhu123",
    "restaurant",
    "biryani123",
    "test1234",
    "testtest",
    "changeme",
    "sunshine1",
    "football",
    "baseball",
    "superman",
    "1q2w3e4r",
    "zaq12wsx",
    "asdf1234",
}


def weak_reason(
    password: str, email: str | None = None, full_name: str | None = None, business: str | None = None
) -> str | None:
    """Why this password is too easy to guess, or None if it's fine."""
    p = password.strip().lower()
    squashed = "".join(ch for ch in p if ch.isalnum())
    if len(password) < 8:
        return "Use at least 8 characters."
    if p in COMMON or p.rstrip("!@#$.") in COMMON or squashed in COMMON:
        return "That password is too common. Choose something harder to guess."
    if len(set(p)) <= 2:
        return "That password is too easy to guess."
    local = (email or "").lower().split("@")[0]
    personal = [
        local,
        *local.replace(".", " ").replace("_", " ").replace("-", " ").split(),
        *(full_name or "").lower().split(),
    ]
    whole = [
        "".join(ch for ch in (business or "").lower() if ch.isalnum()),
        "".join(ch for ch in local if ch.isalnum()),
    ]
    if any(len(x) >= 4 and (x in p or x in squashed) for x in personal) or any(
        len(x) >= 4 and x in squashed for x in whole
    ):
        return "Don't use your name, email or restaurant name in your password."
    return None
