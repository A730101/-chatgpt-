"""Command line interface for the prompt notebook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

from . import PromptBook, PromptNotFoundError, copy_to_clipboard

DEFAULT_PATH = Path("prompts.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage a categorized notebook for prompt storage.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_PATH,
        help="Path to the prompt notebook JSON file (default: prompts.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new notebook")
    init_parser.add_argument(
        "--categories",
        nargs="*",
        default=["角色", "圖像", "系統"],
        help="Optional list of categories to pre-create",
    )

    add_parser = subparsers.add_parser("add", help="Add a new prompt")
    add_parser.add_argument("title", help="Short title for the prompt")
    add_parser.add_argument("category", help="Category such as 角色/圖像/系統")
    add_parser.add_argument("content", help="The full prompt text")
    add_parser.add_argument(
        "--notes",
        default="",
        help="Optional annotation for reminders or context",
    )

    list_parser = subparsers.add_parser("list", help="List stored prompts")
    list_parser.add_argument(
        "--category",
        help="Only show prompts for a specific category",
    )
    list_parser.add_argument(
        "--search",
        help="Filter prompts by keywords in title, category, notes, or content",
    )
    list_parser.add_argument(
        "--sort",
        choices=["updated", "created", "title", "category"],
        default="updated",
        help="Sort prompts by the chosen field (default: updated)",
    )
    list_parser.add_argument(
        "--ascending",
        action="store_true",
        help="Show results in ascending order (default: newest first)",
    )

    show_parser = subparsers.add_parser("show", help="Display a prompt in detail")
    show_parser.add_argument("id", help="The identifier of the prompt")

    update_parser = subparsers.add_parser("update", help="Modify a prompt")
    update_parser.add_argument("id", help="Identifier of the prompt to change")
    update_parser.add_argument("--title")
    update_parser.add_argument("--category")
    update_parser.add_argument("--content")
    update_parser.add_argument("--notes")

    delete_parser = subparsers.add_parser("delete", help="Remove a prompt permanently")
    delete_parser.add_argument("id", help="Identifier of the prompt to delete")

    copy_parser = subparsers.add_parser("copy", help="Copy a prompt to the clipboard")
    copy_parser.add_argument("id", help="Identifier of the prompt to copy")
    copy_parser.add_argument(
        "--only", choices=["content", "notes"], help="Copy a specific field"
    )

    categories_parser = subparsers.add_parser("categories", help="List configured categories")
    categories_parser.add_argument(
        "--add",
        nargs="*",
        help="Add one or more categories to the notebook",
    )
    categories_parser.add_argument(
        "--remove",
        nargs="*",
        help="Remove one or more categories from the notebook",
    )

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    book = PromptBook(args.file)

    if args.command == "init":
        for category in args.categories:
            book.add_category(category)
        print(f"Notebook initialized at {book.path} with categories: {', '.join(book.list_categories())}")
        return 0

    if args.command == "add":
        prompt = book.add_prompt(args.title, args.category, args.content, notes=args.notes)
        print(_format_prompt(prompt))
        return 0

    if args.command == "list":
        prompts = book.list_prompts(
            category=args.category,
            search=args.search,
            sort_by=args.sort,
            descending=not args.ascending,
        )
        if not prompts:
            print("No prompts stored yet.")
            return 0
        timestamp_field = "created_at" if args.sort == "created" else "updated_at"
        _print_table(prompts, timestamp_field=timestamp_field)
        return 0

    if args.command == "show":
        try:
            prompt = book.get_prompt(args.id)
        except PromptNotFoundError as exc:
            parser.error(str(exc))
        print(_format_prompt(prompt))
        return 0

    if args.command == "update":
        try:
            prompt = book.update_prompt(
                args.id,
                title=args.title,
                category=args.category,
                content=args.content,
                notes=args.notes,
            )
        except PromptNotFoundError as exc:
            parser.error(str(exc))
        print(_format_prompt(prompt))
        return 0

    if args.command == "delete":
        try:
            book.delete_prompt(args.id)
        except PromptNotFoundError as exc:
            parser.error(str(exc))
        print(f"Deleted prompt {args.id}")
        return 0

    if args.command == "copy":
        try:
            prompt = book.get_prompt(args.id)
        except PromptNotFoundError as exc:
            parser.error(str(exc))
        payload = _select_copy_payload(prompt, args.only)
        success, message = copy_to_clipboard(payload)
        if success:
            print(f"{message}. Ready to paste!")
        else:
            print(message)
            print(payload)
        return 0

    if args.command == "categories":
        if args.add:
            for name in args.add:
                book.add_category(name)
        if args.remove:
            for name in args.remove:
                book.remove_category(name)
        categories = book.list_categories()
        if categories:
            print("Available categories:")
            for item in categories:
                print(f"  - {item}")
        else:
            print("No categories defined yet.")
        return 0

    parser.error("Unknown command")
    return 1


def _print_table(prompts: Iterable[Any], *, timestamp_field: str = "updated_at") -> None:
    label = "Updated" if timestamp_field == "updated_at" else "Created"
    headers = ("ID", "Title", "Category", label)
    rows = [headers]
    for prompt in prompts:
        timestamp = getattr(prompt, timestamp_field, "") or ""
        display_time = timestamp.split(".")[0] if isinstance(timestamp, str) else timestamp
        rows.append((prompt.id, prompt.title, prompt.category, display_time))

    widths = [max(len(str(row[idx])) for row in rows) for idx in range(len(headers))]

    def render_row(row: Iterable[str]) -> str:
        return "  ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row))

    print(render_row(headers))
    print("  ".join("-" * width for width in widths))
    for row in rows[1:]:
        print(render_row(row))


def _format_prompt(prompt: Any) -> str:
    return (
        f"ID: {prompt.id}\n"
        f"Title: {prompt.title}\n"
        f"Category: {prompt.category}\n"
        f"Notes: {prompt.notes or '-'}\n"
        f"Created: {prompt.created_at}\n"
        f"Updated: {prompt.updated_at}\n"
        "\n"
        f"{prompt.content}"
    )


def _select_copy_payload(prompt: Any, only: str | None) -> str:
    if only == "content":
        return prompt.content
    if only == "notes":
        return prompt.notes
    if prompt.notes:
        return f"{prompt.content}\n\nNotes: {prompt.notes}"
    return prompt.content


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
