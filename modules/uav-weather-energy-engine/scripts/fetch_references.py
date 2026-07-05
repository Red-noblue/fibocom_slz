"""抓取参考论文、开源仓库与数据源元信息。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _download(url: str, target: Path) -> None:
    """下载文件到目标路径。"""

    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux aarch64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as fh:
        shutil.copyfileobj(response, fh)


def _safe_extract(zip_path: Path, dest_dir: Path) -> None:
    """安全解压 zip 文件。"""

    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            out_path = dest_dir / member.filename
            if not str(out_path.resolve()).startswith(str(dest_dir.resolve())):
                raise RuntimeError(f"检测到不安全压缩路径: {member.filename}")
        zf.extractall(dest_dir)


def fetch_from_manifest(manifest_path: Path, output_root: Path) -> dict:
    """按 manifest 抓取参考资料。"""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_root.mkdir(parents=True, exist_ok=True)

    summary = {"downloaded": [], "linked": []}

    for section in ("papers", "repos", "datasets"):
        section_dir = output_root / section
        section_dir.mkdir(parents=True, exist_ok=True)
        for item in manifest.get(section, []):
            kind = item["kind"]
            name = item["name"]
            if kind == "link":
                meta_path = section_dir / f"{name}.json"
                meta_path.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
                summary["linked"].append(str(meta_path))
                continue

            filename = item["filename"]
            target_path = section_dir / filename
            _download(item["url"], target_path)
            summary["downloaded"].append(str(target_path))

            if kind == "archive" and item.get("extract"):
                extract_dir = section_dir / name
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                _safe_extract(target_path, extract_dir)
                summary["downloaded"].append(str(extract_dir))

    return summary


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="抓取论文、开源仓库和数据源元信息到 references 目录。")
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "references" / "manifest.json"),
        help="参考资料 manifest 路径",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "references"),
        help="参考资料输出目录",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary = fetch_from_manifest(Path(args.manifest), Path(args.output_dir))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
