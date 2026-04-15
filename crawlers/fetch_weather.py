#!/usr/bin/env python3
"""
경기별 날씨 수집기
- Open-Meteo 무료 Archive API 사용 (API 키 불필요)
- venue_lat/lon 좌표 기반으로 경기 당시 날씨 조회
- match_player_stats 테이블에 match_date, temperature, humidity, wind_speed, weather_code 컬럼 추가

사용법:
  python crawlers/fetch_weather.py              # 기본: 수원 삼성 (레거시)
  python crawlers/fetch_weather.py --league K1  # K1 전 경기
  python crawlers/fetch_weather.py --league K2  # K2 전 경기
  python crawlers/fetch_weather.py --league all # K1+K2 전 경기
"""

import argparse
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone, timedelta

DB_PATH = "players.db"
KST     = timezone(timedelta(hours=9))

LEAGUE_TID = {"K1": 410, "K2": 777}

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

def add_columns(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(match_player_stats)").fetchall()}
    for col, typedef in [
        ("match_date",    "TEXT"),
        ("temperature",   "REAL"),
        ("humidity",      "REAL"),
        ("wind_speed",    "REAL"),
        ("weather_code",  "INTEGER"),
        ("weather_desc",  "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE match_player_stats ADD COLUMN {col} {typedef}")
            log(f"컬럼 추가: {col}")
    conn.commit()

def fetch_weather(date_str, hour, lat, lon):
    """Open-Meteo Archive API 호출 → 해당 시각의 날씨 반환"""
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
        hourly = data["hourly"]
        # 시간 인덱스 찾기
        idx = hour  # hourly 데이터는 0~23시 순서
        return {
            "temperature":  hourly["temperature_2m"][idx],
            "humidity":     hourly["relative_humidity_2m"][idx],
            "wind_speed":   hourly["wind_speed_10m"][idx],
            "weather_code": hourly["weather_code"][idx],
            "weather_desc": WEATHER_CODE_MAP.get(hourly["weather_code"][idx], "알 수 없음"),
        }
    except Exception as e:
        log(f"  날씨 API 오류 ({date_str} {hour}시): {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", choices=["K1", "K2", "all"], default=None,
                        help="대상 리그 (K1/K2/all). 미지정 시 기존 기본값(수원삼성).")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    add_columns(conn)

    if args.league:
        tids = list(LEAGUE_TID.values()) if args.league == "all" else [LEAGUE_TID[args.league]]
        placeholders = ",".join("?" for _ in tids)
        rows = conn.execute(f"""
            SELECT mps.event_id, e.date_ts, e.venue_lat, e.venue_lon, e.venue_name, e.venue_city
            FROM match_player_stats mps
            JOIN events e ON mps.event_id = e.id
            WHERE e.tournament_id IN ({placeholders})
              AND mps.match_date IS NULL
              AND e.date_ts IS NOT NULL
              AND e.venue_lat IS NOT NULL
            GROUP BY mps.event_id
            ORDER BY e.date_ts
        """, tids).fetchall()
        update_team_filter = ""  # 모든 팀 row 업데이트
        update_params_extra = ()
        log(f"[{args.league}] 날씨 수집 대상: {len(rows)}경기")
    else:
        # 레거시: 수원 삼성만
        rows = conn.execute("""
            SELECT mps.event_id, e.date_ts, e.venue_lat, e.venue_lon, e.venue_name, e.venue_city
            FROM match_player_stats mps
            JOIN events e ON mps.event_id = e.id
            WHERE mps.team_id = 7652
              AND mps.match_date IS NULL
              AND e.date_ts IS NOT NULL
              AND e.venue_lat IS NOT NULL
            GROUP BY mps.event_id
            ORDER BY e.date_ts
        """).fetchall()
        update_team_filter = " AND team_id = 7652"
        update_params_extra = ()
        log(f"날씨 수집 대상 (수원 삼성): {len(rows)}경기")

    for i, (event_id, date_ts, lat, lon, venue_name, venue_city) in enumerate(rows):
        dt_kst = datetime.fromtimestamp(date_ts, tz=KST)
        date_str = dt_kst.strftime("%Y-%m-%d")
        hour     = dt_kst.hour

        weather = fetch_weather(date_str, hour, lat, lon)
        if weather:
            conn.execute(f"""
                UPDATE match_player_stats
                SET match_date   = ?,
                    temperature  = ?,
                    humidity     = ?,
                    wind_speed   = ?,
                    weather_code = ?,
                    weather_desc = ?
                WHERE event_id = ?{update_team_filter}
            """, (
                dt_kst.strftime("%Y-%m-%d %H:%M"),
                weather["temperature"],
                weather["humidity"],
                weather["wind_speed"],
                weather["weather_code"],
                weather["weather_desc"],
                event_id,
            ))
            conn.commit()
            if (i+1) % 20 == 0 or i == 0:
                log(f"  [{i+1}/{len(rows)}] {date_str} {hour}시 | {venue_name} | "
                    f"{weather['temperature']}°C | 바람 {weather['wind_speed']}m/s | {weather['weather_desc']}")
        else:
            log(f"  [{i+1}/{len(rows)}] {date_str} 날씨 수집 실패 ({venue_name})")

        time.sleep(0.5)

    conn.close()
    log("\n완료!")

if __name__ == "__main__":
    main()
