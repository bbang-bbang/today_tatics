#!/usr/bin/env python3
"""
kleague_players_2026.json 의 한글 이름을 players 테이블에 채운다.
매칭 기준: sofascore_id(team) + shirt_number
"""
import json, sqlite3, sys, os

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "players.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "kleague_players_2026.json")

# ── TEAMS 매핑 (id → sofascore_id) ──────────────────────────────
TEAMS = [
    {"id": "ulsan",    "sofascore_id": 7653},
    {"id": "pohang",   "sofascore_id": 7650},
    {"id": "jeju",     "sofascore_id": 7649},
    {"id": "jeonbuk",  "sofascore_id": 6908},
    {"id": "fcseoul",  "sofascore_id": 7646},
    {"id": "daejeon",  "sofascore_id": 7645},
    {"id": "incheon",  "sofascore_id": 7648},
    {"id": "gangwon",  "sofascore_id": 34220},
    {"id": "gwangju",  "sofascore_id": 48912},
    {"id": "bucheon",  "sofascore_id": 92539},
    {"id": "anyang",   "sofascore_id": 32675},
    {"id": "gimcheon", "sofascore_id": 7647},
    {"id": "suwon",    "sofascore_id": 7652},
    {"id": "busan",    "sofascore_id": 7642},
    {"id": "jeonnam",  "sofascore_id": 7643},
    {"id": "seongnam", "sofascore_id": 7651},
    {"id": "daegu",    "sofascore_id": 7644},
    {"id": "gyeongnam","sofascore_id": 7641},
    {"id": "suwon_fc", "sofascore_id": 41261},
    {"id": "seouland", "sofascore_id": 189422},
    {"id": "ansan",    "sofascore_id": 248375},
    {"id": "asan",     "sofascore_id": 339827},
    {"id": "gimpo",    "sofascore_id": 195172},
    {"id": "cheongju", "sofascore_id": 314293},
    {"id": "cheonan",  "sofascore_id": 41263},
    {"id": "hwaseong", "sofascore_id": 195174},
    {"id": "paju",     "sofascore_id": 314294},
    {"id": "gimhae",   "sofascore_id": 41260},
    {"id": "yongin",   "sofascore_id": 41266},
]

ss_id_map = {t["id"]: t["sofascore_id"] for t in TEAMS}

with open(JSON_PATH, encoding="utf-8") as f:
    all_players = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

total_inserted = 0
total_updated  = 0

for team_slug, tdata in all_players.items():
    ss_id = ss_id_map.get(team_slug)
    if not ss_id:
        print(f"[SKIP] {team_slug} → sofascore_id 없음")
        continue

    players_json = tdata.get("players", [])
    # number → name_ko 매핑
    num_to_ko = {p["number"]: p["name"] for p in players_json if p.get("number") and p.get("name")}

    # match_player_stats에서 해당 팀 선수 목록
    cur.execute("""
        SELECT DISTINCT player_id, player_name, shirt_number
        FROM match_player_stats
        WHERE team_id = ?
    """, (ss_id,))
    mps_players = cur.fetchall()

    inserted = updated = 0
    for pid, pname, shirt_num in mps_players:
        name_ko = num_to_ko.get(shirt_num)

        # players 테이블에 이미 있는지 확인
        cur.execute("SELECT id, name_ko FROM players WHERE id = ?", (pid,))
        existing = cur.fetchone()

        if existing is None:
            # 새로 삽입
            cur.execute("""
                INSERT INTO players (id, team_id, name, shirt_number, name_ko)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, ss_id, pname, shirt_num, name_ko))
            inserted += 1
        elif name_ko and existing[1] != name_ko:
            # name_ko 업데이트
            cur.execute("UPDATE players SET name_ko = ? WHERE id = ?", (name_ko, pid))
            updated += 1

    conn.commit()
    team_name = tdata.get("team_name", team_slug)
    matched = sum(1 for _, _, sn in mps_players if num_to_ko.get(sn))
    print(f"[{team_name}] 선수 {len(mps_players)}명, 한글매칭 {matched}명, 신규 {inserted}건, 업데이트 {updated}건")
    total_inserted += inserted
    total_updated  += updated

print(f"\n완료: 총 신규 {total_inserted}건, 업데이트 {total_updated}건")
conn.close()
