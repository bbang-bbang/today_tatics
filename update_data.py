#!/usr/bin/env python3
"""
수원 삼성 데이터 증분 업데이트
1. 새 경기 선수 스탯 (match_player_stats)
2. 새 경기 히트맵 (heatmap_points) — 새 event_id × player_id 쌍만
3. 새 경기 경기장 (events.venue_*)
4. 새 경기 날씨 (match_player_stats.temperature 등)
"""

import asyncio
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

TEAM_ID       = 7652
TOURNAMENT_ID = 777
DB_PATH       = "players.db"
DELAY         = 0.5
KST           = timezone(timedelta(hours=9))

WEATHER_CODE_MAP = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "결빙 안개",
    51: "가벼운 이슬비", 53: "이슬비", 55: "짙은 이슬비",
    61: "가벼운 비", 63: "비", 65: "강한 비",
    71: "가벼운 눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "강한 소나기", 82: "폭우",
    95: "뇌우", 96: "우박 뇌우", 99: "강한 우박 뇌우",
}

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

# ── API ─────────────────────────────────────────────────
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

# ── STEP 1: 새 경기 스탯 ────────────────────────────────
def parse_stats(s):
    def g(k): return s.get(k)
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
        "accurate_passes_pct": (round(g("accuratePass") / g("totalPass") * 100, 1)
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

async def step1_match_stats(page, conn):
    log("\n[STEP 1] 새 경기 선수 스탯 수집")

    # 팀 전체 경기 목록
    event_ids, page_num = [], 0
    while True:
        data = await api_fetch(page, f"/api/v1/team/{TEAM_ID}/events/last/{page_num}")
        if not isinstance(data, dict): break
        events = data.get("events", [])
        if not events: break
        for ev in events:
            tid = ev.get("tournament", {}).get("uniqueTournament", {}).get("id")
            if tid == TOURNAMENT_ID:
                event_ids.append(ev["id"])
        if not data.get("hasNextPage", False): break
        page_num += 1
        await asyncio.sleep(DELAY)

    existing_stats = {r[0] for r in conn.execute(
        "SELECT DISTINCT event_id FROM match_player_stats WHERE team_id=?", (TEAM_ID,)
    ).fetchall()}
    existing_events = {r[0] for r in conn.execute("SELECT id FROM events").fetchall()}

    # 신규 경기 + events 테이블에 누락된 기존 경기 모두 처리
    orphan = existing_stats - existing_events  # stats는 있는데 events가 없는 경기
    todo = [eid for eid in event_ids if eid not in existing_stats] + list(orphan)
    log(f"  전체 {len(event_ids)}경기 중 신규 {len(todo) - len(orphan)}경기, events 누락 {len(orphan)}경기")

    new_event_ids = []
    for i, eid in enumerate(todo):
        is_orphan = eid in orphan

        # events 테이블 저장 (항상)
        ev_data = await api_fetch(page, f"/api/v1/event/{eid}")
        if isinstance(ev_data, dict):
            ev = ev_data.get("event", {})
            ht = ev.get("homeTeam", {}); at = ev.get("awayTeam", {})
            conn.execute("""
                INSERT OR REPLACE INTO events
                    (id, home_team_id, home_team_name, away_team_id, away_team_name,
                     date_ts, home_score, away_score, tournament_id)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                eid,
                ht.get("id"), ht.get("name"),
                at.get("id"), at.get("name"),
                ev.get("startTimestamp"),
                ev.get("homeScore", {}).get("current"),
                ev.get("awayScore", {}).get("current"),
                TOURNAMENT_ID,
            ))
            conn.commit()

        # orphan 경기는 stats 재수집 불필요
        if is_orphan:
            log(f"  [{i+1}/{len(todo)}] event {eid} → events 메타데이터 복구 완료")
            new_event_ids.append(eid)
            await asyncio.sleep(DELAY)
            continue

        data = await api_fetch(page, f"/api/v1/event/{eid}/lineups")
        if not isinstance(data, dict):
            await asyncio.sleep(DELAY)
            continue

        saved = 0
        for side, is_home in [("home", 1), ("away", 0)]:
            for entry in data.get(side, {}).get("players", []):
                if entry.get("teamId") != TEAM_ID: continue
                player = entry.get("player", {})
                pid = player.get("id")
                if not pid: continue
                stats_raw = entry.get("statistics", {})
                s_dict = parse_stats(stats_raw)
                cols = list(s_dict.keys()); vals = list(s_dict.values())
                conn.execute(f"""
                    INSERT OR REPLACE INTO match_player_stats
                        (event_id, player_id, team_id, is_home, position, shirt_number,
                         {', '.join(cols)}, raw_json)
                    VALUES (?,?,?,?,?,?, {', '.join(['?']*len(cols))}, ?)
                """, [eid, pid, TEAM_ID, is_home,
                      entry.get("position"), entry.get("shirtNumber"),
                      *vals, json.dumps(stats_raw, ensure_ascii=False)])
                saved += 1

        conn.commit()
        log(f"  [{i+1}/{len(todo)}] event {eid} → {saved}명")
        new_event_ids.append(eid)
        await asyncio.sleep(DELAY)

    # result 컬럼 업데이트
    conn.execute("""
        UPDATE match_player_stats
        SET result = (
            SELECT CASE
                WHEN match_player_stats.is_home=1 AND e.home_score > e.away_score THEN 2
                WHEN match_player_stats.is_home=0 AND e.away_score > e.home_score THEN 2
                WHEN e.home_score = e.away_score THEN 1
                ELSE 0
            END
            FROM events e WHERE e.id = match_player_stats.event_id
        )
        WHERE team_id=? AND result IS NULL
    """, (TEAM_ID,))
    conn.commit()
    return new_event_ids

# ── STEP 2: 새 경기 히트맵 ──────────────────────────────
async def step2_heatmap(page, conn, new_event_ids):
    log("\n[STEP 2] 새 경기 히트맵 수집")
    if not new_event_ids:
        log("  새 경기 없음, 스킵")
        return

    for eid in new_event_ids:
        # 해당 경기 수원 삼성 선수 목록
        players = conn.execute(
            "SELECT DISTINCT player_id FROM match_player_stats WHERE event_id=? AND team_id=?",
            (eid, TEAM_ID)
        ).fetchall()

        pts_total = 0
        for (pid,) in players:
            hdata = await api_fetch(page, f"/api/v1/event/{eid}/player/{pid}/heatmap")
            if isinstance(hdata, dict):
                pts = hdata.get("heatmap", [])
                if pts:
                    conn.executemany(
                        "INSERT OR IGNORE INTO heatmap_points (player_id, event_id, x, y) VALUES (?,?,?,?)",
                        [(pid, eid, pt["x"], pt["y"]) for pt in pts]
                    )
                    pts_total += len(pts)
            await asyncio.sleep(DELAY * 0.5)

        conn.commit()
        log(f"  event {eid} → {pts_total}pts")
        await asyncio.sleep(DELAY)

# ── STEP 3: 새 경기 경기장 ──────────────────────────────
def is_valid_korea(lat, lon):
    return 33 <= lat <= 39 and 124 <= lon <= 132

def nominatim_geocode(name, city):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": f"{name}, {city}, South Korea", "format": "json", "limit": 1}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "today_tactics/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read())
        if res: return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception as e:
        log(f"  Nominatim 오류: {e}")
    return None, None

async def step3_venues(page, conn, new_event_ids):
    log("\n[STEP 3] 새 경기 경기장 수집")
    if not new_event_ids:
        log("  새 경기 없음, 스킵")
        return

    for eid in new_event_ids:
        data = await api_fetch(page, f"/api/v1/event/{eid}")
        if not isinstance(data, dict): continue
        ev = data.get("event", {}); ht = ev.get("homeTeam", {})
        venue = ht.get("venue", {})
        v_name = venue.get("name") or venue.get("stadium", {}).get("name")
        v_city = venue.get("city", {}).get("name", "")
        coords = venue.get("venueCoordinates", {})
        raw_lat, raw_lon = coords.get("latitude"), coords.get("longitude")
        lat = lon = None
        if raw_lat and raw_lon:
            if is_valid_korea(raw_lat, raw_lon): lat, lon = raw_lat, raw_lon
            elif is_valid_korea(raw_lon, raw_lat): lat, lon = raw_lon, raw_lat
        if lat is None and v_name:
            lat, lon = nominatim_geocode(v_name, v_city)
            time.sleep(1.1)
        conn.execute(
            "UPDATE events SET venue_name=?, venue_city=?, venue_lat=?, venue_lon=? WHERE id=?",
            (v_name, v_city, lat, lon, eid)
        )
        conn.commit()
        log(f"  event {eid} | {v_name} ({v_city}) | {lat},{lon}")
        await asyncio.sleep(DELAY)

# ── STEP 4: 새 경기 날씨 ────────────────────────────────
def fetch_weather(date_str, hour, lat, lon):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={date_str}&end_date={date_str}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        f"&timezone=Asia%2FSeoul"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        h = data["hourly"]
        return {
            "temperature":  h["temperature_2m"][hour],
            "humidity":     h["relative_humidity_2m"][hour],
            "wind_speed":   h["wind_speed_10m"][hour],
            "weather_code": h["weather_code"][hour],
            "weather_desc": WEATHER_CODE_MAP.get(h["weather_code"][hour], "알 수 없음"),
        }
    except Exception as e:
        log(f"  날씨 API 오류: {e}")
        return None

def step4_weather(conn):
    log("\n[STEP 4] 새 경기 날씨 수집")
    rows = conn.execute("""
        SELECT mps.event_id, e.date_ts, e.venue_lat, e.venue_lon, e.venue_name
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        WHERE mps.team_id=? AND mps.match_date IS NULL
          AND e.date_ts IS NOT NULL AND e.venue_lat IS NOT NULL
        GROUP BY mps.event_id
        ORDER BY e.date_ts
    """, (TEAM_ID,)).fetchall()
    log(f"  날씨 수집 대상: {len(rows)}경기")
    for eid, date_ts, lat, lon, venue_name in rows:
        dt = datetime.fromtimestamp(date_ts, tz=KST)
        w = fetch_weather(dt.strftime("%Y-%m-%d"), dt.hour, lat, lon)
        if w:
            conn.execute("""
                UPDATE match_player_stats
                SET match_date=?, temperature=?, humidity=?, wind_speed=?, weather_code=?, weather_desc=?
                WHERE event_id=? AND team_id=?
            """, (dt.strftime("%Y-%m-%d %H:%M"), w["temperature"], w["humidity"],
                  w["wind_speed"], w["weather_code"], w["weather_desc"], eid, TEAM_ID))
            conn.commit()
            log(f"  event {eid} | {venue_name} | {w['temperature']}C | {w['weather_desc']}")
        time.sleep(0.5)

# ── 메인 ────────────────────────────────────────────────
async def main():
    conn = sqlite3.connect(DB_PATH)

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

        new_event_ids = await step1_match_stats(page, conn)
        await step2_heatmap(page, conn, new_event_ids)
        await step3_venues(page, conn, new_event_ids)

        await browser.close()

    step4_weather(conn)
    conn.close()

    log("\n전체 업데이트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
