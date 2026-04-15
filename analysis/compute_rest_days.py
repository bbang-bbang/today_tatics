"""
각 경기에 대해 홈/원정 팀의 직전 경기로부터의 휴식일 계산.
events 테이블에 home_rest_days, away_rest_days 컬럼 추가.

- 같은 tournament_id(K1=410, K2=777) 내에서만 계산 (리그 경기 간격 기준)
- 시즌 첫 경기: NULL (prev 없음)
- 예측 모델에서 fatigue penalty로 사용
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "players.db")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# 컬럼 추가
existing = {r[1] for r in cur.execute("PRAGMA table_info(events)").fetchall()}
for col in ("home_rest_days", "away_rest_days"):
    if col not in existing:
        cur.execute(f"ALTER TABLE events ADD COLUMN {col} INTEGER")
        print(f"  컬럼 추가: {col}")
conn.commit()

# 모든 리그 경기 순회 (날짜순)
for tid_filter, lbl in [(410, "K1"), (777, "K2")]:
    cur.execute("""
        SELECT id, date_ts, home_team_id, away_team_id
        FROM events
        WHERE tournament_id=? AND home_score IS NOT NULL
        ORDER BY date_ts ASC
    """, (tid_filter,))
    games = cur.fetchall()

    # 팀별 직전 경기 date_ts 추적
    last_seen = {}
    updated = 0
    for eid, ts, hid, aid in games:
        h_rest = None
        a_rest = None
        if hid in last_seen:
            h_rest = int((ts - last_seen[hid]) / 86400)
        if aid in last_seen:
            a_rest = int((ts - last_seen[aid]) / 86400)
        cur.execute(
            "UPDATE events SET home_rest_days=?, away_rest_days=? WHERE id=?",
            (h_rest, a_rest, eid)
        )
        updated += 1
        last_seen[hid] = ts
        last_seen[aid] = ts

    print(f"  [{lbl}] {updated}경기 휴식일 계산 완료")

conn.commit()

# 분포 리포트
for tid_filter, lbl in [(410, "K1"), (777, "K2")]:
    cur.execute("""
        SELECT
            MIN(home_rest_days), MAX(home_rest_days), AVG(home_rest_days),
            SUM(CASE WHEN home_rest_days <= 3 THEN 1 ELSE 0 END) as short_rest,
            SUM(CASE WHEN home_rest_days >= 10 THEN 1 ELSE 0 END) as long_rest,
            COUNT(home_rest_days)
        FROM events WHERE tournament_id=? AND home_score IS NOT NULL
          AND home_rest_days IS NOT NULL
    """, (tid_filter,))
    mn, mx, avg, short, long_, tot = cur.fetchone()
    print(f"  [{lbl}] 휴식일: 평균 {avg:.1f}일, 범위 {mn}~{mx}일, "
          f"3일 이하 연전 {short}건, 10일+ 긴 휴식 {long_}건 (총 {tot})")

conn.close()
print("완료!")
