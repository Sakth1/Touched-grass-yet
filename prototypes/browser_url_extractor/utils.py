SKIP_PREFIXES = [
    "about:",
    "chrome://",
    "edge://",
    "chrome-extension://",
    "view-source:",
    "data:",
    "brave://",
    "opera://",
    "vivaldi://",
]

SKIP_EXACT = {
    "about:blank",
    "about:newtab",
    "about:home",
    "about:welcome",
    "chrome://newtab/",
    "chrome://newtab",
    "chrome://bookmarks/",
    "chrome://history/",
    "chrome://settings/",
    "edge://newtab/",
    "edge://newtab",
    "edge://favorites/",
    "edge://history/",
    "edge://settings/",
    "brave://newtab/",
    "brave://newtab",
    "brave://bookmarks/",
    "brave://history/",
    "brave://settings/",
    "opera://newtab/",
    "opera://newtab",
    "opera://settings/",
    "vivaldi://newtab/",
    "vivaldi://newtab",
    "vivaldi://settings/",
}


def is_trackable_url(url: str | None) -> bool:
    if not url or not url.strip():
        return False
    url = url.strip()
    if url in SKIP_EXACT:
        return False
    url_lower = url.lower()
    return not any(url_lower.startswith(prefix) for prefix in SKIP_PREFIXES)


KNOWN_PREFIXES = ("http://", "https://", "file://", "about:", "chrome://",
                  "edge://", "data:", "brave://", "opera://", "vivaldi://")


def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not url.startswith(KNOWN_PREFIXES):
        url = f"http://{url}"
    return url
