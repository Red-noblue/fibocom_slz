# -*- coding: utf-8 -*-
# 结果落盘说明：把 MinerU 原始 zip 结果整理成主文档、图片实体和可读文本，避免源码与输出混在一起。
from __future__ import annotations

import hashlib
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests


_MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HTML_IMG_RE = re.compile(r"<img[^>]+src=['\"]([^'\"]+)['\"][^>]*>", re.I)
_TEX_IMG_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")


def _slugify(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^0-9A-Za-z._+-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "doc"


def _sha256_bytes(blob: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(blob)
    return digest.hexdigest()


def _guess_ext_from_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return ""
    normalized = content_type.split(";", 1)[0].strip().lower()
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
    }.get(normalized, "")


def _url_basename(url: str) -> str:
    try:
        parsed = urlparse(url)
        return os.path.basename(parsed.path)
    except Exception:
        return ""


def download_url(url: str, out_path: Path, *, timeout_s: int = 180, session: Optional[requests.Session] = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()
    with sess.get(url, stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with open(out_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def extract_zip(zip_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(out_dir)
    children = [child for child in out_dir.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return out_dir


def find_main_file(root: Path, exts: Tuple[str, ...]) -> Optional[Path]:
    candidates: List[Path] = []
    for ext in exts:
        candidates.extend([path_obj for path_obj in root.rglob(f"*{ext}") if path_obj.is_file()])
    if not candidates:
        return None

    def key(path_obj: Path) -> Tuple[int, int]:
        depth = len(path_obj.relative_to(root).parts)
        size = path_obj.stat().st_size
        return (depth, -size)

    return sorted(candidates, key=key)[0]


@dataclass
class ImageEntity:
    idx: int
    label: str
    original_ref: str
    rel_path: str
    abs_path: str


def _normalize_ref(ref_raw: str) -> str:
    text = (ref_raw or "").strip()
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1].strip()
    if (text.startswith('"') and '"' in text[1:]) or (text.startswith("'") and "'" in text[1:]):
        quote = text[0]
        end = text.find(quote, 1)
        if end > 0:
            text = text[1:end]
    if " " in text and not text.startswith("http"):
        text = text.split(" ", 1)[0].strip()
    return text


def _copy_or_download_image(
    ref: str,
    *,
    raw_root: Path,
    images_dir: Path,
    idx: int,
    session: Optional[requests.Session] = None,
) -> Tuple[str, Path]:
    images_dir.mkdir(parents=True, exist_ok=True)
    normalized_ref = _normalize_ref(ref)
    sess = session or requests.Session()

    if normalized_ref.startswith("data:"):
        match = re.match(r"data:([^;]+);base64,(.*)$", normalized_ref, re.I | re.S)
        if not match:
            raise RuntimeError("暂不支持该 data URI 格式")
        content_type = match.group(1).strip().lower()
        base64_payload = match.group(2).strip()
        import base64

        blob = base64.b64decode(base64_payload)
        ext = _guess_ext_from_content_type(content_type) or ".bin"
        name = f"img_{idx:04d}_data{ext}"
        out_path = images_dir / name
        out_path.write_bytes(blob)
        return f"images/{name}", out_path.resolve()

    if normalized_ref.startswith("http://") or normalized_ref.startswith("https://"):
        base = _slugify(_url_basename(normalized_ref)) or f"img_{idx:04d}"
        ext = os.path.splitext(base)[1]
        response = sess.get(normalized_ref, stream=True, timeout=60)
        response.raise_for_status()
        content = response.content
        if not ext:
            ext = _guess_ext_from_content_type(response.headers.get("Content-Type")) or ".bin"
        digest = _sha256_bytes(content)[:10]
        name = f"img_{idx:04d}_{digest}{ext}"
        out_path = images_dir / name
        out_path.write_bytes(content)
        return f"images/{name}", out_path.resolve()

    src_path = Path(normalized_ref)
    if not src_path.is_absolute():
        src_path = raw_root / normalized_ref
    if not src_path.exists():
        raise FileNotFoundError(f"图片不存在：{normalized_ref}")
    base = _slugify(src_path.name)
    ext = src_path.suffix or ".bin"
    name = f"img_{idx:04d}_{base}"
    if not name.lower().endswith(ext.lower()):
        name = name + ext
    out_path = images_dir / name
    shutil.copyfile(src_path, out_path)
    return f"images/{name}", out_path.resolve()


def materialize_markdown(
    md_path: Path,
    *,
    raw_root: Path,
    out_dir: Path,
    session: Optional[requests.Session] = None,
) -> Tuple[Path, List[ImageEntity]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    sess = session or requests.Session()

    raw_text = md_path.read_text(encoding="utf-8", errors="replace")
    entities: List[ImageEntity] = []
    ref_to_rel: Dict[str, str] = {}
    occurrences: List[Tuple[str, str]] = []

    for match in _MD_IMG_RE.finditer(raw_text):
        alt = (match.group(1) or "").strip()
        ref = (match.group(2) or "").strip()
        occurrences.append((alt, ref))
    for match in _HTML_IMG_RE.finditer(raw_text):
        occurrences.append(("", match.group(1)))

    for index, (alt, ref_raw) in enumerate(occurrences, start=1):
        ref = _normalize_ref(ref_raw)
        if ref in ref_to_rel:
            rel_path = ref_to_rel[ref]
            abs_path = (out_dir / rel_path).resolve()
        else:
            rel_path, abs_path = _copy_or_download_image(ref, raw_root=raw_root, images_dir=images_dir, idx=index, session=sess)
            ref_to_rel[ref] = rel_path
        label = alt.strip() or f"image_{index:04d}"
        entities.append(ImageEntity(idx=index, label=label, original_ref=ref, rel_path=rel_path, abs_path=str(abs_path)))

    def repl_md(match: re.Match) -> str:
        alt = match.group(1)
        ref = _normalize_ref(match.group(2))
        rel_path = ref_to_rel.get(ref)
        if not rel_path:
            return match.group(0)
        return f"![{alt}]({rel_path})"

    def repl_html(match: re.Match) -> str:
        ref = _normalize_ref(match.group(1))
        rel_path = ref_to_rel.get(ref)
        if not rel_path:
            return match.group(0)
        return re.sub(r"src=['\"][^'\"]+['\"]", f"src=\\\"{rel_path}\\\"", match.group(0))

    main_md_text = _MD_IMG_RE.sub(repl_md, raw_text)
    main_md_text = _HTML_IMG_RE.sub(repl_html, main_md_text)
    main_md_path = out_dir / "main.md"
    main_md_path.write_text(main_md_text, encoding="utf-8")

    entity_index = 0

    def repl_text_md(match: re.Match) -> str:
        nonlocal entity_index
        if entity_index >= len(entities):
            return match.group(0)
        entity = entities[entity_index]
        entity_index += 1
        return f"[IMAGE_ENTITY: {entity.label}] {entity.abs_path}"

    text_md = _MD_IMG_RE.sub(repl_text_md, main_md_text)
    (out_dir / "text.md").write_text(text_md, encoding="utf-8")

    lines: List[str] = [f"# 图片实体清单：`{main_md_path.name}`", ""]
    for entity in entities:
        lines.append(f"- [IMAGE_ENTITY: {entity.label}]")
        lines.append(f"  - 原始引用：`{entity.original_ref}`")
        lines.append(f"  - 相对路径：`{entity.rel_path}`")
        lines.append(f"  - 绝对路径：`{entity.abs_path}`")
        try:
            size = Path(entity.abs_path).stat().st_size
            lines.append(f"  - 文件大小：{size} bytes")
        except OSError:
            pass
        lines.append("")
    (out_dir / "images_manifest.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return main_md_path, entities


def materialize_tex(
    tex_path: Path,
    *,
    raw_root: Path,
    out_dir: Path,
    session: Optional[requests.Session] = None,
) -> Optional[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    sess = session or requests.Session()
    raw_text = tex_path.read_text(encoding="utf-8", errors="replace")

    ref_to_rel: Dict[str, str] = {}
    refs = [match.group(1).strip() for match in _TEX_IMG_RE.finditer(raw_text)]
    for index, ref in enumerate(refs, start=1):
        normalized_ref = _normalize_ref(ref)
        if normalized_ref in ref_to_rel:
            continue
        try:
            rel_path, _abs_path = _copy_or_download_image(normalized_ref, raw_root=raw_root, images_dir=images_dir, idx=index, session=sess)
        except Exception:
            continue
        ref_to_rel[normalized_ref] = rel_path

    def repl(match: re.Match) -> str:
        normalized_ref = _normalize_ref(match.group(1))
        rel_path = ref_to_rel.get(normalized_ref)
        if not rel_path:
            return match.group(0)
        return match.group(0).replace(match.group(1), rel_path)

    out_path = out_dir / tex_path.name
    out_path.write_text(_TEX_IMG_RE.sub(repl, raw_text), encoding="utf-8")
    return out_path


def materialize_from_raw(
    raw_root: Path,
    *,
    out_dir: Path,
    prefer_md: bool = True,
    session: Optional[requests.Session] = None,
) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()

    md_path = find_main_file(raw_root, (".md",))
    tex_path = find_main_file(raw_root, (".tex",))
    result: Dict[str, str] = {}

    if prefer_md and md_path is not None:
        main_md_path, _entities = materialize_markdown(md_path, raw_root=raw_root, out_dir=out_dir, session=sess)
        result["main_md"] = str(main_md_path)
    if tex_path is not None:
        out_tex = materialize_tex(tex_path, raw_root=raw_root, out_dir=out_dir, session=sess)
        if out_tex:
            result["main_tex"] = str(out_tex)
    return result
