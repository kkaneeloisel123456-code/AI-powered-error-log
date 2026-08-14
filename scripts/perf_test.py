"""万级数据性能压测（T-M5-06 / PRD 7.9-28 / NFR-01/05）。

用法（后端已启动）：
    python scripts/perf_test.py --base http://127.0.0.1:8000 [--seed 10000] [--no-seed]

验证指标：
    - 列表 P95 < 500ms（含搜索/筛选）
    - 看板聚合 < 2s
    - 导出 Markdown 可用（200 题截断）
"""
import argparse
import random
import statistics
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os_env = __import__("os")


def get_token(base: str, data_dir: Path) -> str:
    token_file = data_dir / "auth" / "token.key"
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        print(f"[auth] 使用本地令牌 {token[:8]}…（{token_file}）")
        return token
    print(f"[auth] 令牌文件不存在（{token_file}），尝试 setup 揭示")
    with httpx.Client(base_url=base, timeout=10) as client:
        resp = client.post("/api/v1/auth/setup")
        body = resp.json()
        if not body.get("token"):
            raise SystemExit("setup 无法揭示令牌：请删除 data/auth 下 auth 设置后重试，或检查后端数据目录是否一致")
        return body["token"]


def seed_data(base: str, headers: dict, count: int) -> None:
    """直连 SQLite 批量插入（避开 HTTP 逐条开销），复用内置学科与知识点。"""
    from app.core.config import get_settings
    from app.db.models import KnowledgePoint, Mistake, PlanItem, Problem, STATUS_COLORS, Subject
    from app.db.session import get_sessionmaker, reset_engine
    reset_engine()
    db = get_sessionmaker()()
    try:
        subjects = db.query(Subject).all()
        kps = db.query(KnowledgePoint).all()
        existing = db.query(Mistake).count()
        if existing >= count:
            print(f"[seed] 已有 {existing} 条错题，跳过（如需重建请删除 data/recall.sqlite3）")
            return
        need = count - existing
        print(f"[seed] 批量插入 {need} 条错题…")
        t0 = time.monotonic()
        batch = 500
        statuses = ["pending", "wrong", "fixing", "mastered"]
        errors = ["knowledge", "logic", "reading", "calculation", "concept", "careless", "other"]
        for i in range(need):
            kp = random.choice(kps) if kps else None
            subject = db.get(Subject, kp.subject_id) if kp else random.choice(subjects)
            problem = Problem(
                question_text=f"压测题目第 {i} 号：已知某物体做匀变速直线运动，加速度 a={random.randint(1, 9)}m/s²，"
                              f"初速度 v0={random.randint(0, 20)}m/s，求 t={random.randint(1, 10)}s 内位移。",
                options_json='["A. 10m", "B. 20m", "C. 30m", "D. 40m"]',
                answer_text=random.choice(["A", "B", "C", "D"]),
                analysis="由位移公式 x = v0t + 1/2 at² 计算。",
                difficulty="medium",
            )
            db.add(problem)
            db.flush()
            status = random.choice(statuses)
            mistake = Mistake(
                problem_id=problem.id,
                subject_id=subject.id if subject else subjects[0].id,
                kp_id=kp.id if kp else None,
                error_type=random.choice(errors),
                status=status,
                color=STATUS_COLORS[status],
                tags_json='["压测"]',
                source=random.choice(["image", "text"]),
                first_seen_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                last_reviewed_at=datetime.now() - timedelta(days=random.randint(0, 7)),
                review_count=random.randint(0, 5),
                correct_count=random.randint(0, 3),
                wrong_count=random.randint(0, 3),
                mastery=random.random(),
                created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
            )
            db.add(mistake)
            db.flush()
            db.add(PlanItem(mistake_id=mistake.id, due_date=date.today() + timedelta(days=random.randint(0, 10)),
                            interval_days=random.randint(1, 15), ease_factor=2.5, status="pending"))
            if i % batch == 0:
                db.commit()
        db.commit()
        print(f"[seed] 完成 {need} 条，耗时 {time.monotonic() - t0:.1f}s")
    finally:
        db.close()


def measure(client: httpx.Client, name: str, method: str, path: str, runs: int = 5) -> list[float]:
    times = []
    for _ in range(runs):
        t0 = time.monotonic()
        resp = getattr(client, method)(path)
        resp.raise_for_status()
        times.append((time.monotonic() - t0) * 1000)
    p95 = statistics.quantiles(times, n=20)[18] if runs >= 20 else max(times)
    print(f"[perf] {name:<28} 平均 {statistics.mean(times):7.1f}ms  P95 {p95:7.1f}ms  (n={runs})")
    return times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--seed", type=int, default=10000)
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    from app.core.config import get_settings
    data_dir = get_settings().data_dir
    token = get_token(args.base, data_dir)
    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(base_url=args.base, timeout=30, headers=headers)

    if not args.no_seed:
        seed_data(args.base, headers, args.seed)

    print("\n== 性能基线（万级数据）==")
    measure(client, "列表分页", "get", "/api/v1/mistakes?page=1&page_size=20")
    measure(client, "关键词搜索", "get", "/api/v1/mistakes?q=%E5%8A%A0%E9%80%9F%E5%BA%A6&page=1")
    measure(client, "组合筛选", "get", "/api/v1/mistakes?subject_id=4&status=wrong&error_type=calculation")
    measure(client, "标签筛选", "get", "/api/v1/mistakes?tags=%E5%8E%8B%E6%B5%8B")
    measure(client, "看板聚合 7d", "get", "/api/v1/dashboard/summary?range_days=7")
    measure(client, "看板聚合 30d", "get", "/api/v1/dashboard/summary?range_days=30")
    measure(client, "知识图谱", "get", "/api/v1/graph/knowledge")
    t0 = time.monotonic()
    resp = client.get("/api/v1/export/markdown")
    print(f"[perf] {'导出 Markdown(200题截断)':<28} 耗时 {(time.monotonic() - t0) * 1000:7.1f}ms  大小 {len(resp.content) // 1024}KB")
    measure(client, "今日计划", "get", "/api/v1/plans/today")
    print("\n结论：列表类需 P95 < 500ms；看板 < 2s（NFR-01/05/06）。")


if __name__ == "__main__":
    main()
