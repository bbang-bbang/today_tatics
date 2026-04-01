import asyncio, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY = 0.25

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 아직 events 테이블에 없는 event_id만 수집
    cur.execute("""
        SELECT DISTINCT h.event_id FROM heatmap_points h
        LEFT JOIN events e ON h.event_id = e.id
        WHERE e.id IS NULL
    """)
    event_ids = [r[0] for r in cur.fetchall()]
    log(f"수집할 이벤트 수: {len(event_ids)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com/tournament/football/south-korea/k-league-1/410", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료")

        batch = []
        for i, eid in enumerate(event_ids):
            try:
                data = await page.evaluate(f"""() =>
                    fetch('/api/v1/event/{eid}')
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
                """)
                if data and isinstance(data, dict):
                    event = data.get("event", {})
                    home_id = event.get("homeTeam", {}).get("id")
                    away_id = event.get("awayTeam", {}).get("id")
                    if home_id and away_id:
                        batch.append((eid, home_id, away_id))
            except Exception as e:
                try:
                    await page.goto("https://www.sofascore.com/tournament/football/south-korea/k-league-1/410", wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(2)
                except:
                    pass

            if len(batch) >= 100:
                conn.executemany("INSERT OR REPLACE INTO events (id, home_team_id, away_team_id) VALUES (?,?,?)", batch)
                conn.commit()
                batch = []

            if (i + 1) % 100 == 0:
                log(f"진행: {i+1}/{len(event_ids)}")

            await asyncio.sleep(DELAY)

        if batch:
            conn.executemany("INSERT OR REPLACE INTO events (id, home_team_id, away_team_id) VALUES (?,?,?)", batch)
            conn.commit()

        await browser.close()
    conn.close()
    log("완료!")

asyncio.run(main())
