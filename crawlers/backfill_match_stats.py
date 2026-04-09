#!/usr/bin/env python3
"""
누락된 경기의 선수 스탯을 재수집 (양 팀 전체 선수)
대상: match_player_stats에 데이터 없는 events (tournament_id=777)
"""
import asyncio, json, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.5

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

def parse_stats(s):
    def g(key): return s.get(key)
    return {
        "minutes_played":      g("minutesPlayed"),
        "rating":              g("rating"),
        "goals":               g("goals"),
        "assists":             g("goalAssist"),
        "total_shots":         g("totalShots"),
        "shots_on_target":     g("onTargetScoringAttempt"),
        "big_chances_missed":  g("bigChanceMissed"),
        "expected_goals":      g("expectedGoals"),
        "total_passes":        g("totalPass"),
        "accurate_passes":     g("accuratePass"),
        "accurate_passes_pct": (round(g("accuratePass")/g("totalPass")*100, 1)
                                 if g("totalPass") else None),
        "key_passes":          g("keyPass"),
        "accurate_long_balls": g("accurateLongBalls"),
        "total_long_balls":    g("totalLongBalls"),
        "accurate_crosses":    g("accurateCross"),
        "total_crosses":       g("totalCross"),
        "successful_dribbles": g("wonContest"),
        "attempted_dribbles":  g("totalContest"),
        "touches":             g("touches"),
        "possession_lost":     g("possessionLostCtrl"),
        "tackles":             g("totalTackle"),
        "interceptions":       g("interceptionWon"),
        "clearances":          g("totalClearance"),
        "blocked_shots":       g("outfielderBlock"),
        "duel_won":            g("duelWon"),
        "duel_lost":           g("duelLost"),
        "aerial_won":          g("aerialWon"),
        "aerial_lost":         g("aerialLost"),
        "was_fouled":          g("wasFouled"),
        "fouls":               g("fouls"),
        "yellow_cards":        g("yellowCard"),
        "red_cards":           g("redCard"),
        "saves":               g("saves"),
        "goals_conceded":      g("goalsConceded"),
    }

async def main():
    conn = sqlite3.connect(DB_PATH)

    # 수집 대상: 스탯이 아예 없는 경기
    rows = conn.execute("""
        SELECT e.id
        FROM events e
        WHERE e.tournament_id = 777 AND e.home_score IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM match_player_stats mps WHERE mps.event_id = e.id
          )
        ORDER BY e.date_ts
    """).fetchall()
    todo = [r[0] for r in rows]
    log(f"수집 대상: {len(todo)}경기")

    # 부분 수집된 경기 중 goals 부족한 것도 추가
    partial = conn.execute("""
        SELECT e.id
        FROM events e
        JOIN (
            SELECT event_id, SUM(goals) as tracked
            FROM match_player_stats GROUP BY event_id
        ) t ON e.id = t.event_id
        WHERE e.tournament_id = 777 AND e.home_score IS NOT NULL
          AND t.tracked < (e.home_score + e.away_score)
          AND (e.home_score + e.away_score) > 0
        ORDER BY e.date_ts
    """).fetchall()
    partial_ids = [r[0] for r in partial if r[0] not in todo]
    log(f"부분 수집 재시도: {len(partial_ids)}경기")
    todo = todo + partial_ids
    log(f"총 처리 대상: {len(todo)}경기")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.sofascore.com/",
            }
        )
        page = await ctx.new_page()
        await page.goto(
            "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777",
            wait_until="domcontentloaded", timeout=60000
        )
        await asyncio.sleep(3)
        log("세션 준비 완료")

        ok = 0
        for i, eid in enumerate(todo):
            try:
                data = await page.evaluate(f"""() =>
                    fetch('/api/v1/event/{eid}/lineups')
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
                """)
            except Exception:
                await page.goto(
                    "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777",
                    wait_until="domcontentloaded", timeout=60000
                )
                await asyncio.sleep(2)
                data = None

            if not isinstance(data, dict):
                log(f"  [{i+1}/{len(todo)}] {eid} 스킵")
                await asyncio.sleep(DELAY)
                continue

            saved = 0
            for side, is_home_flag in [("home", 1), ("away", 0)]:
                side_data = data.get(side, {})
                team_id = side_data.get("teamId")
                for entry in side_data.get("players", []):
                    player = entry.get("player", {})
                    pid = player.get("id")
                    if not pid:
                        continue
                    # teamId: entry 우선, 없으면 side teamId
                    tid = entry.get("teamId") or team_id
                    pname = player.get("name") or player.get("shortName", "")
                    shirt = entry.get("shirtNumber")
                    pos = entry.get("position") or player.get("position", "")
                    stats_raw = entry.get("statistics", {})
                    s_dict = parse_stats(stats_raw)
                    cols = list(s_dict.keys())
                    vals = list(s_dict.values())
                    try:
                        conn.execute(f"""
                            INSERT OR REPLACE INTO match_player_stats
                                (event_id, player_id, team_id, is_home, position,
                                 shirt_number, player_name,
                                 {', '.join(cols)}, raw_json)
                            VALUES
                                (?, ?, ?, ?, ?, ?, ?,
                                 {', '.join(['?']*len(cols))}, ?)
                        """, [eid, pid, tid, is_home_flag, pos, shirt, pname,
                              *vals, json.dumps(stats_raw, ensure_ascii=False)])
                        saved += 1
                    except Exception as e:
                        log(f"    저장 오류 player {pid}: {e}")

            conn.commit()
            ok += 1
            if (i + 1) % 10 == 0:
                log(f"  [{i+1}/{len(todo)}] 완료 ({ok}경기 저장)")
            await asyncio.sleep(DELAY)

        await browser.close()

    # 결과 확인
    cur = conn.cursor()
    cur.execute("""
        SELECT
            strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) as yr,
            COUNT(DISTINCT e.id) as total,
            COUNT(DISTINCT CASE WHEN mps.event_id IS NOT NULL THEN e.id END) as has_stats
        FROM events e
        LEFT JOIN (SELECT DISTINCT event_id FROM match_player_stats WHERE goals > 0) mps
            ON e.id = mps.event_id
        WHERE e.tournament_id = 777 AND e.home_score IS NOT NULL
        GROUP BY yr ORDER BY yr
    """)
    log("\n=== 수집 후 현황 ===")
    for r in cur.fetchall():
        log(f"  {r[0]}: {r[2]}/{r[1]}경기 득점기록 있음")

    conn.close()
    log(f"\n완료! {ok}/{len(todo)}경기 처리")

if __name__ == "__main__":
    asyncio.run(main())
