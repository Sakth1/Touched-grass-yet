"""Browser URL Extractor Prototype — cross-platform browser URL tracking.

Platform support
  Windows: fully tested (UIA via pywinauto + SNSS fallback)
  macOS:   AppleScript stub only, untested (session files should work)
  Linux:   AT-SPI2/xdotool stubs only, untested (session files should work)

  See browser_url_extractor package docstring for full details.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_url_extractor import chromium, discovery, firefox, platform_url
from browser_url_extractor.utils import is_trackable_url


def list_browsers():
    found = discovery.find_all_session_dirs()
    if not found:
        print("No browsers with session files found.")
        return

    print(f"{'Browser':<12} {'Session Dir':<60}")
    print("-" * 72)
    for name, path in found:
        print(f"{name:<12} {path:<60}")


def extract_url(browser_filter: str | None = None) -> dict:
    result: dict = {"url": None, "browser": None, "method": "session-file", "all_tabs": []}

    platform_url_val = platform_url.get_active_url_platform()
    if platform_url_val and is_trackable_url(platform_url_val):
        result["url"] = platform_url_val
        result["browser"] = "detected"
        result["method"] = "platform-a11y"
        result["all_tabs"] = []
        return result

    cfgs = discovery.find_chromium_session_dirs(browser_filter)
    for bname, sess_dir in cfgs:
        url = chromium.get_active_tab_url(bname, sess_dir)
        if url and is_trackable_url(url):
            result["url"] = url
            result["browser"] = bname
            result["method"] = "snss"
            return result
        if url:
            result["url"] = url
            result["browser"] = bname
            result["method"] = "snss"
            result["filtered_out"] = True
            return result

    ff_cfgs = discovery.find_firefox_session_dirs()
    for bname, backups_dir in ff_cfgs:
        if browser_filter and bname != browser_filter:
            continue
        url = firefox.get_active_tab_url(backups_dir)
        if url and is_trackable_url(url):
            result["url"] = url
            result["browser"] = bname
            result["method"] = "jsonlz4"
            return result

    return result


def run_oneshot(browser_filter: str | None = None, show_all: bool = False):
    result = extract_url(browser_filter)
    if result["url"]:
        print(f"Browser: {result['browser']}")
        print(f"Method:  {result['method']}")
        print(f"URL:     {result['url']}")
    else:
        print("No active browser URL found.")
        sys.exit(1)


def run_poll(interval: float, browser_filter: str | None = None, verbose: bool = False):
    print(f"Polling every {interval}s. Press Ctrl+C to stop.\n")
    prev_url: str | None = None
    first = True
    try:
        while True:
            result = extract_url(browser_filter)
            url = result.get("url")
            ts = time.strftime("%H:%M:%S")
            method = result.get("method", "?")
            browser = result.get("browser", "?")

            if first:
                if url:
                    print(f"[{ts}] {browser} ({method}): {url}")
                else:
                    print(f"[{ts}] No browser URL detected. Polling...")
                first = False
                prev_url = url
            elif url and url != prev_url:
                print(f"[{ts}] {browser} ({method}): {url}")
                prev_url = url
            elif verbose and url:
                print(f"[{ts}] {browser} ({method}): {url}  (unchanged)")
            elif verbose and not url:
                print(f"[{ts}] No URL detected. Polling...")
            elif url:
                print(".", end="", flush=True)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nPolling stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Browser URL Extractor Prototype",
        epilog="Platform support: Windows (fully tested), macOS/Linux (stubs only, untested)",
    )
    parser.add_argument("--one-shot", action="store_true", help="Extract URL once and exit")
    parser.add_argument("--poll", action="store_true", help="Poll URL continuously")
    parser.add_argument("--interval", type=float, default=3.0, help="Poll interval in seconds (default: 3)")
    parser.add_argument("--list-browsers", action="store_true", help="List detected browser session dirs")
    parser.add_argument("--browser", type=str, default=None, help="Target browser: chrome, brave, firefox, etc.")
    parser.add_argument("--verbose", action="store_true", help="Print every poll result (not just changes)")

    args = parser.parse_args()

    if args.list_browsers:
        list_browsers()
        return

    if args.poll:
        run_poll(args.interval, args.browser, verbose=args.verbose)
    else:
        run_oneshot(args.browser)


if __name__ == "__main__":
    main()
