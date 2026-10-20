from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

import yaml
from PIL import Image, ImageOps, UnidentifiedImageError

import time
import requests
from config import Config

# authorityid задаётся внешним каталогом. Жёсткий charset — никаких `/`,
# `..` и пробелов. 64 символа — с запасом под любые внешние ID.
AUTHORITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
IMAGES_DIR = Config.DATA_DIR / "images"

Image.MAX_IMAGE_PIXELS = Config.MAX_PIXELS


class StorageError(ValueError):
    """Не прошёл валидацию файл или его содержимое."""


class AuthorityIdExists(StorageError):
    """Запись с таким authorityid уже существует."""


class InvalidAuthorityId(StorageError):
    """authorityid не проходит валидацию."""


@dataclass
class Picture:
    authorityid: str
    title: str
    description: str
    created_at: str
    updated_at: str
    width: int
    height: int
    original_filename: str

    @property
    def directory(self) -> Path:
        return IMAGES_DIR / self.authorityid

    @property
    def image_file(self) -> Path:
        return self.directory / "image.jpg"

    @property
    def meta_file(self) -> Path:
        return self.directory / "description.yml"

    def as_dict(self) -> dict:
        return asdict(self)


def init_storage() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def valid_authorityid(value: str) -> bool:
    return isinstance(value, str) and bool(AUTHORITY_ID_PATTERN.match(value))


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in Config.ALLOWED_EXTENSIONS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prepare_image(stream: BinaryIO) -> Image.Image:
    try:
        with Image.open(stream) as raw:
            image = ImageOps.exif_transpose(raw)
            image.load()

            if image.mode in {"RGBA", "LA", "PA"} or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                canvas = Image.new("RGB", rgba.size, (255, 255, 255))
                canvas.paste(rgba, mask=rgba.getchannel("A"))
                image = canvas
            else:
                image = image.convert("RGB")

            image.thumbnail(Config.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            return image.copy()
    except Image.DecompressionBombError as exc:
        raise StorageError("Изображение слишком большое по числу пикселей.") from exc
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise StorageError("Не удалось прочитать изображение. Попробуйте другой файл.") from exc


def _save_jpeg(image: Image.Image, dest: Path) -> None:
    image.save(
        dest,
        format="JPEG",
        quality=Config.JPEG_QUALITY,
        progressive=True,
        optimize=True,
    )


def _dump_meta(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def create_picture(
    authorityid: str,
    title: str,
    description: str,
    stream: BinaryIO,
    original_filename: str,
) -> Picture:
    if not valid_authorityid(authorityid):
        raise InvalidAuthorityId("Некорректный идентификатор источника.")
    init_storage()
    target = IMAGES_DIR / authorityid
    if target.exists():
        # Защита от гонок: два одновременных POST с одним authorityid
        # не должны друг друга перезатереть.
        raise AuthorityIdExists("Картинка с этим authorityid уже существует.")

    image = _prepare_image(stream)

    workdir = Path(tempfile.mkdtemp(prefix=".upload-", dir=IMAGES_DIR))
    try:
        _save_jpeg(image, workdir / "image.jpg")
        stamp = _now()
        record = Picture(
            authorityid=authorityid,
            title=title,
            description=description,
            created_at=stamp,
            updated_at=stamp,
            width=image.width,
            height=image.height,
            original_filename=original_filename,
        )
        (workdir / "description.yml").write_text(
            yaml.safe_dump(record.as_dict(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        os.replace(workdir, target)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return record


def load_picture(authorityid: str) -> Picture | None:
    if not valid_authorityid(authorityid):
        return None
    meta_file = IMAGES_DIR / authorityid / "description.yml"
    if not meta_file.is_file():
        return None
    try:
        data = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        record = Picture(
            # Имя каталога — источник истины, не доверяем id внутри YAML.
            authorityid=authorityid,
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            width=int(data.get("width") or 0),
            height=int(data.get("height") or 0),
            original_filename=str(data.get("original_filename") or ""),
        )
    except (yaml.YAMLError, OSError, TypeError, ValueError):
        return None
    return record if record.image_file.is_file() else None


def list_pictures() -> list[Picture]:
    records = []
    for entry in IMAGES_DIR.iterdir():
        if entry.is_dir() and valid_authorityid(entry.name):
            record = load_picture(entry.name)
            if record is not None:
                records.append(record)
    return sorted(records, key=lambda p: p.created_at, reverse=True)


def image_path(authorityid: str) -> Path | None:
    if not valid_authorityid(authorityid):
        return None
    path = IMAGES_DIR / authorityid / "image.jpg"
    return path if path.is_file() else None


def update_picture(
    authorityid: str,
    title: str,
    description: str,
    stream: BinaryIO | None = None,
    original_filename: str | None = None,
) -> Picture | None:
    record = load_picture(authorityid)
    if record is None:
        return None

    replacement = _prepare_image(stream) if stream is not None else None
    if replacement is not None:
        tmp = record.directory / f"image-{uuid.uuid4().hex[:8]}.tmp"
        try:
            _save_jpeg(replacement, tmp)
            os.replace(tmp, record.image_file)
        finally:
            tmp.unlink(missing_ok=True)
        record.width, record.height = replacement.size
        record.original_filename = original_filename or record.original_filename

    record.title = title
    record.description = description
    record.updated_at = _now()
    _dump_meta(record.meta_file, record.as_dict())
    return record


# Кэш: authorityid -> (timestamp, linked_ids)
_linked_cache = {}

def get_linked_authorityids(authorityid: str) -> list[str]:
    """
    Запрашивает у каталога список связанных authorityid.
    Кэширует результат на CATALOG_CACHE_TTL_SECONDS.
    """
    now = time.time()
    cached = _linked_cache.get(authorityid)
    
    if cached and (now - cached[0]) < Config.CATALOG_CACHE_TTL_SECONDS:
        return cached[1]
    
    url = Config.CATALOG_LINKED_AUTHORS_URL.format(authorityid=authorityid)
    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code != 200:
            _linked_cache[authorityid] = (now, [])
            return []
        
        data = response.json()
        linked = data.get("author_ids", [])
        
        # Валидируем каждый ID
        linked = [aid for aid in linked if valid_authorityid(aid)]
        
        _linked_cache[authorityid] = (now, linked)
        return linked
        
    except (requests.RequestException, ValueError, KeyError):
        _linked_cache[authorityid] = (now, [])
        return []


def image_path_with_fallback(authorityid: str) -> Path | None:
    """
    Ищет картинку по authorityid. Если не найдена — ищет по связанным записям.
    """
    # Сначала проверяем локально
    if not valid_authorityid(authorityid):
        return None
    
    path = IMAGES_DIR / authorityid / "image.jpg"
    if path.is_file():
        return path
    
    # Не найдена — запрашиваем связанные записи
    linked_ids = get_linked_authorityids(authorityid)
    
    for linked_id in linked_ids:
        if linked_id == authorityid:
            continue  # Уже проверили
        linked_path = IMAGES_DIR / linked_id / "image.jpg"
        if linked_path.is_file():
            return linked_path
    
    return None
