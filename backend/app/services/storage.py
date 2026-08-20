"""文件存储抽象：Phase 1 仅实现本地存储，架构预留 MinIO/OSS/COS 切换。"""
from pathlib import Path
import zipfile

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError

ALLOWED_FILE_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}


class StorageBackend:
    """存储后端抽象基类。后续接入 MinIO/OSS/COS 时实现同接口。"""

    def save(self, rel_path: str, file: UploadFile, *, max_bytes: int) -> int:
        raise NotImplementedError

    def delete(self, rel_path: str) -> None:
        raise NotImplementedError

    def file_url(self, rel_path: str) -> str:
        raise NotImplementedError

    def resolve_path(self, rel_path: str) -> Path:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def save(self, rel_path: str, file: UploadFile, *, max_bytes: int) -> int:
        dest = self.resolve_path(rel_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with dest.open("wb") as f:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValidationError(
                            f"单个文件不能超过 {settings.max_upload_file_size_mb} MB"
                        )
                    f.write(chunk)
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return size

    def delete(self, rel_path: str) -> None:
        dest = self.resolve_path(rel_path)
        dest.unlink(missing_ok=True)

    def file_url(self, rel_path: str) -> str:
        return f"/files/{rel_path}"

    def resolve_path(self, rel_path: str) -> Path:
        dest = (self.root / rel_path).resolve()
        root = self.root.resolve()
        if root != dest and root not in dest.parents:
            raise ValidationError("非法文件存储路径")
        return dest


def get_storage() -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalStorage(settings.local_storage_dir)
    raise NotImplementedError(f"storage backend {settings.storage_backend!r} 未实现")


def validate_upload(file: UploadFile) -> str:
    """校验扩展名和浏览器声明的 MIME 类型，返回标准化扩展名。"""
    ext = Path(file.filename or "").suffix.lower()
    expected_types = ALLOWED_FILE_TYPES.get(ext)
    if expected_types is None:
        raise ValidationError(f"不支持的文件类型：{ext or '未知'}")
    if file.content_type not in expected_types:
        raise ValidationError("文件内容类型与扩展名不匹配")
    _validate_file_signature(file, ext)
    return ext


def _validate_file_signature(file: UploadFile, ext: str) -> None:
    """验证常见文件头，降低伪造扩展名的风险。"""
    stream = file.file
    try:
        stream.seek(0)
        header = stream.read(16)
        stream.seek(0)
        if ext == ".pdf" and not header.startswith(b"%PDF-"):
            raise ValidationError("文件内容不是有效的 PDF")
        if ext == ".png" and header != b"\x89PNG\r\n\x1a\n":
            raise ValidationError("文件内容不是有效的 PNG")
        if ext in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
            raise ValidationError("文件内容不是有效的 JPEG")
        if ext in {".docx", ".xlsx"}:
            if not header.startswith(b"PK"):
                raise ValidationError("Office Open XML 文件格式无效")
            try:
                with zipfile.ZipFile(stream) as archive:
                    names = set(archive.namelist())
            except zipfile.BadZipFile as exc:
                raise ValidationError("Office 文件压缩包无效") from exc
            required = "word/document.xml" if ext == ".docx" else "xl/workbook.xml"
            if required not in names:
                raise ValidationError("文件内容与扩展名不匹配")
        if ext in {".doc", ".xls"} and not header.startswith(b"\xd0\xcf\x11\xe0"):
            raise ValidationError("旧版 Office 文件格式无效")
    finally:
        stream.seek(0)
