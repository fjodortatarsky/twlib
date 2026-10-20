from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = "picstore-dev-secret-do-not-use-in-production"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    DATA_DIR = BASE_DIR / "data"

    MAX_IMAGE_SIZE = (1600, 1200)
    JPEG_QUALITY = 88

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    MAX_PIXELS = 40_000_000

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

    MAX_TITLE_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 5000

    AUTHORITY_BASE_URL = "http://109.123.168.74:5000/author/{authorityid}"

    # URL эндпоинта связанных записей в каталоге
    CATALOG_LINKED_AUTHORS_URL = "http://109.123.168.74:5000/linkedauthors/{authorityid}"
    
    # Кэшируем запросы к каталогу на 1 час
    CATALOG_CACHE_TTL_SECONDS = 3600

