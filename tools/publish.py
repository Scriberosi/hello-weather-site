#!/usr/bin/env python3
"""Collection-time helpers for the magazine workflow, kept testable.

Untrusted input — the workflow_dispatch month and the collected response — is
validated here instead of being interpolated into a shell script, so a value
such as ``$(touch pwned)`` cannot execute and ``../../etc/passwd`` cannot escape
the issues directory.

Subcommands:
  decide-month              print the month to publish (INPUT_MONTH env or last)
  write-issue --response R --month M --issues D
                            write the collected issue, refusing a month
                            mismatch, path traversal, or overwrite
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Exact ASCII YYYY-MM. [0-9] matches only ASCII digits (not Unicode digits),
# and \A ... \Z anchor the whole string, so no metacharacters slip through.
_MONTH = re.compile(r"\A[0-9]{4}-[0-9]{2}\Z")


def validate_month(value: str) -> str:
    """Return ``value`` when it is an exact ASCII ``YYYY-MM`` with a real month.

    Raises ``ValueError`` otherwise. ``strptime`` rejects month ``00`` or ``13``,
    so both shell metacharacters and calendar-invalid input are refused.
    """
    if not _MONTH.match(value):
        raise ValueError(f"month {value!r} is not an exact YYYY-MM value")
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"month {value!r} is not a real calendar month") from exc
    return value


def default_month(today: date | None = None) -> str:
    """The previous calendar month as ``YYYY-MM``."""
    today = today or date.today()
    last_of_previous = today.replace(day=1) - timedelta(days=1)
    return f"{last_of_previous.year:04d}-{last_of_previous.month:02d}"


def decide_month(input_month: str | None) -> str:
    """Validate an explicit month, or fall back to the previous month."""
    value = (input_month or "").strip()
    return validate_month(value) if value else default_month()


def write_issue(response_path: Path, requested_month: str, issues_dir: Path) -> Path:
    """Write the collected issue, refusing mismatch, traversal, and overwrite."""
    month = validate_month(requested_month)
    payload = json.loads(Path(response_path).read_text(encoding="utf-8"))
    if payload.get("month") != month:
        raise ValueError(
            f"response month {payload.get('month')!r} does not match the "
            f"requested {month!r}"
        )
    if "rendered_html" not in payload:
        raise KeyError("response is missing rendered_html")
    issues_dir = Path(issues_dir)
    issues_dir.mkdir(exist_ok=True)
    # The path is built only from the validated request, so it cannot traverse;
    # "x" mode never truncates an already-published issue.
    target = issues_dir / f"{month}.html"
    with open(target, "x", encoding="utf-8") as handle:
        handle.write(payload["rendered_html"])
    print(f"wrote {target}, generator={payload.get('generator')}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("decide-month")
    writer = sub.add_parser("write-issue")
    writer.add_argument("--response", required=True, type=Path)
    writer.add_argument("--month", required=True)
    writer.add_argument("--issues", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "decide-month":
            print(decide_month(os.environ.get("INPUT_MONTH")))
        else:
            write_issue(args.response, args.month, args.issues)
    except (ValueError, KeyError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
