#!/usr/bin/env python3
"""
K2 출전 선수들의 키/몸무게/생년월일/국적을 sofascore에서 수집.
players 테이블에 weight 컬럼 추가 후 upsert.
"""

import asyncio, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.2

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

async def api(page, path):
    for attempt in range(3):
        try:
            r = await page.evaluate(f"""() =>
                fetch('{path}').then(r => r.ok ? r.json() : null).catch(() => null)
            """)
            return r
        except:
            if attempt < 2:
                await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
    return None

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # weight 컬럼 없으면 추가
    cur.execute("PRAGMA table_info(players)")
    cols = {r[1] for r in cur.fetchall()}
    if "weight" not in cols:
        cur.execute("ALTER TABLE players ADD COLUMN weight INTEGER")
        conn.commit()
        log("weight 컬럼 추가 완료")

    # K2 출전 선수 전체 (height 없거나 weight 없는 선수 우선)
    cur.execute("""
        SELECT DISTINCT mps.player_id
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777
        ORDER BY mps.player_id
    """)
    all_pids = [r[0] for r in cur.fetchall()]

    # 이미 height+weight 다 있는 선수 제외
    cur.execute("""
        SELECT id FROM players
        WHERE height IS NOT NULL AND height > 0
          AND weight IS NOT NULL AND weight > 0
    """)
    already = {r[0] for r in cur.fetchall()}
    targets = [p for p in all_pids if p not in already]
    log(f"전체 K2 선수: {len(all_pids)}명 / 신체정보 없음: {len(targets)}명")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료\n")

        ok = skip = 0
        for i, pid in enumerate(targets):
            data = await api(page, f"/api/v1/player/{pid}")
            await asyncio.sleep(DELAY)

            if not data or "player" not in data:
                skip += 1
                continue

            info = data["player"]
            height  = info.get("height")
            weight  = info.get("weight")
            dob     = info.get("dateOfBirthTimestamp")
            nat     = info.get("nationality", {}).get("name") if isinstance(info.get("nationality"), dict) else info.get("nationality")
            foot    = info.get("preferredFoot")
            name    = info.get("name", "")

            if not height and not weight:
                skip += 1
                continue

            # players 테이블에 있으면 update, 없으면 insert
            cur.execute("SELECT id FROM players WHERE id=?", (pid,))
            exists = cur.fetchone()
            if exists:
                cur.execute("""
                    UPDATE players SET
                        height=COALESCE(?,height),
                        weight=COALESCE(?,weight),
                        dob=COALESCE(?,dob),
                        nationality=COALESCE(?,nationality),
                        preferred_foot=COALESCE(?,preferred_foot)
                    WHERE id=?
                """, (height, weight, str(dob) if dob else None, nat, foot, pid))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO players (id, name, height, weight, dob, nationality, preferred_foot)
                    VALUES (?,?,?,?,?,?,?)
                """, (pid, name, height, weight, str(dob) if dob else None, nat, foot))

            ok += 1
            if (i+1) % 50 == 0:
                conn.commit()
                log(f"  [{i+1}/{len(targets)}] 처리 중... (최근: {name} h={height} w={weight})")

        conn.commit()
        await browser.close()

    # 결과 확인
    cur.execute("SELECT COUNT(*) FROM players WHERE height>0 AND weight>0 AND EXISTS (SELECT 1 FROM match_player_stats m JOIN events e ON m.event_id=e.id WHERE m.player_id=players.id AND e.tournament_id=777)")
    filled = cur.fetchone()[0]
    conn.close()
    log(f"\n완료: {ok}명 신체정보 저장 / 스킵: {skip}명")
    log(f"height+weight 보유 K2 선수: {filled}명")

if __name__ == "__main__":
    asyncio.run(main())
