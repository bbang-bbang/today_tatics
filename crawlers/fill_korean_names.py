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
    # number → 풀 메타 매핑 (name_ko, height, weight, dob, position)
    def parse_dob(s):
        # "2007/01/24" → ts로 저장 (기존 dob 컬럼은 TEXT 형식이라 그대로)
        return s if s else None
    num_to_meta = {
        p["number"]: {
            "name_ko": p.get("name"),
            "height":  p.get("height"),
            "weight":  p.get("weight"),
            "dob":     parse_dob(p.get("dob")),
            "position":p.get("position"),
        }
        for p in players_json if p.get("number") and p.get("name")
    }

    # match_player_stats에서 해당 팀 선수 목록
    cur.execute("""
        SELECT DISTINCT player_id, player_name, shirt_number
        FROM match_player_stats
        WHERE team_id = ?
    """, (ss_id,))
    mps_players = cur.fetchall()

    inserted = updated_ko = updated_phys = 0
    for pid, pname, shirt_num in mps_players:
        meta = num_to_meta.get(shirt_num)
        if not meta:
            continue
        name_ko = meta["name_ko"]
        height  = meta["height"]
        weight  = meta["weight"]
        dob     = meta["dob"]

        # players 테이블에 이미 있는지 확인
        cur.execute("SELECT id, name_ko, height, weight, dob FROM players WHERE id = ?", (pid,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute("""
                INSERT INTO players (id, team_id, name, shirt_number, name_ko, height, weight, dob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pid, ss_id, pname, shirt_num, name_ko, height, weight, dob))
            inserted += 1
            continue

        # COALESCE 패턴: 기존 값 비어있을 때만 채움 (덮어쓰지 않음)
        new_ko     = name_ko if (not existing[1] or existing[1] == "") else existing[1]
        new_height = height  if (not existing[2] or existing[2] == 0)  else existing[2]
        new_weight = weight  if (not existing[3] or existing[3] == 0)  else existing[3]
        new_dob    = dob     if (not existing[4])                       else existing[4]

        ko_change   = (new_ko != existing[1] and name_ko)
        phys_change = (new_height != existing[2] or new_weight != existing[3] or new_dob != existing[4])

        if ko_change or phys_change:
            cur.execute("""
                UPDATE players
                SET name_ko=?, height=?, weight=?, dob=?
                WHERE id=?
            """, (new_ko, new_height, new_weight, new_dob, pid))
            if ko_change:   updated_ko += 1
            if phys_change: updated_phys += 1

    conn.commit()
    team_name = tdata.get("team_name", team_slug)
    matched = sum(1 for _, _, sn in mps_players if num_to_meta.get(sn))
    print(f"[{team_name}] 선수 {len(mps_players)}명 매칭 {matched}명 / 신규 {inserted} / name_ko {updated_ko} / 신체정보 {updated_phys}")
    total_inserted += inserted
    total_updated  += updated_ko + updated_phys

print(f"\n완료: 총 신규 {total_inserted}건, 업데이트 {total_updated}건")
conn.close()
