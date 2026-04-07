#!/usr/bin/env python3
"""
기존 heatmap_points의 event_id에 대해 경기 메타데이터를 채워넣는 백필 스크립트
"""

import asyncio
import sqlite3
import sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY = 0.3

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 기존 events 테이블에 컬럼 없으면 추가
    existing = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    for col, typedef in [
        ("date_ts",       "INTEGER"),
        ("home_score",    "INTEGER"),
        ("away_score",    "INTEGER"),
        ("tournament_id", "INTEGER"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {typedef}")
    conn.commit()

    # 메타데이터가 없는 event_id 목록
    rows = conn.execute("""
        SELECT DISTINCT h.event_id FROM heatmap_points h
        LEFT JOIN events e ON h.event_id = e.id
        WHERE e.date_ts IS NULL
    """).fetchall()
    event_ids = [r["event_id"] for r in rows]
    log(f"백필 대상 경기: {len(event_ids)}개")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        for i, eid in enumerate(event_ids):
            resp = await page.request.get(f"https://www.sofascore.com/api/v1/event/{eid}")
            if resp.status != 200:
                log(f"  [{i+1}/{len(event_ids)}] event {eid} → 실패({resp.status})")
                await asyncio.sleep(DELAY)
                continue

            data = await resp.json()
            event = data.get("event", {})
            ht = event.get("homeTeam", {})
            at = event.get("awayTeam", {})
            hs = event.get("homeScore", {}).get("current")
            as_ = event.get("awayScore", {}).get("current")
            ts = event.get("startTimestamp")
            tid = event.get("tournament", {}).get("uniqueTournament", {}).get("id")

            conn.execute("""
                INSERT OR REPLACE INTO events
                    (id, home_team_id, home_team_name, away_team_id, away_team_name,
                     date_ts, home_score, away_score, tournament_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (eid, ht.get("id"), ht.get("name"), at.get("id"), at.get("name"),
                  ts, hs, as_, tid))
            conn.commit()

            if (i + 1) % 50 == 0 or i == 0:
                log(f"  [{i+1}/{len(event_ids)}] {ht.get('name')} vs {at.get('name')} ({ts})")

            await asyncio.sleep(DELAY)

        await browser.close()

    conn.close()
    log("백필 완료!")

if __name__ == "__main__":
    asyncio.run(main())
