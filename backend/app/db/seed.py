"""内置种子数据：学科库 + 教材知识树 + 默认设置（T-M0-04 / 风险 R5 缓解）。"""
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgePoint, Setting, Subject

logger = logging.getLogger("recall")

# 内置学科（PRD 5.2：学科管理）
BUILTIN_SUBJECTS = ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "地理", "政治"]

# 内置教材知识树（一级 -> 二级），冷启动图谱兜底
KNOWLEDGE_TREE: dict[str, dict[str, list[str]]] = {
    "数学": {
        "代数": ["函数与导数", "三角函数", "数列", "不等式"],
        "几何": ["平面几何", "立体几何", "解析几何", "向量"],
        "概率统计": ["计数原理", "概率", "统计"],
    },
    "物理": {
        "力学": ["牛顿运动定律", "功和能", "动量", "万有引力"],
        "电磁学": ["电场", "恒定电流", "磁场", "电磁感应"],
        "热学": ["分子动理论", "热力学定律"],
        "光学": ["几何光学", "物理光学"],
        "近代物理": ["原子物理", "波粒二象性"],
    },
    "化学": {
        "化学基本概念": ["物质的量", "离子反应", "氧化还原"],
        "元素化合物": ["金属及其化合物", "非金属及其化合物"],
        "有机化学": ["烃", "烃的衍生物"],
        "化学实验": ["基本操作", "物质制备与检验"],
    },
}

DEFAULT_SETTINGS = {
    "default_review": {"count": 5, "difficulty": "auto", "scope": "due"},
    "ai": {"provider": "deepseek", "mock": None},  # mock 由环境变量决定，None=跟随配置
    "privacy": {"send_question_to_ai": True, "lan_enabled": False},
    "auth": {"token_revealed": False},
}


def seed_if_empty(db: Session) -> None:
    """首次启动种子（幂等：已有数据则跳过）。"""
    if db.scalar(select(Subject.id).limit(1)) is None:
        for i, name in enumerate(BUILTIN_SUBJECTS):
            subject = Subject(name=name, sort_order=i)
            db.add(subject)
            db.flush()
            for level1, children in KNOWLEDGE_TREE.get(name, {}).items():
                kp1 = KnowledgePoint(subject_id=subject.id, name=level1, level=1, path=f"/{level1}")
                db.add(kp1)
                db.flush()
                for child in children:
                    db.add(KnowledgePoint(
                        subject_id=subject.id, parent_id=kp1.id, name=child, level=2,
                        path=f"/{level1}/{child}",
                    ))
        logger.info("seeded %d subjects with built-in knowledge tree", len(BUILTIN_SUBJECTS))

    for key, value in DEFAULT_SETTINGS.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value_json=json.dumps(value, ensure_ascii=False)))
    db.commit()
