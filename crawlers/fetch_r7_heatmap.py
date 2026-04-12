#!/usr/bin/env python3
"""R7 (4/11~4/12) 경기 히트맵만 수집"""

import asyncio
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.4
KST     = timezone(timedelta(hours=9))

R7_EVENT_IDS = (15403829, 15403830, 15403831, 15403832,
                15403833, 15403834, 15403835, 15403836)

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

async def api_fetch(page, path, retries=2):
    for attempt in range(retries + 1):
        try:
            return await page.evaluate(f"""() =>
                fetch('{path}')
                .then(r => r.ok ? r.json() : r.status)
                .catch(e => ({{error: e.message}}))
            """)
        except Exception as e:
            if attempt < retries:
                try:
                    await page.goto(
                        "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777",
                        wait_until="domcontentloaded", timeout=60000
                    )
                    await asyncio.sleep(2)
                except Exception:
                    pass
            else:
                return {"error": str(e)}

async def main():
    conn = sqlite3.connect(DB_PATH)

    # 수집 대상: R7 경기에서 히트맵 없는 선수×경기
    rows = conn.execute(f"""
        SELECT mps.event_id, mps.player_id
        FROM match_player_stats mps
        WHERE mps.event_id IN {R7_EVENT_IDS}
          AND NOT EXISTS (
              SELECT 1 FROM heatmap_points hp
              WHERE hp.event_id = mps.event_id AND hp.player_id = mps.player_id
          )
        ORDER BY mps.event_id
    """).fetchall()

    log(f"R7 히트맵 수집 대상: {len(rows)}건 (선수×경기)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            extra_http_headers={"Referer": "https://www.sofascore.com/"}
        )
        page = await ctx.new_page()
        await page.goto(
            "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777",
            wait_until="domcontentloaded", timeout=60000
        )
        await asyncio.sleep(3)
        log("세션 준비 완료")

        batch = []
        for i, (eid, pid) in enumerate(rows):
            hdata = await api_fetch(page, f"/api/v1/event/{eid}/player/{pid}/heatmap")
            if isinstance(hdata, dict):
                pts = hdata.get("heatmap", [])
                batch.extend([(pid, eid, pt["x"], pt["y"]) for pt in pts])

            if len(batch) >= 200:
                conn.executemany(
                    "INSERT OR IGNORE INTO heatmap_points (player_id, event_id, x, y) VALUES (?,?,?,?)",
                    batch
                )
                conn.commit()
                batch = []

            now = datetime.now(tz=KST).strftime("%H:%M:%S")
            log(f"  [{now}] {i+1}/{len(rows)} event {eid} player {pid}")
            await asyncio.sleep(DELAY)

        if batch:
            conn.executemany(
                "INSERT OR IGNORE INTO heatmap_points (player_id, event_id, x, y) VALUES (?,?,?,?)",
                batch
            )
            conn.commit()

        await browser.close()

    conn.close()
    log("\nR7 히트맵 수집 완료!")

if __name__ == "__main__":
    asyncio.run(main())
