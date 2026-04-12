#!/usr/bin/env python3
"""
K리그1 2026 선수 한국어 이름 최신화
1. K1 경기 출전 선수 중 players 테이블 미등록자 → 등록
2. name_ko 없는 선수 전원 → Sofascore API로 업데이트
"""
import asyncio, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.25

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

def is_ascii_only(s):
    if not s: return True
    try:
        s.encode("ascii"); return True
    except UnicodeEncodeError:
        return False

async def api(page, path):
    for attempt in range(3):
        try:
            return await page.evaluate(f"""() =>
                fetch('{path}').then(r => r.ok ? r.json() : null).catch(() => null)
            """)
        except:
            if attempt < 2:
                await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
    return None

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # K1 출전 선수 전체 ID
    cur.execute("""
        SELECT DISTINCT mps.player_id
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        WHERE e.tournament_id = 410
    """)
    k1_ids = {r[0] for r in cur.fetchall()}

    # 이미 players 테이블에 있는 ID
    cur.execute("SELECT id FROM players")
    existing_ids = {r[0] for r in cur.fetchall()}

    new_ids     = k1_ids - existing_ids   # 신규 등록 필요
    update_ids  = k1_ids & existing_ids   # name_ko 업데이트 대상

    # name_ko 없거나 ASCII인 기존 선수 필터
    if update_ids:
        placeholders = ",".join("?" * len(update_ids))
        cur.execute(f"""
            SELECT id FROM players
            WHERE id IN ({placeholders})
              AND (name_ko IS NULL OR name_ko = ''
                   OR length(name_ko) = length(CAST(name_ko AS BLOB)))
        """, list(update_ids))
        update_ids = {r[0] for r in cur.fetchall()}

    all_targets = sorted(new_ids | update_ids)
    log(f"신규 등록 필요: {len(new_ids)}명 | name_ko 업데이트: {len(update_ids)}명 | 합계: {len(all_targets)}명")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await ctx.new_page()
        await page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료\n")

        inserted = updated = skip = fail = 0
        for i, pid in enumerate(all_targets):
            data = await api(page, f"/api/v1/player/{pid}")
            await asyncio.sleep(DELAY)

            if not data or "player" not in data:
                fail += 1
                continue

            p     = data["player"]
            name  = p.get("name", "")
            ft    = p.get("fieldTranslations", {})
            nt    = ft.get("nameTranslation", {})
            name_ko = nt.get("ko") or None

            # ASCII면 한국어 아님
            if name_ko and is_ascii_only(name_ko):
                name_ko = None

            if pid in new_ids:
                cur.execute("""
                    INSERT OR IGNORE INTO players (id, name, name_ko)
                    VALUES (?, ?, ?)
                """, (pid, name, name_ko))
                inserted += 1
            elif name_ko:
                cur.execute("UPDATE players SET name_ko = ? WHERE id = ?", (name_ko, pid))
                updated += 1
            else:
                skip += 1

            if (i + 1) % 50 == 0:
                conn.commit()
                log(f"  [{i+1}/{len(all_targets)}] 등록 {inserted} / 업데이트 {updated} / 스킵 {skip} / 실패 {fail}")

        conn.commit()
        await browser.close()

    log(f"\n완료: 신규등록 {inserted} / 업데이트 {updated} / 스킵 {skip} / 실패 {fail}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
