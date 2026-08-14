"""本机加密（API Key 静态加密，开发规划 5.5）。

密钥文件 data/auth/secret.key 首启生成；加密只防落盘明文，
不防本机恶意进程（本地单机应用的预期边界）。
"""
from cryptography.fernet import Fernet

from app.core.config import get_settings

_KEY = None


def _fernet() -> Fernet:
    global _KEY
    if _KEY is None:
        path = get_settings().data_dir / "auth" / "secret.key"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(Fernet.generate_key())
        _KEY = Fernet(path.read_bytes())
    return _KEY


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()


def mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "••••••••"
    return f"{secret[:4]}••••••••{secret[-4:]}"
