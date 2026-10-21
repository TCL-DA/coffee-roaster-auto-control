#!/usr/bin/env python3
"""Tải kho issue công khai của Artisan và lưu bản snapshot có thể tìm kiếm.

Lệnh này chỉ đọc GitHub API. Dữ liệu được ghi theo từng dòng để có thể tiếp tục
đợt tải sau khi hết hạn mức API hoặc mất mạng; không xoá bản snapshot cũ.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO = "artisan-roaster-scope/artisan"
API = f"https://api.github.com/repos/{REPO}"
SINCE = dt.datetime(2016, 1, 1, tzinfo=dt.timezone.utc)
UNTIL = dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc)
DEFAULT_OUT = Path(__file__).with_name("roast_skills") / "artisan-issues" / "data"


def parse_date(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def request_json(url: str) -> tuple[object, dict[str, str]]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OTL-RoastSkill-Artisan-Archive"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=45) as response:
            return json.load(response), {k.lower(): v for k, v in response.headers.items()}
    except HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining", "?")
        reset = exc.headers.get("X-RateLimit-Reset", "?")
        raise RuntimeError(f"GitHub API {exc.code} cho {url}; còn {remaining}, reset {reset}") from exc
    except URLError as exc:
        raise RuntimeError(f"Không đọc được GitHub API: {exc.reason}") from exc


def issue_row(item: dict) -> dict:
    return {
        "number": item["number"],
        "title": item.get("title", ""),
        "state": item.get("state", ""),
        "state_reason": item.get("state_reason"),
        "author": (item.get("user") or {}).get("login", ""),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "closed_at": item.get("closed_at"),
        "labels": [label.get("name", "") for label in item.get("labels", [])],
        "body": item.get("body") or "",
        "html_url": item.get("html_url", ""),
        "comments_count": item.get("comments", 0),
        "locked": bool(item.get("locked")),
        "assignees": [user.get("login", "") for user in item.get("assignees", [])],
        "milestone": (item.get("milestone") or {}).get("title"),
        "is_pull_request": "pull_request" in item,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


def load_jsonl(path: Path) -> dict[int, dict]:
    if not path.is_file():
        return {}
    rows: dict[int, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[int(row["number"])] = row
    return rows


def fetch_issues(out: Path, pause: float) -> tuple[dict[int, dict], int]:
    target = out / "issues.jsonl"
    rows = load_jsonl(target)
    page = 1
    pages = 0
    while True:
        params = urlencode({"state": "all", "per_page": 100, "sort": "created", "direction": "asc", "page": page})
        try:
            payload, headers = request_json(f"{API}/issues?{params}")
        except RuntimeError as exc:
            # REST API trả 422 khi page vượt quá trang cuối của một số repo.
            if "GitHub API 422" in str(exc) and page > 1:
                break
            raise
        if not isinstance(payload, list) or not payload:
            break
        pages += 1
        for item in payload:
            created = parse_date(item["created_at"])
            if SINCE <= created < UNTIL and "pull_request" not in item:
                rows[int(item["number"])] = issue_row(item)
        print(f"issues page {page}: {len(payload)} records, saved {len(rows)}", flush=True)
        # GitHub có thể trả 422 khi hỏi page vượt quá trang cuối; Link là cách
        # ổn định để biết còn trang kế tiếp, kể cả khi trang cuối đủ 100 dòng.
        write_jsonl(target, [rows[number] for number in sorted(rows)])
        if 'rel="next"' not in headers.get("link", ""):
            break
        page += 1
        if pause:
            time.sleep(pause)
    return rows, pages


def comment_row(issue_number: int, item: dict) -> dict:
    return {
        "issue_number": issue_number,
        "id": item["id"],
        "author": (item.get("user") or {}).get("login", ""),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "body": item.get("body") or "",
        "html_url": item.get("html_url", ""),
        "author_association": item.get("author_association", ""),
    }


def fetch_comments(out: Path, issues: dict[int, dict], pause: float) -> int:
    target = out / "comments.jsonl"
    rows = load_jsonl(target)
    page = 1
    # Một endpoint cho toàn bộ repository cần khoảng 39 request thay vì một
    # request cho từng issue. Lọc lại theo issue snapshot để loại bình luận PR.
    while True:
        params = urlencode({"per_page": 100, "page": page, "sort": "created", "direction": "asc"})
        try:
            payload, headers = request_json(f"{API}/issues/comments?{params}")
        except RuntimeError as exc:
            if "GitHub API 422" in str(exc) and page > 1:
                break
            raise
        if not isinstance(payload, list) or not payload:
            break
        for item in payload:
            issue_url = item.get("issue_url", "")
            try:
                issue_number = int(issue_url.rstrip("/").rsplit("/", 1)[-1])
            except (ValueError, IndexError):
                continue
            created = parse_date(item.get("created_at", "1970-01-01T00:00:00Z"))
            if issue_number in issues and SINCE <= created < UNTIL:
                rows[int(item["id"])] = comment_row(issue_number, item)
        write_jsonl(target, sorted(rows.values(), key=lambda row: (int(row["issue_number"]), row["created_at"])))
        print(f"comments page {page}: {len(payload)} records, saved {len(rows)}", flush=True)
        if 'rel="next"' not in headers.get("link", ""):
            break
        page += 1
        if pause:
            time.sleep(pause)
    return len(rows)


def write_manifest(out: Path, issues: dict[int, dict], pages: int, comments: int | None) -> None:
    years: dict[str, int] = {str(year): 0 for year in range(SINCE.year, UNTIL.year)}
    for issue in issues.values():
        year = issue["created_at"][:4]
        years[year] = years.get(year, 0) + 1
    manifest = {
        "repository": f"https://github.com/{REPO}",
        "issues_api": f"https://api.github.com/repos/{REPO}/issues",
        "range": {"since": SINCE.isoformat(), "until_exclusive": UNTIL.isoformat()},
        "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "issue_pages_read": pages,
        "issue_count": len(issues),
        "issue_count_by_year": dict(sorted(years.items())),
        "comment_count": comments,
        "comments_note": "Bình luận được lưu khi chạy với --comments hoặc --comments-only; file đã ghi được giữ để chạy tiếp.",
        "scope_note": "Chỉ lấy GitHub Issues; pull request bị loại khỏi kho. Năm 2025–2026 không có issue công khai trong API tại thời điểm snapshot nếu thống kê bằng 0.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--comments", action="store_true", help="tải cả bình luận issue; có thể tiếp tục nhiều lần")
    parser.add_argument("--comments-only", action="store_true", help="dùng issues.jsonl hiện có và chỉ tải bình luận")
    parser.add_argument("--manifest-only", action="store_true", help="dùng snapshot hiện có và chỉ dựng manifest")
    parser.add_argument("--issue-pages", type=int, default=0, help="số trang issue đã đọc khi dựng manifest hiện có")
    parser.add_argument("--pause", type=float, default=0.2, help="nghỉ giữa các API request, giây")
    args = parser.parse_args()
    existing = load_jsonl(args.output / "issues.jsonl")
    if args.manifest_only:
        write_manifest(args.output, existing, args.issue_pages, None)
        print(json.dumps({"issues": len(existing), "comments": None, "pages": args.issue_pages}, ensure_ascii=False))
        return 0
    if args.comments_only:
        issues = existing
        prior_manifest = args.output / "manifest.json"
        pages = (json.loads(prior_manifest.read_text(encoding="utf-8")).get("issue_pages_read", 0)
                 if prior_manifest.is_file() else 0)
    else:
        issues, pages = fetch_issues(args.output, max(0.0, args.pause))
    comments = None
    if args.comments or args.comments_only:
        comments = fetch_comments(args.output, issues, max(0.0, args.pause))
    write_manifest(args.output, issues, pages, comments)
    print(json.dumps({"issues": len(issues), "comments": comments, "pages": pages}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
