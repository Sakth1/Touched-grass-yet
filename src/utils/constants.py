import os
from pathlib import Path
from typing import Dict, List, Set


#: Absolute path to the ``src`` directory; used as the anchor for bundled assets.
ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Directory containing app images, icons, fonts, and chess piece artwork.
ASSET_DIR = Path(ROOT_DIR, "assets")


# ── Layout defaults (pixels) ────────────────────────────────────────────────

#: Fallback page width used when the Flet viewport reports ``0``.
DEFAULT_PAGE_WIDTH = 960

#: Fallback page height used when the Flet viewport reports ``0``.
DEFAULT_PAGE_HEIGHT = 800

#: Minimum viewport width enforced after safe-area padding is subtracted.
MIN_PAGE_WIDTH = 320.0

#: Minimum viewport height enforced after safe-area padding is subtracted.
MIN_PAGE_HEIGHT = 480.0

#: Maximum viewport width, in pixels, treated as a stacked mobile layout.
MOBILE_BREAKPOINT = 700

#: Maximum viewport width, in pixels, treated as a tablet split layout.
TABLET_BREAKPOINT = 1100
