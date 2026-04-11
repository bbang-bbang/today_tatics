#!/usr/bin/env python3
"""
SofaScore /api/v1/team/{id}/players 에서 선수 ID 기반으로
players 테이블의 name_ko를 업데이트한다.

로스터 API 구조: { players: [{ player: { id, name, shirtNumber, ... } }, ...] }
"""
import asyncio, sqlite3, sys, json, re
from playwright.async_api import async_playwright

DB_PATH   = "players.db"
JSON_PATH = "data/kleague_players_2026.json"
DELAY     = 0.3

TEAMS = {
    'ulsan': 7653, 'pohang': 7650, 'jeju': 7649, 'jeonbuk': 6908,
    'fcseoul': 7646, 'daejeon': 7645, 'incheon': 7648, 'gangwon': 34220,
    'gwangju': 48912, 'bucheon': 92539, 'anyang': 32675, 'gimcheon': 7647,
    'suwon': 7652, 'busan': 7642, 'jeonnam': 7643, 'seongnam': 7651,
    'daegu': 7644, 'gyeongnam': 22020, 'suwon_fc': 41261, 'seouland': 189422,
    'ansan': 248375, 'asan': 339827, 'gimpo': 195172, 'cheongju': 314293,
    'cheonan': 41263, 'hwaseong': 195174, 'paju': 314294, 'gimhae': 41260, 'yongin': 41266,
}

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

def is_korean(s):
    return bool(s and re.search(r'[가-힣]', s))

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
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    with open(JSON_PATH, encoding="utf-8") as f:
        jdata = json.load(f)

    # 미매핑 선수 집합
    cur.execute("""
        SELECT DISTINCT p.id, p.name, p.name_ko
        FROM players p
        JOIN match_player_stats m ON p.id = m.player_id
        WHERE p.name_ko IS NULL OR p.name_ko = ''
           OR length(p.name_ko) = length(CAST(p.name_ko AS BLOB))
        GROUP BY p.id
    """)
    unmapped = {r["id"]: dict(r) for r in cur.fetchall()}
    log(f"미매핑 선수: {len(unmapped)}명")

    updated = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료\n")

        for slug, ss_id in TEAMS.items():
            if slug not in jdata:
                continue

            # JSON에서 등번호 → 한국어 이름 맵
            num_to_ko = {}
            for p in jdata[slug].get("players", []):
                if p.get("number") and is_korean(p.get("name", "")):
                    num_to_ko[p["number"]] = p["name"]

            # SofaScore 로스터 API
            data = await api(page, f"/api/v1/team/{ss_id}/players")
            await asyncio.sleep(DELAY)

            if not data:
                log(f"[{slug}] API 실패")
                continue

            # 올바른 구조: players 배열 내 각 항목이 { player: {...} }
            roster_items = data.get("players", [])
            slug_updated = 0

            for item in roster_items:
                # player 키 안에 실제 선수 정보
                p = item.get("player") or item
                pid  = p.get("id")
                if pid not in unmapped:
                    continue

                shirt = p.get("shirtNumber") or p.get("jerseyNumber")
                ko_name = num_to_ko.get(shirt) if shirt else None

                if ko_name and is_korean(ko_name):
                    cur.execute("UPDATE players SET name_ko=? WHERE id=?", (ko_name, pid))
                    slug_updated += 1
                    updated += 1
                    del unmapped[pid]
                    log(f"  [{slug}] {p.get('name')} → {ko_name} (#{shirt})")

            if slug_updated:
                conn.commit()
                log(f"[{slug}] {slug_updated}명 업데이트")

        await browser.close()

    conn.commit()
    log(f"\n완료: 총 {updated}명 업데이트 / 여전히 미매핑: {len(unmapped)}명")

    if unmapped:
        log("\n여전히 미매핑 선수 (샘플 20명):")
        for pid, r in list(unmapped.items())[:20]:
            log(f"  id={pid} | {r['name']}")

    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
