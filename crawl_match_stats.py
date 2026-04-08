#!/usr/bin/env python3
"""
SofaScore 경기별 선수 세부 스탯 수집기
- 대상: 수원 삼성 블루윙즈 (K리그2 2026)
- 엔드포인트: /api/v1/event/{event_id}/lineups
- 저장: SQLite (players.db) → match_player_stats 테이블
"""

import asyncio
import json
import sqlite3
import sys
from playwright.async_api import async_playwright

TEAM_ID       = 7652   # 수원 삼성 블루윙즈
TOURNAMENT_ID = 777    # K리그2
SEASON_ID     = 88837
DB_PATH       = "players.db"
DELAY         = 0.5

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

# ── DB 테이블 초기화 ─────────────────────────────────────
def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS match_player_stats (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id                INTEGER NOT NULL,
            player_id               INTEGER NOT NULL,
            team_id                 INTEGER,
            is_home                 INTEGER,   -- 1=홈, 0=원정
            position                TEXT,
            shirt_number            INTEGER,
            minutes_played          INTEGER,
            rating                  REAL,

            -- 공격
            goals                   INTEGER,
            assists                 INTEGER,
            total_shots             INTEGER,
            shots_on_target         INTEGER,
            big_chances_missed      INTEGER,
            expected_goals          REAL,

            -- 패스
            total_passes            INTEGER,
            accurate_passes         INTEGER,
            accurate_passes_pct     REAL,
            key_passes              INTEGER,
            accurate_long_balls     INTEGER,
            total_long_balls        INTEGER,
            accurate_crosses        INTEGER,
            total_crosses           INTEGER,

            -- 드리블
            successful_dribbles     INTEGER,
            attempted_dribbles      INTEGER,
            touches                 INTEGER,
            possession_lost         INTEGER,

            -- 수비
            tackles                 INTEGER,
            interceptions           INTEGER,
            clearances              INTEGER,
            blocked_shots           INTEGER,
            duel_won                INTEGER,
            duel_lost               INTEGER,
            aerial_won              INTEGER,
            aerial_lost             INTEGER,

            -- 기타
            was_fouled              INTEGER,
            fouls                   INTEGER,
            yellow_cards            INTEGER,
            red_cards               INTEGER,
            saves                   INTEGER,
            goals_conceded          INTEGER,

            raw_json                TEXT,
            UNIQUE(event_id, player_id)
        );

        CREATE INDEX IF NOT EXISTS idx_mps_event  ON match_player_stats(event_id);
        CREATE INDEX IF NOT EXISTS idx_mps_player ON match_player_stats(player_id);
        CREATE INDEX IF NOT EXISTS idx_mps_team   ON match_player_stats(team_id);
    """)
    conn.commit()

# ── API fetch ────────────────────────────────────────────
async def api_fetch(page, path, retries=2):
    for attempt in range(retries + 1):
        try:
            result = await page.evaluate(f"""() =>
                fetch('{path}')
                .then(r => r.ok ? r.json() : r.status)
                .catch(e => ({{error: e.message}}))
            """)
            return result
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

# ── 수원 삼성 경기 목록 수집 ────────────────────────────
async def fetch_team_events(page, team_id):
    """팀의 시즌 전체 경기 event_id 목록 반환"""
    event_ids = []
    page_num = 0
    while True:
        data = await api_fetch(page, f"/api/v1/team/{team_id}/events/last/{page_num}")
        if not isinstance(data, dict):
            break
        events = data.get("events", [])
        if not events:
            break
        for ev in events:
            # K리그2 경기만 필터
            tid = ev.get("tournament", {}).get("uniqueTournament", {}).get("id")
            if tid == TOURNAMENT_ID:
                event_ids.append(ev["id"])
        if not data.get("hasNextPage", False):
            break
        page_num += 1
        await asyncio.sleep(DELAY)

    log(f"수원 삼성 경기 수집: {len(event_ids)}경기")
    return event_ids

# ── 경기별 선수 스탯 파싱 ───────────────────────────────
def parse_stats(s):
    """statistics dict → 컬럼 값 dict (SofaScore 실제 키 기준)"""
    def g(key):
        return s.get(key)
    return {
        "minutes_played":       g("minutesPlayed"),
        "rating":               g("rating"),
        "goals":                g("goals"),
        "assists":              g("goalAssist"),
        "total_shots":          g("totalShots"),
        "shots_on_target":      g("onTargetScoringAttempt"),
        "big_chances_missed":   g("bigChanceMissed"),
        "expected_goals":       g("expectedGoals"),
        "total_passes":         g("totalPass"),
        "accurate_passes":      g("accuratePass"),
        "accurate_passes_pct":  (round(g("accuratePass") / g("totalPass") * 100, 1)
                                  if g("totalPass") else None),
        "key_passes":           g("keyPass"),
        "accurate_long_balls":  g("accurateLongBalls"),
        "total_long_balls":     g("totalLongBalls"),
        "accurate_crosses":     g("accurateCross"),
        "total_crosses":        g("totalCross"),
        "successful_dribbles":  g("wonContest"),
        "attempted_dribbles":   g("totalContest"),
        "touches":              g("touches"),
        "possession_lost":      g("possessionLostCtrl"),
        "tackles":              g("totalTackle"),
        "interceptions":        g("interceptionWon"),
        "clearances":           g("totalClearance"),
        "blocked_shots":        g("outfielderBlock"),
        "duel_won":             g("duelWon"),
        "duel_lost":            g("duelLost"),
        "aerial_won":           g("aerialWon"),
        "aerial_lost":          g("aerialLost"),
        "was_fouled":           g("wasFouled"),
        "fouls":                g("fouls"),
        "yellow_cards":         g("yellowCard"),
        "red_cards":            g("redCard"),
        "saves":                g("saves"),
        "goals_conceded":       g("goalsConceded"),
    }

# ── 경기 라인업에서 수원 삼성 선수 스탯 저장 ────────────
def save_player_stat(conn, event_id, player_id, team_id, is_home,
                     position, shirt_number, stats_raw, s_dict):
    cols = list(s_dict.keys())
    vals = list(s_dict.values())
    conn.execute(f"""
        INSERT OR REPLACE INTO match_player_stats
            (event_id, player_id, team_id, is_home, position, shirt_number,
             {', '.join(cols)}, raw_json)
        VALUES
            (?, ?, ?, ?, ?, ?,
             {', '.join(['?']*len(cols))}, ?)
    """, [event_id, player_id, team_id, is_home, position, shirt_number,
          *vals, json.dumps(stats_raw, ensure_ascii=False)])

# ── 메인 ────────────────────────────────────────────────
async def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.sofascore.com/",
            }
        )
        page = await ctx.new_page()

        log("sofascore 접속 중...")
        await page.goto(
            "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777",
            wait_until="domcontentloaded", timeout=60000
        )
        await asyncio.sleep(3)
        log("세션 준비 완료")

        # 1) 수원 삼성 경기 목록
        event_ids = await fetch_team_events(page, TEAM_ID)

        # 이미 수집된 경기 제외
        existing = {r[0] for r in conn.execute(
            "SELECT DISTINCT event_id FROM match_player_stats WHERE team_id = ?", (TEAM_ID,)
        ).fetchall()}
        todo = [eid for eid in event_ids if eid not in existing]
        log(f"수집 대상: {len(todo)}경기 (이미 완료: {len(existing)}경기)")

        # 2) 경기별 라인업 수집
        for i, eid in enumerate(todo):
            data = await api_fetch(page, f"/api/v1/event/{eid}/lineups")
            if not isinstance(data, dict):
                log(f"  [{i+1}/{len(todo)}] event {eid} 스킵 (응답 없음)")
                await asyncio.sleep(DELAY)
                continue

            saved = 0
            for side, is_home in [("home", 1), ("away", 0)]:
                side_data = data.get(side, {})
                for entry in side_data.get("players", []):
                    # teamId는 각 entry에 직접 있음
                    if entry.get("teamId") != TEAM_ID:
                        continue
                    player = entry.get("player", {})
                    pid = player.get("id")
                    if not pid:
                        continue
                    stats_raw = entry.get("statistics", {})
                    s_dict = parse_stats(stats_raw)
                    pos = entry.get("position", player.get("position", ""))
                    shirt = entry.get("shirtNumber")
                    try:
                        save_player_stat(conn, eid, pid, TEAM_ID, is_home,
                                         pos, shirt, stats_raw, s_dict)
                        saved += 1
                    except Exception as e:
                        log(f"    저장 오류 player {pid}: {e}")

            conn.commit()
            log(f"  [{i+1}/{len(todo)}] event {eid} → {saved}명 저장")
            await asyncio.sleep(DELAY)

        await browser.close()
    conn.close()
    log(f"\n완료! match_player_stats 테이블에 저장됨")

if __name__ == "__main__":
    asyncio.run(main())
