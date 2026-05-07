#!/usr/bin/env python3
"""
players 마스터 갱신 — lineup/mps에 등장한 모든 player_id를 대상으로
SofaScore /api/v1/player/{id} 호출 → 신규 INSERT 또는 누락 필드 UPDATE.

대상 우선순위 (NOT EXISTS 또는 누락 필드 보유):
1. mps/lineup에는 있는데 players에 없는 orphan
2. players에는 있지만 position/team_id/height/nationality 등 누락

레거시 fill_player_physical.py는 K2(777) 한정 + height/weight 위주였음.
이 스크립트는 K1+K2 양 리그, 모든 누락 필드 일괄.

옵션:
  --limit N      최대 N명 처리 (테스트용)
  --refetch      이미 모든 필드 있는 선수도 강제 재조회
"""

import argparse
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE / "players.db")
DELAY = 0.25


def log(msg):
    print(msg, flush=True)


async def api(page, path, retries=2):
    for attempt in range(retries + 1):
        try:
            return await page.evaluate(f"""() =>
                fetch('{path}').then(r => r.ok ? r.json() : null).catch(() => null)
            """)
        except Exception:
            if attempt < retries:
                try:
                    await page.goto("https://www.sofascore.com",
                                    wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                except Exception:
                    pass
    return None


def collect_targets(conn, refetch=False):
    """
    대상 = mps + lineup union의 player_id에서 다음 중 하나:
      - players에 row 없음 (orphan)
      - players에 있지만 position/team_id/height/nationality 중 하나라도 NULL
      - refetch=True
    """
    rows = conn.execute("""
        WITH used AS (
            SELECT DISTINCT player_id FROM match_lineups
            UNION
            SELECT DISTINCT player_id FROM match_player_stats
        )
        SELECT u.player_id,
               p.id IS NOT NULL AS has_row,
               COALESCE(p.position, '') AS pos,
               COALESCE(p.team_id, 0)    AS tid,
               COALESCE(p.height, 0)     AS h,
               COALESCE(p.nationality, '') AS nat
        FROM used u LEFT JOIN players p ON p.id = u.player_id
        ORDER BY u.player_id
    """).fetchall()
    targets = []
    for pid, has_row, pos, tid, h, nat in rows:
        if not has_row:
            targets.append(pid)
        elif refetch:
            targets.append(pid)
        elif (not pos) or (not tid) or (h == 0) or (not nat):
            targets.append(pid)
    return targets


def upsert_player(conn, pid, info):
    name = info.get("name") or ""
    pos = info.get("position")
    team_obj = info.get("team") or {}
    team_id = team_obj.get("id")
    height = info.get("height")
    weight = info.get("weight")
    dob = info.get("dateOfBirthTimestamp")
    nat_obj = info.get("nationality") or info.get("country") or {}
    nationality = nat_obj.get("name") if isinstance(nat_obj, dict) else (nat_obj or None)
    foot = info.get("preferredFoot")
    shirt = info.get("shirtNumber")

    cur = conn.execute("SELECT id FROM players WHERE id=?", (pid,))
    exists = cur.fetchone()
    if exists:
        conn.execute("""
            UPDATE players SET
                name           = COALESCE(NULLIF(?, ''), name),
                team_id        = COALESCE(?, team_id),
                position       = COALESCE(NULLIF(?, ''), position),
                height         = COALESCE(?, height),
                weight         = COALESCE(?, weight),
                dob            = COALESCE(?, dob),
                nationality    = COALESCE(NULLIF(?, ''), nationality),
                preferred_foot = COALESCE(NULLIF(?, ''), preferred_foot),
                shirt_number   = COALESCE(?, shirt_number)
            WHERE id=?
        """, (name, team_id, pos or "", height, weight,
              str(dob) if dob else None, nationality or "", foot or "",
              shirt, pid))
    else:
        conn.execute("""
            INSERT INTO players
              (id, team_id, name, position, nationality, dob, height,
               preferred_foot, shirt_number, weight)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (pid, team_id, name, pos, nationality,
              str(dob) if dob else None, height, foot, shirt, weight))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    targets = collect_targets(conn, refetch=args.refetch)
    if args.limit:
        targets = targets[:args.limit]
    log(f"대상: {len(targets)}명 (refetch={args.refetch})")
    if not targets:
        log("처리할 대상 없음")
        return

    ok = skip = 0
    t0 = time.time()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com",
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료")

        for i, pid in enumerate(targets):
            data = await api(page, f"/api/v1/player/{pid}")
            await asyncio.sleep(DELAY)
            if not data or "player" not in data:
                skip += 1
                continue
            try:
                upsert_player(conn, pid, data["player"])
                ok += 1
            except Exception as e:
                log(f"  upsert fail pid={pid}: {e}")
                skip += 1

            if (i + 1) % 50 == 0:
                conn.commit()
                log(f"  [{i+1}/{len(targets)}] ok={ok} skip={skip}")

        conn.commit()
        await browser.close()

    log(f"\n완료: ok={ok} skip={skip} ({time.time()-t0:.1f}s)")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
