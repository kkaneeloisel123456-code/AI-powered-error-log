"""初始表结构：全部核心表 + 复合索引（PRD 8.4 / 开发规划 4.4）

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-14
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401  注册全部模型

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 以模型元数据为准创建全部表，保持模型与迁移一致（MVP 基线）
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
