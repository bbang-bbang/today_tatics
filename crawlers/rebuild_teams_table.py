#!/usr/bin/env python3
"""
P1: teams 테이블 재구축
- events 테이블에서 (team_id, latest_english_name, primary_tournament_id) 추출 (102팀)
- data/kleague_players_2026.json에서 한글 short_name 매핑 (29 K리그 팀)
- INSERT OR REPLACE

main.py가 현재 teams 테이블을 사용하지 않으므로 화면 영향 0이지만,
SQL JOIN 인프라 정합성 확보 (P4 분석가 관점 데이터 신뢰도).
"""

import json
import sqlite3

DB_PATH = "players.db"

# events의 영문 team name → kleague slug 매핑 (수동 정의: 가장 신뢰성 있는 방법)
EN_TO_SLUG = {
    "Ulsan HD FC": "ulsan", "Ulsan HD": "ulsan",
    "Pohang Steelers": "pohang",
    "Jeju United": "jeju", "Jeju SK FC": "jeju",
    "Jeonbuk Hyundai Motors": "jeonbuk",
    "FC Seoul": "fcseoul",
    "Daejeon Hana Citizen": "daejeon",
    "Incheon United": "incheon",
    "Gangwon FC": "gangwon",
    "Gwangju FC": "gwangju",
    "Bucheon FC 1995": "bucheon",
    "FC Anyang": "anyang",
    "Gimcheon Sangmu FC": "gimcheon", "Gimcheon Sangmu": "gimcheon",
    "Suwon Samsung Bluewings": "suwon",
    "Busan I Park": "busan", "Busan IPark": "busan",
    "Jeonnam Dragons": "jeonnam",
    "Seongnam FC": "seongnam",
    "Daegu FC": "daegu",
    "Gyeongnam FC": "gyeongnam",
    "Suwon FC": "suwon_fc",
    "Seoul E-Land FC": "seouland", "Seoul E-Land": "seouland",
    "Ansan Greeners FC": "ansan", "Ansan Greeners": "ansan",
    "Chungnam Asan FC": "asan",
    "Gimpo FC": "gimpo",
    "Chungbuk Cheongju FC": "cheongju", "Cheongju FC": "cheongju",
    "Cheonan City FC": "cheonan", "Cheonan FC": "cheonan",
    "Hwaseong FC": "hwaseong",
    "Paju Citizen FC": "paju", "Paju FC": "paju", "Paju Citizen": "paju",
    "Gimhae City FC": "gimhae", "Gimhae FC": "gimhae",
    "Yongin City FC": "yongin", "Yongin FC": "yongin",
}

# tournament_id → league 라벨 (우선순위 설정용)
TOURNAMENT_LEAGUE = {
    410: "K리그1",
    777: "K리그2",
    10268: "K3리그",
    463: "AFC",
    242: "FA컵",
    308: "국제대회",
    453: "U20",
    357: "국제친선",  # FIFA 클럽월드컵/친선
    2293: "J3리그",
    11669: "외국리그",  # 브라질
    18641: "외국리그",  # MLS Next Pro
    495: "외국리그",   # MLS/USL
}

# 같은 team_id가 여러 tournament에 출전 시 우선순위 (한국 K리그 우선)
TID_PRIORITY = [410, 777, 10268, 463, 242, 308, 453]


def main():
    conn = sqlite3.connect(DB_PATH)

    # 1. kleague 마스터 로드 (slug → 한글, portal_id)
    with open("data/kleague_players_2026.json", "r", encoding="utf-8") as f:
        kleague = json.load(f)
    slug_to_kr = {slug: v.get("team_name") for slug, v in kleague.items()}

    # 2. events에서 팀 ID 목록
    team_ids = [r[0] for r in conn.execute("""
        SELECT DISTINCT t_id FROM (
            SELECT home_team_id t_id FROM events WHERE home_team_id IS NOT NULL
            UNION
            SELECT away_team_id FROM events WHERE away_team_id IS NOT NULL
        )
    """).fetchall()]

    print(f"events 추출: {len(team_ids)}팀")

    inserted, matched_kr, season_id = 0, 0, 88837  # season_id는 기존 수원 행 값 재사용
    for t_id in team_ids:
        # 가장 최근 경기의 (영문명, tournament_id)
        latest = conn.execute("""
            SELECT name, tid FROM (
                SELECT home_team_id t_id, home_team_name name, tournament_id tid, date_ts FROM events
                UNION ALL
                SELECT away_team_id, away_team_name, tournament_id, date_ts FROM events
            )
            WHERE t_id=? ORDER BY date_ts DESC LIMIT 1
        """, (t_id,)).fetchone()
        if not latest:
            continue
        en_name, primary_tid = latest

        # 단, 가장 최근 경기가 컵/AFC/대표팀 등 일회성이면 league 라벨이 왜곡됨.
        # 한국 K1/K2/K3 출전 이력 있으면 그 중 가장 최근 K리그를 우선 적용.
        kleague_recent = conn.execute("""
            SELECT tid FROM (
                SELECT home_team_id t_id, tournament_id tid, date_ts FROM events WHERE tournament_id IN (410,777,10268)
                UNION ALL
                SELECT away_team_id, tournament_id, date_ts FROM events WHERE tournament_id IN (410,777,10268)
            )
            WHERE t_id=? ORDER BY date_ts DESC LIMIT 1
        """, (t_id,)).fetchone()
        if kleague_recent:
            primary_tid = kleague_recent[0]

        league = TOURNAMENT_LEAGUE.get(primary_tid, "기타")

        # 한글 short_name 매칭
        slug = EN_TO_SLUG.get(en_name)
        short_name = slug_to_kr.get(slug) if slug else None
        if short_name:
            matched_kr += 1

        conn.execute("""
            INSERT OR REPLACE INTO teams (id, name, short_name, league, tournament_id, season_id)
            VALUES (?,?,?,?,?,?)
        """, (t_id, en_name, short_name, league, primary_tid, season_id))
        inserted += 1

    conn.commit()
    print(f"INSERT OR REPLACE: {inserted}팀 / 한글 매칭: {matched_kr}/29 (목표)")

    # 3. 검증: events.home_team_id가 teams.id에 모두 있는가
    orphan = conn.execute("""
        SELECT COUNT(*) FROM events
        WHERE home_team_id IS NOT NULL AND home_team_id NOT IN (SELECT id FROM teams)
           OR away_team_id IS NOT NULL AND away_team_id NOT IN (SELECT id FROM teams)
    """).fetchone()[0]
    print(f"events↔teams orphan: {orphan} (목표 0)")

    # 4. league 분포
    print("\n=== league 분포 ===")
    for r in conn.execute("SELECT league, COUNT(*) FROM teams GROUP BY league ORDER BY 2 DESC").fetchall():
        print(f"  {r[0]:12} {r[1]}팀")

    # 5. K리그 미매칭 (short_name NULL 중 K1/K2/K3) 확인
    print("\n=== short_name 미매칭 K리그 팀 (수동 매핑 누락 추적) ===")
    miss = conn.execute("""
        SELECT id, name, league FROM teams
        WHERE short_name IS NULL AND league IN ('K리그1','K리그2','K3리그')
        ORDER BY league, name
    """).fetchall()
    if miss:
        for r in miss:
            print(f"  [{r[2]}] id={r[0]} {r[1]}")
    else:
        print("  없음 ✓")

    conn.close()
    print("\n완료.")


if __name__ == "__main__":
    main()
