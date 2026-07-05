"""文档预览服务，负责把设备文档转成网页可展示的内容。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote


class DocumentPreviewService:
    """扫描文档目录并按需生成 PDF 和文本缓存。"""

    def __init__(self, docs_root: Path, cache_root: Path) -> None:
        self.docs_root = docs_root
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def list_documents(self) -> list[dict]:
        """列出可预览的文档清单。"""

        documents: list[dict] = []
        for file_path in sorted(self.docs_root.rglob("*")):
            if not file_path.is_file():
                continue
            if "mineru_outputs" in file_path.relative_to(self.docs_root).parts:
                continue
            if file_path.suffix.lower() not in {".doc", ".docx", ".pdf", ".txt"}:
                continue
            relative_path = file_path.relative_to(self.docs_root).as_posix()
            documents.append(
                {
                    "name": file_path.name,
                    "relative_path": relative_path,
                    "suffix": file_path.suffix.lower(),
                    "source_url": f"/api/docs/source?path={quote(relative_path)}",
                    "pdf_url": f"/api/docs/pdf?path={quote(relative_path)}",
                    "text_url": f"/api/docs/text?path={quote(relative_path)}",
                }
            )
        return documents

    def get_source_path(self, relative_path: str) -> Path:
        """将相对路径解析为受限的源文档路径。"""

        source_path = (self.docs_root / relative_path).resolve()
        docs_root = self.docs_root.resolve()
        if docs_root not in source_path.parents and source_path != docs_root:
            raise ValueError("文档路径超出允许范围")
        if not source_path.exists():
            raise FileNotFoundError(f"文档不存在: {relative_path}")
        return source_path

    def ensure_pdf(self, relative_path: str) -> Path:
        """确保指定文档有可供网页嵌入的 PDF 版本。"""

        source_path = self.get_source_path(relative_path)
        if source_path.suffix.lower() == ".pdf":
            return source_path
        output_path = self.cache_root / f"{source_path.stem}.pdf"
        self._ensure_converted(source_path, output_path, "pdf")
        return output_path

    def ensure_text(self, relative_path: str) -> Path:
        """确保指定文档有文本提取版本，便于快速浏览。"""

        source_path = self.get_source_path(relative_path)
        if source_path.suffix.lower() == ".txt":
            return source_path
        output_path = self.cache_root / f"{source_path.stem}.txt"
        self._ensure_converted(source_path, output_path, "txt")
        return output_path

    def _ensure_converted(self, source_path: Path, output_path: Path, mode: str) -> None:
        """按需调用 soffice 转换文档，避免重复生成。"""

        if output_path.exists() and output_path.stat().st_mtime >= source_path.stat().st_mtime:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        filter_name = "pdf" if mode == "pdf" else "txt:Text"
        profile_dir = self.cache_root / "lo_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "soffice",
            f"-env:UserInstallation=file://{profile_dir}",
            "--headless",
            "--convert-to",
            filter_name,
            "--outdir",
            str(output_path.parent),
            str(source_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if output_path.exists():
            return
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode,
                completed.args,
                output=completed.stdout,
                stderr=completed.stderr,
            )
