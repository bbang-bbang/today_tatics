#!/usr/bin/env python3
"""
K2 출전 선수 중 name_ko 없는 선수들을 sofascore에서 가져와 채우는 스크립트.
- players 테이블에 있으면 name_ko UPDATE
- players 테이블에 없으면 INSERT
- sofascore player.name 이 한글이면 그대로, 영문이면 영문명 사용
"""

import asyncio, sqlite3, sys, re
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.25

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

def is_korean(s):
    return bool(re.search(r'[\uAC00-\uD7A3]', s or ""))

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

    # name_ko 없는 K2 출전 선수 목록
    cur.execute('''
        SELECT DISTINCT mps.player_id, mps.player_name, mps.team_id,
               p.id as p_exists, p.name_ko
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        LEFT JOIN players p ON mps.player_id=p.id
        WHERE e.tournament_id=777
          AND (p.name_ko IS NULL OR p.name_ko = "" OR p.id IS NULL)
        ORDER BY mps.player_id
    ''')
    targets = cur.fetchall()
    log(f"처리 대상: {len(targets)}명")

    # 손호준 먼저 수동 추가
    manual = {1002465: "손호준"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료\n")

        ok = 0
        for i, (pid, mps_name, team_id, p_exists, _) in enumerate(targets):
            # 수동 매핑 우선
            if pid in manual:
                ko_name = manual[pid]
            else:
                data = await api(page, f"/api/v1/player/{pid}")
                await asyncio.sleep(DELAY)

                if not data or "player" not in data:
                    # API 실패 시 영문명이라도 넣기
                    ko_name = mps_name or ""
                else:
                    pinfo = data["player"]
                    sf_name = pinfo.get("name", "") or ""
                    # sofascore가 한국어로 주면 그대로, 아니면 영문명 사용
                    ko_name = sf_name if sf_name else (mps_name or "")

            if not ko_name:
                continue

            if p_exists:
                cur.execute("UPDATE players SET name_ko=? WHERE id=?", (ko_name, pid))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO players (id, name, name_ko, team_id)
                    VALUES (?, ?, ?, ?)
                """, (pid, mps_name or ko_name, ko_name, team_id))

            ok += 1
            if (i+1) % 20 == 0:
                conn.commit()
                log(f"  [{i+1}/{len(targets)}] 저장 중... (최근: {ko_name})")

        conn.commit()
        await browser.close()

    # 결과 확인
    cur.execute('''
        SELECT COUNT(DISTINCT mps.player_id)
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        LEFT JOIN players p ON mps.player_id=p.id
        WHERE e.tournament_id=777
          AND (p.name_ko IS NULL OR p.name_ko = "" OR p.id IS NULL)
    ''')
    remaining = cur.fetchone()[0]
    conn.close()

    log(f"\n완료: {ok}명 처리 / 아직 name_ko 없음: {remaining}명")

if __name__ == "__main__":
    asyncio.run(main())
