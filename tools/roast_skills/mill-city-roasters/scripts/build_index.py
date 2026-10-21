"""Tạo chỉ mục SQLite FTS từ phụ đề JSON3 của Mill City Roasters."""

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3


VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def default_paths():
    skill_dir = Path(__file__).resolve().parents[1]
    project_dir = skill_dir.parents[2]
    return (
        project_dir / "_external" / "mill-city-roasters" / "raw",
        skill_dir / "corpus.sqlite3",
        project_dir / "_external" / "mill-city-roasters",
    )


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def select_caption(raw_dir, video_id, info):
    """Ưu tiên phụ đề tiếng Anh do kênh đăng, sau đó mới dùng bản tự động."""
    manual = info.get("subtitles") or {}
    candidates = []
    for language in ("en", "en-US", "en-GB", "en-orig"):
        path = raw_dir / f"{video_id}.{language}.json3"
        if path.exists() and language in manual:
            candidates.append((path, language, "manual"))
    for language in ("en-orig", "en", "en-US", "en-GB"):
        path = raw_dir / f"{video_id}.{language}.json3"
        if path.exists():
            candidates.append((path, language, "automatic"))
    for path in sorted(raw_dir.glob(f"{video_id}.*-orig.json3")):
        language = path.name[len(video_id) + 1:-len(".json3")]
        candidates.append((path, language, "automatic"))
    return candidates[0] if candidates else None


def caption_events(path):
    out = []
    for event in load_json(path).get("events", []):
        segs = event.get("segs") or []
        text = re.sub(r"\s+", " ", "".join(s.get("utf8", "") for s in segs)).strip()
        if not text:
            continue
        start_ms = int(event.get("tStartMs") or 0)
        end_ms = start_ms + int(event.get("dDurationMs") or 0)
        out.append((start_ms, max(start_ms, end_ms), text))
    return out


def chunk_events(events, max_ms=45_000, max_chars=1_400):
    """Gom câu liên tiếp thành đoạn ngắn để tìm nhanh và giữ mốc nguồn chính xác."""
    chunks = []
    current = []
    start_ms = end_ms = 0
    chars = 0
    for event_start, event_end, text in events:
        if current and (event_start - start_ms >= max_ms or chars + len(text) + 1 > max_chars):
            chunks.append((start_ms, end_ms, " ".join(current)))
            current = []
            chars = 0
        if not current:
            start_ms = event_start
        current.append(text)
        chars += len(text) + 1
        end_ms = max(end_ms, event_end)
    if current:
        chunks.append((start_ms, end_ms, " ".join(current)))
    return chunks


def time_label(milliseconds):
    seconds = max(0, int(milliseconds) // 1000)
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:d}:{seconds:02d}"


def write_transcript(corpus_dir, video_id, title, info, language, caption_type, chunks):
    """Xuất bản văn có mốc thời gian để skill dùng Read/Grep mà không phải đọc JSON3."""
    transcript_dir = corpus_dir / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    source_url = f"https://www.youtube.com/watch?v={video_id}"
    lines = [
        f"# {title}",
        "",
        f"Video ID: {video_id}",
        f"Source: {source_url}",
        f"Upload date: {info.get('upload_date') or ''}",
        f"Language: {language}",
        f"Caption type: {caption_type}",
        "",
    ]
    lines.extend(f"[{time_label(start_ms)}] {text}" for start_ms, _end_ms, text in chunks)
    path = transcript_dir / f"{video_id}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.relative_to(corpus_dir).as_posix()


