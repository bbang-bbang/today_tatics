#!/usr/bin/env python3
"""
경기별 경기장 정보 수집기
- SofaScore homeTeam.venue 에서 경기장명, 도시, 좌표 추출
- 좌표 이상 시 lat/lon 교정 또는 Nominatim 지오코딩으로 보완
- events 테이블에 venue_name, venue_city, venue_lat, venue_lon 저장

사용법:
  python crawlers/fetch_venues.py              # 기본: K2 (수원 삼성 경기 기준)
  python crawlers/fetch_venues.py --league K1  # K1 전 경기
  python crawlers/fetch_venues.py --league K2  # K2 전 경기
  python crawlers/fetch_venues.py --league all # K1+K2 전 경기
"""

import argparse
import asyncio
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
from playwright.async_api import async_playwright

DB_PATH = "players.db"
DELAY   = 0.4

LEAGUE_TID = {"K1": 410, "K2": 777}

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

def add_columns(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    for col, typedef in [
        ("venue_name", "TEXT"),
        ("venue_city", "TEXT"),
        ("venue_lat",  "REAL"),
        ("venue_lon",  "REAL"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {typedef}")
            log(f"컬럼 추가 (events): {col}")
    conn.commit()

def is_valid_korea_coords(lat, lon):
    """한국 좌표 범위 검증: 위도 33~39, 경도 124~132"""
    return 33 <= lat <= 39 and 124 <= lon <= 132

def nominatim_geocode(stadium_name, city):
    """Nominatim(OpenStreetMap)으로 경기장 좌표 조회"""
    query = f"{stadium_name}, {city}, South Korea"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 1
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "today_tactics/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        log(f"  Nominatim 오류 ({stadium_name}): {e}")
    return None, None

async def api_fetch(page, path):
    try:
        return await page.evaluate(f"""() =>
            fetch('{path}')
            .then(r => r.ok ? r.json() : null)
            .catch(() => null)
        """)
    except Exception:
        return None

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", choices=["K1", "K2", "all"], default=None,
                        help="대상 리그 (K1/K2/all). 지정 시 해당 리그 전 경기. 미지정 시 기존 기본값(수원삼성).")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    add_columns(conn)

    if args.league:
        tids = list(LEAGUE_TID.values()) if args.league == "all" else [LEAGUE_TID[args.league]]
        placeholders = ",".join("?" for _ in tids)
        rows = conn.execute(f"""
            SELECT DISTINCT id FROM events
            WHERE tournament_id IN ({placeholders})
              AND venue_lat IS NULL
              AND home_score IS NOT NULL
            ORDER BY date_ts
        """, tids).fetchall()
        log(f"[{args.league}] 경기장 수집 대상 (venue_lat NULL): {len(rows)}경기")
        session_url = "https://www.sofascore.com/tournament/football/south-korea/k-league-1/410" \
            if args.league == "K1" else "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777"
    else:
        # 레거시: 수원 삼성 경기만
        rows = conn.execute("""
            SELECT DISTINCT e.id
            FROM events e
            JOIN match_player_stats mps ON e.id = mps.event_id
            WHERE mps.team_id = 7652
              AND e.venue_lat IS NULL
            ORDER BY e.date_ts
        """).fetchall()
        log(f"경기장 수집 대상 (수원 삼성): {len(rows)}경기")
        session_url = "https://www.sofascore.com/tournament/football/south-korea/k-league-2/777"

    event_ids = [r[0] for r in rows]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            extra_http_headers={"Referer": "https://www.sofascore.com/"}
        )
        page = await ctx.new_page()
        await page.goto(session_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        log("세션 준비 완료")

        for i, eid in enumerate(event_ids):
            data = await api_fetch(page, f"/api/v1/event/{eid}")
            if not data:
                log(f"  [{i+1}/{len(event_ids)}] event {eid} 응답 없음")
                await asyncio.sleep(DELAY)
                continue

            event     = data.get("event", {})
            home_team = event.get("homeTeam", {})
            venue     = home_team.get("venue", {})

            v_name = venue.get("name") or venue.get("stadium", {}).get("name")
            v_city = venue.get("city", {}).get("name", "")
            coords = venue.get("venueCoordinates", {})
            raw_lat = coords.get("latitude")
            raw_lon = coords.get("longitude")

            lat, lon = None, None
            if raw_lat and raw_lon:
                if is_valid_korea_coords(raw_lat, raw_lon):
                    lat, lon = raw_lat, raw_lon
                elif is_valid_korea_coords(raw_lon, raw_lat):
                    # lat/lon 뒤집힌 경우 교정
                    lat, lon = raw_lon, raw_lat
                    log(f"  좌표 교정 ({v_name}): {raw_lat},{raw_lon} → {lat},{lon}")

            # 좌표 없으면 Nominatim
            if (lat is None or lon is None) and v_name:
                lat, lon = nominatim_geocode(v_name, v_city)
                time.sleep(1.1)  # Nominatim 1초 제한
                if lat:
                    log(f"  Nominatim 지오코딩 ({v_name}): {lat},{lon}")

            conn.execute("""
                UPDATE events
                SET venue_name=?, venue_city=?, venue_lat=?, venue_lon=?
                WHERE id=?
            """, (v_name, v_city, lat, lon, eid))
            conn.commit()

            log(f"  [{i+1}/{len(event_ids)}] event {eid} | {v_name} ({v_city}) | {lat},{lon}")
            await asyncio.sleep(DELAY)

        await browser.close()
    conn.close()
    log("\n경기장 수집 완료!")

if __name__ == "__main__":
    asyncio.run(main())
