import subprocess
import sys


def _step(name: str, *args: str) -> None:
    print(f"\n=== {name} ===")
    result = subprocess.run(args)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    _step("1. uv sync (frozen)", "uv", "sync", "--frozen")
    _step(
        "2. black formating",
        "uv",
        "run",
        "black",
        "src/",
        "tests/",
        "--target-version",
        "py312",
    )
    _step("3. ruff check", "uv", "run", "ruff", "check", "src/", "tests/")
    _step("4. pyright", "uv", "run", "pyright", "src/")
    _step("5. pytest", "uv", "run", "pytest", "tests/", "-v", "--tb=short", "-q")
    print("\n=== All CI checks passed ===")


if __name__ == "__main__":
    main()
