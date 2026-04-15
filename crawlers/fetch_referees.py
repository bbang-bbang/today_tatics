#!/usr/bin/env python3
"""
K1 경기 심판 정보 수집 — SofaScore /api/v1/event/{id}
- K2는 원천 부재 확인됨 (심판 null)
- events 테이블에 referee_id, referee_name 추가
- referees 테이블 신규 (career cards/games 통산 저장)

모델 활용:
- 각 심판의 per-game 평균 카드/PK 빈도 → 베팅 라인 보정용
- 직접적 1X2 영향은 제한적이지만 스코어/카드 예측에 의미
"""

import argparse
import asyncio
import os
import sqlite3
import sys
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "players.db")
DELAY    = 0.3


def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def ensure_schema(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    for col, typedef in [
        ("referee_id",   "INTEGER"),
        ("referee_name", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {typedef}")
            log(f"  컬럼 추가 (events): {col}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS referees (
            id             INTEGER PRIMARY KEY,
            name           TEXT,
            country        TEXT,
            career_games   INTEGER,
            career_yellow  INTEGER,
            career_red     INTEGER,
            career_yellow_red INTEGER,
            updated_at     TEXT
        )
    """)
    conn.commit()


async def api_fetch(page, path):
    try:
        return await page.evaluate(f"""async()=>{{
            const r = await fetch('{path}');
            return r.ok ? r.json() : null;
        }}""")
    except Exception:
        return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", choices=["K1", "K2"], default="K1")
    parser.add_argument("--force",  action="store_true", help="이미 수집된 경기도 재수집")
    args = parser.parse_args()

    tid_filter = 410 if args.league == "K1" else 777

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    ensure_schema(conn)

    if args.force:
        cur.execute("""SELECT id FROM events WHERE tournament_id=? AND home_score IS NOT NULL
                       ORDER BY date_ts DESC""", (tid_filter,))
    else:
        cur.execute("""SELECT id FROM events WHERE tournament_id=? AND home_score IS NOT NULL
                         AND referee_id IS NULL
                       ORDER BY date_ts DESC""", (tid_filter,))
    target_events = [r[0] for r in cur.fetchall()]
    log(f"[{args.league}] 심판 수집 대상: {len(target_events)}경기")
    if not target_events:
        return

    import datetime
    now_iso = datetime.datetime.now().isoformat()

    session_url = ("https://www.sofascore.com/tournament/football/south-korea/k-league-1/410"
                   if args.league == "K1"
                   else "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777")

    ok = no_ref = 0
    refs_upserted = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto(session_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료")

        for i, eid in enumerate(target_events):
            data = await api_fetch(page, f"/api/v1/event/{eid}")
            if not isinstance(data, dict) or "event" not in data:
                await asyncio.sleep(DELAY)
                continue

            ref = (data["event"] or {}).get("referee")
            if not ref:
                no_ref += 1
                await asyncio.sleep(DELAY)
                continue

            rid   = ref.get("id")
            rname = ref.get("name", "")
            if rid:
                cur.execute("""
                    UPDATE events SET referee_id=?, referee_name=? WHERE id=?
                """, (rid, rname, eid))

                if rid not in refs_upserted:
                    cur.execute("""
                        INSERT OR REPLACE INTO referees
                        (id, name, country, career_games, career_yellow, career_red, career_yellow_red, updated_at)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        rid,
                        rname,
                        (ref.get("country") or {}).get("name", ""),
                        ref.get("games"),
                        ref.get("yellowCards"),
                        ref.get("redCards"),
                        ref.get("yellowRedCards"),
                        now_iso,
                    ))
                    refs_upserted.add(rid)

                ok += 1
                if (i+1) % 50 == 0:
                    conn.commit()
                    log(f"  [{i+1}/{len(target_events)}] ok={ok} no_ref={no_ref} refs={len(refs_upserted)}")

            await asyncio.sleep(DELAY)

        conn.commit()
        await browser.close()

    log(f"\n완료: 경기 {ok} / 심판 미기록 {no_ref} / 유니크 심판 {len(refs_upserted)}명")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
