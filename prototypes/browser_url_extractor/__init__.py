"""Browser URL Extractor — pure-Python cross-browser URL tracking prototype.

Architecture
  Two-layer extraction: (1) platform accessibility API for real-time URL,
  (2) session file parsing as fallback (no browser restart or flags needed).

Platform support
  Windows: Fully tested via UIA (pywinauto). SNSS session files also work.
  macOS:   AppleScript stub exists (untested — no macOS CI).
           JSONLZ4 session files should work (same format as Windows).
  Linux:   AT-SPI2 / xdotool stubs exist (untested — no Linux CI).
           SNSS and JSONLZ4 session files should work.
  Cross-platform session parsing: Chromium SNSS binary, Firefox JSONLZ4.

Dependencies
  Windows: pywinauto (for UIA). Optional: uiautomation (alternative UIA lib).
  macOS:   No extra deps (uses osascript/AppleScript built-in).
  Linux:   PyGObject/gi (for AT-SPI2). Optional: xdotool fallback.
  All:     lz4 (for Firefox JSONLZ4, optional if only Chromium browsers).
"""
