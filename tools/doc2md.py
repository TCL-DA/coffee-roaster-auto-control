#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc2md.py - Chuyen hang loat tai lieu (PDF/Word/Excel/PPT/ODF/RTF/EPUB/CSV) sang Markdown
bang anydoc (https://github.com/firecrawl/anydoc), de AI va grep doc duoc noi dung.

Cai dat 1 lan:  npm install -g @firecrawl/anydoc

Vi du:
  python tools/doc2md.py "F:/Project/112_Quanly/Manuals"
  python tools/doc2md.py "F:/Project/112_Quanly" -o "F:/Project/112_Quanly/_md" --ocr hosted
  python tools/doc2md.py file.pdf --stdout

Ket qua: cay thu muc .md soi guong nguon + INDEX.md + bang bao cao file can OCR.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Duoi file anydoc doc duoc (theo --help cua anydoc)
EXTS = {
    ".doc", ".docx", ".docm", ".odt", ".rtf",
    ".ppt", ".pptx", ".pptm", ".ppsx", ".odp",
    ".xls", ".xlsx", ".xlsm", ".ods",
    ".pdf", ".epub", ".csv",
}

# Thu muc bo qua khi quet
SKIP_DIRS = {"_md", "node_modules", ".git", "__pycache__", ".venv", "dist", "build"}

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_OCR = 0, 1, 2, 3


def anydoc_cmd():
    """Tra ve lenh goi anydoc; uu tien ban cai global, khong co thi chay qua npx."""
    exe = "anydoc.cmd" if os.name == "nt" else "anydoc"
    from shutil import which
    if which(exe):
        return [exe]
    if which("anydoc"):
        return ["anydoc"]
    return ["npx", "-y", "@firecrawl/anydoc"]


def convert(cmd, src: Path, dst: Path, ocr: str, api_key: str | None):
    """Chuyen 1 file. Tra ve (ma_thoat, thong_bao_loi)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    args = list(cmd) + [str(src), "-o", str(dst)]
    if ocr != "reject":
        args += ["--ocr", ocr]
        if api_key:
            args += ["--api-key", api_key]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stderr or "").strip()


def main():
    ap = argparse.ArgumentParser(description="Chuyen tai lieu sang Markdown bang anydoc")
    ap.add_argument("src", help="File hoac thu muc nguon")
    ap.add_argument("-o", "--out", help="Thu muc dich (mac dinh: <nguon>/_md)")
    ap.add_argument("--ocr", choices=["reject", "hosted"], default="reject",
                    help="PDF scan: reject = bo qua (mac dinh), hosted = gui len Firecrawl Parse")
    ap.add_argument("--api-key", default=os.environ.get("FIRECRAWL_API_KEY"),
                    help="Khoa API Firecrawl cho --ocr hosted")
    ap.add_argument("--force", action="store_true", help="Chuyen lai ca file da co .md moi hon")
    ap.add_argument("--stdout", action="store_true", help="In Markdown ra man hinh (chi 1 file)")
    args = ap.parse_args()

    cmd = anydoc_cmd()
    src = Path(args.src).resolve()
    if not src.exists():
        print(f"Khong tim thay: {src}", file=sys.stderr)
        return EXIT_USAGE

    if args.stdout:
        if src.is_dir():
            print("--stdout chi dung cho 1 file", file=sys.stderr)
            return EXIT_USAGE
        a = list(cmd) + [str(src)]
        if args.ocr != "reject":
            a += ["--ocr", args.ocr] + (["--api-key", args.api_key] if args.api_key else [])
        return subprocess.run(a).returncode

    # Gom danh sach file nguon
    if src.is_file():
        files = [src]
        root = src.parent
    else:
        root = src
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if Path(fn).suffix.lower() in EXTS and not fn.startswith("~$"):
                    files.append(Path(dirpath) / fn)
        files.sort()

    out_root = Path(args.out).resolve() if args.out else root / "_md"
    out_root.mkdir(parents=True, exist_ok=True)

    ok, skipped, need_ocr, failed = [], [], [], []
    t0 = time.time()

    for i, f in enumerate(files, 1):
        rel = f.relative_to(root)
        dst = out_root / rel.with_suffix(".md")
        if dst.exists() and not args.force and dst.stat().st_mtime >= f.stat().st_mtime:
            skipped.append(rel)
            continue
        print(f"[{i}/{len(files)}] {rel}", flush=True)
        code, err = convert(cmd, f, dst, args.ocr, args.api_key)
        if code == EXIT_OK:
            ok.append((rel, dst.stat().st_size))
        elif code == EXIT_OCR:
            need_ocr.append((rel, err))
            dst.unlink(missing_ok=True)
            print(f"    -> can OCR: {err}", flush=True)
        else:
            failed.append((rel, err))
            dst.unlink(missing_ok=True)
            print(f"    -> LOI: {err}", flush=True)

    # Bang muc luc de grep nhanh
    idx = out_root / "INDEX.md"
    lines = [
        "# Muc luc tai lieu da chuyen sang Markdown",
        "",
        f"Nguon: `{root}`  ",
        f"Sinh boi `tools/doc2md.py` (anydoc) luc {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Chuyen moi: **{len(ok)}** | Bo qua (da co): **{len(skipped)}** | "
        f"Can OCR: **{len(need_ocr)}** | Loi: **{len(failed)}**",
        "",
        "## File da co Markdown",
        "",
    ]
    for md in sorted(out_root.rglob("*.md")):
        if md.name == "INDEX.md":
            continue
        r = md.relative_to(out_root)
        lines.append(f"- [{r.as_posix()}]({r.as_posix()}) — {md.stat().st_size // 1024} KB")
    if need_ocr:
        lines += ["", "## Can OCR (PDF scan — chay lai voi `--ocr hosted`)", ""]
        lines += [f"- `{r.as_posix()}` — {e}" for r, e in need_ocr]
    if failed:
        lines += ["", "## Loi chuyen", ""]
        lines += [f"- `{r.as_posix()}` — {e}" for r, e in failed]
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print()
    print(f"Xong sau {time.time() - t0:.1f}s -> {out_root}")
    print(f"  moi {len(ok)} | bo qua {len(skipped)} | can OCR {len(need_ocr)} | loi {len(failed)}")
    print(f"  muc luc: {idx}")
    return EXIT_OK if not failed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
