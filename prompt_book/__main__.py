"""Allow ``python -m prompt_book`` execution."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
