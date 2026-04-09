#!/usr/bin/env python3
"""
match_player_stats의 player_name 공백 채우기
SofaScore /api/v1/player/{player_id} 에서 이름 수집
"""
import asyncio, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.3

def log(msg):
    sys.stdout.buffer.write((msg+"\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

async def main():
    conn = sqlite3.connect(DB_PATH)

    # 이름이 없는 고유 player_id 목록
    rows = conn.execute("""
        SELECT DISTINCT player_id, team_id FROM match_player_stats
        WHERE player_name IS NULL
        ORDER BY team_id, player_id
    """).fetchall()
    log(f"이름 수집 대상: {len(rows)}명")

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

        for i, (pid, team_id) in enumerate(rows):
            try:
                data = await page.evaluate(f"""() =>
                    fetch('/api/v1/player/{pid}')
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
                """)
                if data and isinstance(data, dict):
                    name = data.get("player", {}).get("name")
                    if name:
                        conn.execute(
                            "UPDATE match_player_stats SET player_name=? WHERE player_id=? AND player_name IS NULL",
                            (name, pid)
                        )
            except Exception:
                pass

            if (i + 1) % 100 == 0:
                conn.commit()
                log(f"  {i+1}/{len(rows)} 완료")

            await asyncio.sleep(DELAY)

        conn.commit()
        await browser.close()

    filled = conn.execute("SELECT COUNT(*) FROM match_player_stats WHERE player_name IS NOT NULL").fetchone()[0]
    total  = conn.execute("SELECT COUNT(*) FROM match_player_stats").fetchone()[0]
    log(f"\n완료! {filled}/{total} 이름 채워짐")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