def write_catalog(corpus_dir, rows, values):
    corpus_dir.mkdir(parents=True, exist_ok=True)
    fields = ("video_id", "title", "upload_date", "duration_s", "language", "caption_type",
              "status", "transcript", "source_url")
    with (corpus_dir / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    readme = f"""# Mill City Roasters subtitle corpus

Nguồn: https://www.youtube.com/@MillCityRoasters
Ngày dựng chỉ mục: {values['built_at']}
Video trên kênh: {values['channel_videos']}
Video có phụ đề: {values['indexed_videos']}
Video không có phụ đề: {values['missing_videos']}

`raw/` giữ JSON3 và metadata tải từ YouTube. `transcripts/` là bản văn có mốc thời gian
được chọn theo thứ tự: phụ đề tiếng Anh thủ công, tiếng Anh tự động, rồi ngôn ngữ gốc.
Tra `manifest.csv` trước khi mở transcript. Auto-caption có thể sai thuật ngữ và con số;
luôn dẫn video cùng mốc thời gian và đối chiếu nguồn kỹ thuật khác khi quyết định có rủi ro.
"""
    (corpus_dir / "README.md").write_text(readme, encoding="utf-8")


def playlist_entries(raw_dir):
    playlists = []
    for path in raw_dir.glob("*.info.json"):
        data = load_json(path)
        if data.get("_type") == "playlist" and data.get("entries"):
            playlists.append(data)
    if not playlists:
        return {}
    playlist = max(playlists, key=lambda value: len(value.get("entries") or []))
    return {
        item.get("id"): item
        for item in playlist.get("entries") or []
        if item.get("id") and VIDEO_ID.fullmatch(item["id"])
    }


def video_info(raw_dir):
    found = {}
    for path in raw_dir.glob("*.info.json"):
        data = load_json(path)
        video_id = str(data.get("id") or "")
        if VIDEO_ID.fullmatch(video_id) and data.get("_type") != "playlist":
            found[video_id] = data
    return found


def build(raw_dir, output, corpus_dir):
    expected = playlist_entries(raw_dir)
    info_by_id = video_info(raw_dir)
    video_ids = list(expected) or list(info_by_id)
    if not video_ids:
        raise ValueError("Không tìm thấy metadata video trong thư mục phụ đề.")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    if temp.exists():
        temp.unlink()
    db = sqlite3.connect(temp)
    try:
        db.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE videos (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                upload_date TEXT,
                duration_s INTEGER,
                language TEXT,
                caption_type TEXT,
                status TEXT NOT NULL,
                source_url TEXT NOT NULL
            );
            CREATE TABLE passages (
                id INTEGER PRIMARY KEY,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                language TEXT NOT NULL,
                caption_type TEXT NOT NULL,
                text TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE passages_fts USING fts5(
                title, text, content='passages', content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );
            """
        )
        indexed = 0
        passage_count = 0
        catalog = []
        for video_id in video_ids:
            info = info_by_id.get(video_id) or expected.get(video_id) or {}
            title = str(info.get("title") or video_id)
            caption = select_caption(raw_dir, video_id, info)
            language = caption_type = ""
            status = "missing_subtitle"
            transcript = ""
            if caption:
                path, language, caption_type = caption
                chunks = chunk_events(caption_events(path))
                if chunks:
                    indexed += 1
                    status = "indexed"
                    transcript = write_transcript(
                        corpus_dir, video_id, title, info, language, caption_type, chunks
                    )
                    for start_ms, end_ms, text in chunks:
                        cursor = db.execute(
                            "INSERT INTO passages(video_id,title,start_ms,end_ms,language,caption_type,text) "
                            "VALUES(?,?,?,?,?,?,?)",
                            (video_id, title, start_ms, end_ms, language, caption_type, text),
                        )
                        db.execute(
                            "INSERT INTO passages_fts(rowid,title,text) VALUES(?,?,?)",
                            (cursor.lastrowid, title, text),
                        )
                        passage_count += 1
            source_url = f"https://www.youtube.com/watch?v={video_id}"
            db.execute(
                "INSERT INTO videos VALUES(?,?,?,?,?,?,?,?)",
                (
                    video_id,
                    title,
                    str(info.get("upload_date") or ""),
                    int(info.get("duration") or 0),
                    language,
                    caption_type,
                    status,
                    source_url,
                ),
            )
            catalog.append({
                "video_id": video_id,
                "title": title,
                "upload_date": str(info.get("upload_date") or ""),
                "duration_s": int(info.get("duration") or 0),
                "language": language,
                "caption_type": caption_type,
                "status": status,
                "transcript": transcript,
                "source_url": source_url,
            })

        built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        values = {
            "channel": "Mill City Roasters®",
            "channel_url": "https://www.youtube.com/@MillCityRoasters",
            "built_at": built_at,
            "channel_videos": str(len(video_ids)),
            "indexed_videos": str(indexed),
            "missing_videos": str(len(video_ids) - indexed),
            "passages": str(passage_count),
        }
        db.executemany("INSERT INTO metadata VALUES(?,?)", values.items())
        db.commit()
        db.execute("VACUUM")
    finally:
        db.close()
    os.replace(temp, output)
    write_catalog(corpus_dir, catalog, values)
    return values


def main():
    default_raw, default_output, default_corpus = default_paths()
    parser = argparse.ArgumentParser(description="Tạo chỉ mục phụ đề Mill City Roasters.")
    parser.add_argument("--raw-dir", type=Path, default=default_raw)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--corpus-dir", type=Path, default=default_corpus)
    args = parser.parse_args()
    values = build(args.raw_dir.resolve(), args.output.resolve(), args.corpus_dir.resolve())
    print(json.dumps(values, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
