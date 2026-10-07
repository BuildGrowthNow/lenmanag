"""Default booking destination for LenQuant's client galleries."""

DEFAULT_BOOKING_URL = "https://calendly.com/lengrowth/lenquant-new-website"


def resolve_booking_url(url: str | None) -> str:
    value = (url or "").strip()
    if not value or value == "https://calendly.com/lenquant/sites":
        return DEFAULT_BOOKING_URL
    return value
