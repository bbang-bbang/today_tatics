import json
import os
import uuid
import sqlite3
import urllib.request
from datetime import datetime

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SAVES_DIR  = os.path.join(BASE_DIR, "saves")
SQUADS_DIR = os.path.join(BASE_DIR, "squads")
os.makedirs(SAVES_DIR, exist_ok=True)
os.makedirs(SQUADS_DIR, exist_ok=True)

def _init_default_squads():
    """kleague_players_2026.json 을 읽어 팀별 기본 스쿼드 파일을 생성한다."""
    players_file = os.path.join(BASE_DIR, "data", "kleague_players_2026.json")
    if not os.path.exists(players_file):
        return
    with open(players_file, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    now = datetime.now().isoformat()
    for team_id, tdata in all_data.items():
        fpath = os.path.join(SQUADS_DIR, f"default_{team_id}.json")
        if os.path.exists(fpath):       # 이미 있으면 덮어쓰지 않음
            continue
        players = [{"number": p["number"], "name": p["name"], "position": p.get("position",""), "height": p.get("height",0), "weight": p.get("weight",0), "dob": p.get("dob","")} for p in tdata.get("players", [])]
        data = {
            "id": f"default_{team_id}",
            "teamId": team_id,
            "name": f"2026 시즌 ({tdata.get('team_name', team_id)})",
            "players": players,
            "createdAt": now,
            "updatedAt": now,
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

_init_default_squads()

# ── K리그 2026 팀 데이터 (K리그 데이터 포털 기준) ─────────
TEAMS = [
    # K1 리그 (12팀)
    # border_home: HOME 킷 아이콘 테두리색 / border_away: AWAY 킷 아이콘 테두리색
    {"id": "ulsan",    "sofascore_id": 7653,  "name": "울산 HD FC",        "short": "울산",   "league": "K1", "primary": "#1d5fa5", "secondary": "#ffffff", "accent": "#f2a900", "emblem": "emblem_K01.png", "border_home": "#fbf500", "border_away": "#6294c1"},
    {"id": "pohang",   "sofascore_id": 7650,  "name": "포항 스틸러스",      "short": "포항",   "league": "K1", "primary": "#d41123", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K03.png", "border_home": "#191e24", "border_away": "#c70027"},
    {"id": "jeju",     "sofascore_id": 7649,  "name": "제주 유나이티드",     "short": "제주",   "league": "K1", "primary": "#f47920", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K04.png", "border_home": "#121928", "border_away": "#121928"},
    {"id": "jeonbuk",  "sofascore_id": 6908,  "name": "전북 현대 모터스",    "short": "전북",   "league": "K1", "primary": "#0a4436", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K05.png", "border_home": "#50b79a", "border_away": "#214b4f"},
    {"id": "fcseoul",  "sofascore_id": 7646,  "name": "FC 서울",           "short": "서울",   "league": "K1", "primary": "#ef3744", "secondary": "#e8e7ef", "accent": "#ffd700", "emblem": "emblem_K09.png", "border_home": "#161516", "border_away": "#1f2125"},
    {"id": "daejeon",  "sofascore_id": 7645,  "name": "대전 하나 시티즌",    "short": "대전",   "league": "K1", "primary": "#059a86", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K10.png", "border_home": "#771e34", "border_away": "#771e34"},
    {"id": "incheon",  "sofascore_id": 7648,  "name": "인천 유나이티드",     "short": "인천",   "league": "K1", "primary": "#01a0fc", "secondary": "#bac6d4", "accent": "#ffffff", "emblem": "emblem_K18.png", "border_home": "#1f2521", "border_away": "#52b3f7"},
    {"id": "gangwon",  "sofascore_id": 34220, "name": "강원 FC",           "short": "강원",   "league": "K1", "primary": "#f55947", "secondary": "#e4e3f3", "accent": "#f47920", "emblem": "emblem_K21.png", "border_home": "#191e24", "border_away": "#191e24"},
    {"id": "gwangju",  "sofascore_id": 48912, "name": "광주 FC",           "short": "광주",   "league": "K1", "primary": "#f3ad02", "secondary": "#e4e3ed", "accent": "#000000", "emblem": "emblem_K22.png", "border_home": "#121621", "border_away": "#0f1b2f"},
    {"id": "bucheon",  "sofascore_id": 92539, "name": "부천 FC 1995",      "short": "부천",   "league": "K1", "primary": "#8e272b", "secondary": "#e1d8db", "accent": "#ffffff", "emblem": "emblem_K26.png", "border_home": "#170f0c", "border_away": "##a31822"},
    {"id": "anyang",   "sofascore_id": 32675, "name": "FC 안양",           "short": "안양",   "league": "K1", "primary": "#501b85", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K27.png", "border_home": "#ffffff", "border_away": "#501b85"},
    {"id": "gimcheon", "sofascore_id": 7647,  "name": "김천 상무 FC",       "short": "김천",   "league": "K1", "primary": "#df242b", "secondary": "#eeeeee", "accent": "#ffffff", "emblem": "emblem_K35.png", "border_home": "#1d1e2e", "border_away": "#262d3d"},
    # K2 리그 (17팀)
    {"id": "suwon",    "sofascore_id": 7652,  "name": "수원 삼성 블루윙즈",  "short": "수원",   "league": "K2", "primary": "#2553a5", "secondary": "#e7e6ec", "accent": "#c8102e", "emblem": "emblem_K02.png", "border_home": "#253052", "border_away": "#1f4183"},
    {"id": "busan",    "sofascore_id": 7642,  "name": "부산 아이파크",      "short": "부산",   "league": "K2", "primary": "#b4050f", "secondary": "#b7c6ca", "accent": "#ffffff", "emblem": "emblem_K06.png", "border_home": "#120d11", "border_away": "#ffffff"},
    {"id": "jeonnam",  "sofascore_id": 7643,  "name": "전남 드래곤즈",      "short": "전남",   "league": "K2", "primary": "#fbea09", "secondary": "#f0f0f2", "accent": "#000000", "emblem": "emblem_K07.png", "border_home": "#000000", "border_away": "#000000"},
    {"id": "seongnam", "sofascore_id": 7651,  "name": "성남 FC",           "short": "성남",   "league": "K2", "primary": "#0e131b", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K08.png", "border_home": "#ffffff", "border_away": "#1a222d"},
    {"id": "daegu",    "sofascore_id": 7644,  "name": "대구 FC",           "short": "대구",   "league": "K2", "primary": "#86c5e8", "secondary": "#e2e5ea", "accent": "#ffffff", "emblem": "emblem_K17.png", "border_home": "#e2e5ea", "border_away": "#86c5e8"},
    {"id": "gyeongnam","sofascore_id": 22020,  "name": "경남 FC",           "short": "경남",   "league": "K2", "primary": "#ac101b", "secondary": "#d9d9d9", "accent": "#ffffff", "emblem": "emblem_K20.png", "border_home": "#121211", "border_away": "#121211"},
    {"id": "suwon_fc", "sofascore_id": 41261, "name": "수원 FC",           "short": "수원FC", "league": "K2", "primary": "#07306a", "secondary": "#cac3c3", "accent": "#ffffff", "emblem": "emblem_K29.png", "border_home": "#c9232e", "border_away": "#0b3972"},
    {"id": "seouland", "sofascore_id": 189422, "name": "서울 이랜드 FC",     "short": "이랜드", "league": "K2", "primary": "#030a1b", "secondary": "#d7dddd", "accent": "#1e3a8a", "emblem": "emblem_K31.png", "border_home": "#051025", "border_away": "#051025"},
    {"id": "ansan",    "sofascore_id": 248375, "name": "안산 그리너스 FC",    "short": "안산",   "league": "K2", "primary": "#0087a7", "secondary": "#eaedf4", "accent": "#ffd700", "emblem": "emblem_K32.png", "border_home": "#272c3d", "border_away": "#00677f"},
    {"id": "asan",     "sofascore_id": 339827, "name": "충남 아산 FC",       "short": "아산",   "league": "K2", "primary": "#12122c", "secondary": "#dfdfdf", "accent": "#e30613", "emblem": "emblem_K34.png", "border_home": "#d3a84c", "border_away": "#d3a84c"},
    {"id": "gimpo",    "sofascore_id": 195172, "name": "김포 FC",           "short": "김포",   "league": "K2", "primary": "#78bc36", "secondary": "#ebebeb", "accent": "#ffffff", "emblem": "emblem_K36.png", "border_home": "#0f2716", "border_away": "#0f2716"},
    {"id": "cheongju", "sofascore_id": 314293, "name": "충북 청주 FC",       "short": "청주",   "league": "K2", "primary": "#0d1026", "secondary": "#f0f0f0", "accent": "#ffffff", "emblem": "emblem_K37.png", "border_home": "#ae1d25", "border_away": "#0d1026"},
    {"id": "cheonan",  "sofascore_id": 41263,  "name": "천안 시티 FC",       "short": "천안",   "league": "K2", "primary": "#3e8fb3", "secondary": "#e2e2e2", "accent": "#e30613", "emblem": "emblem_K38.png", "border_home": "#201d1d", "border_away": "#3e8fb3"},
    {"id": "hwaseong", "sofascore_id": 195174, "name": "화성 FC",           "short": "화성",   "league": "K2", "primary": "#d45820", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K39.png", "border_home": "#fbf5f6", "border_away": "#090811"},
    {"id": "paju",     "sofascore_id": 314294, "name": "파주 시민축구단",     "short": "파주",   "league": "K2", "primary": "#042ba0", "secondary": "#f8f8f8", "accent": "#c8102e", "emblem": "emblem_K40.png", "border_home": "#d381a2", "border_away": "#d381a2"},
    {"id": "gimhae",   "sofascore_id": 41260,  "name": "김해 FC",           "short": "김해",   "league": "K2", "primary": "#ac0d0e", "secondary": "#f3f3f3", "accent": "#ffd700", "emblem": "emblem_K41.png", "border_home": "#2c2c2c", "border_away": "#bba473"},
    {"id": "yongin",   "sofascore_id": 41266,  "name": "용인 시민축구단",     "short": "용인",   "league": "K2", "primary": "#910c26", "secondary": "#dddddd", "accent": "#ffd700", "emblem": "emblem_K42.png", "border_home": "#54bfe1", "border_away": "#8c0e29"},
]


@app.route("/api/teams")
def teams():
    return jsonify(TEAMS)


PLAYER_STEP = 0.16  # 선수 간 고정 세로 간격

def compute_formation(formation_str):
    """포메이션 문자열을 파싱하여 선수 좌표(0~1 정규화)를 계산한다."""
    rows = [int(x) for x in formation_str.split("-")]
    positions = []

    # 골키퍼
    positions.append({"x": 0.05, "y": 0.5})

    num_rows = len(rows)
    for row_idx, count in enumerate(rows):
        # x: 0.12 ~ 0.44 (하프라인 직전까지, 중앙 여백 확보)
        x = 0.12 + (row_idx / max(num_rows - 1, 1)) * 0.32
        for player_idx in range(count):
            if count == 1:
                y = 0.5
            else:
                # 최대 5명 기준 전체 높이 0.8 사용
                total_h = min((count - 1) * PLAYER_STEP, 0.80)
                step = total_h / (count - 1)
                start = 0.5 - total_h / 2
                y = start + player_idx * step
            positions.append({"x": round(x, 3), "y": round(y, 3)})

    return positions


POSITION_LABELS = {
    "4-4-2": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"],
    "4-3-3": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"],
    "3-5-2": ["GK", "CB", "CB", "CB", "LM", "CM", "CDM", "CM", "RM", "ST", "ST"],
    "4-2-3-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LW", "AM", "RW", "ST"],
    "4-1-4-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "LM", "CM", "CM", "RM", "ST"],
    "3-4-3": ["GK", "CB", "CB", "CB", "LM", "CM", "CM", "RM", "LW", "ST", "RW"],
    "5-3-2": ["GK", "LWB", "CB", "CB", "CB", "RWB", "CM", "CM", "CM", "ST", "ST"],
    "5-4-1": ["GK", "LWB", "CB", "CB", "CB", "RWB", "LM", "CM", "CM", "RM", "ST"],
}

def mirror_labels(labels):
    result = []
    for label in labels:
        if label.startswith("L"):
            result.append("R" + label[1:])
        elif label.startswith("R"):
            result.append("L" + label[1:])
        else:
            result.append(label)
    return result


FORMATIONS = {}
for name in POSITION_LABELS:
    team_a = compute_formation(name)
    team_b = [{"x": round(1.0 - p["x"], 3), "y": p["y"]} for p in compute_formation(name)]
    FORMATIONS[name] = {
        "teamA": team_a,
        "teamB": team_b,
        "labelsA": POSITION_LABELS[name],
        "labelsB": mirror_labels(POSITION_LABELS[name]),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/formations")
def formations():
    return jsonify(FORMATIONS)


@app.route("/api/saves", methods=["GET"])
def list_saves():
    saves = []
    for fname in os.listdir(SAVES_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SAVES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        saves.append({
            "id": data["id"],
            "name": data["name"],
            "formation": data.get("formation", ""),
            "createdAt": data.get("createdAt", ""),
            "updatedAt": data.get("updatedAt", ""),
        })
    saves.sort(key=lambda s: s["updatedAt"], reverse=True)
    return jsonify(saves)


@app.route("/api/saves", methods=["POST"])
def create_save():
    body = request.get_json()
    save_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    data = {
        "id": save_id,
        "name": body.get("name", "Untitled"),
        "formation": body.get("formation", ""),
        "players": body.get("players", []),
        "lines": body.get("lines", body.get("arrows", [])),
        "teamAId": body.get("teamAId"),
        "teamBId": body.get("teamBId"),
        "createdAt": now,
        "updatedAt": now,
    }
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(data), 201


@app.route("/api/saves/<save_id>", methods=["GET"])
def get_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/saves/<save_id>", methods=["PUT"])
def update_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        existing = json.load(f)
    body = request.get_json()
    existing["name"] = body.get("name", existing["name"])
    existing["formation"] = body.get("formation", existing["formation"])
    existing["players"] = body.get("players", existing["players"])
    existing["lines"] = body.get("lines", existing.get("lines", existing.get("arrows", [])))
    existing["teamAId"] = body.get("teamAId", existing.get("teamAId"))
    existing["teamBId"] = body.get("teamBId", existing.get("teamBId"))
    existing["updatedAt"] = datetime.now().isoformat()
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return jsonify(existing)


@app.route("/api/saves/<save_id>", methods=["DELETE"])
def delete_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    os.remove(fpath)
    return jsonify({"ok": True})


# ── 스쿼드(선수 명단) API ──────────────────────────────────
@app.route("/api/squads", methods=["GET"])
def list_squads():
    team_id = request.args.get("teamId")
    squads = []
    for fname in os.listdir(SQUADS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SQUADS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if team_id and data.get("teamId") != team_id:
            continue
        squads.append({
            "id": data["id"],
            "teamId": data["teamId"],
            "name": data["name"],
            "playerCount": len(data.get("players", [])),
            "updatedAt": data.get("updatedAt", ""),
        })
    squads.sort(key=lambda s: s["updatedAt"], reverse=True)
    return jsonify(squads)


@app.route("/api/squads", methods=["POST"])
def create_squad():
    body = request.get_json()
    squad_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    data = {
        "id": squad_id,
        "teamId": body.get("teamId", ""),
        "name": body.get("name", "Untitled"),
        "players": body.get("players", []),
        "createdAt": now,
        "updatedAt": now,
    }
    fpath = os.path.join(SQUADS_DIR, f"{squad_id}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(data), 201


@app.route("/api/squads/<squad_id>", methods=["GET"])
def get_squad(squad_id):
    # 직접 파일명으로 시도
    fpath = os.path.join(SQUADS_DIR, f"{squad_id}.json")
    if not os.path.exists(fpath):
        # 내부 id로 스캔
        fpath = None
        for fname in os.listdir(SQUADS_DIR):
            if not fname.endswith(".json"):
                continue
            candidate = os.path.join(SQUADS_DIR, fname)
            with open(candidate, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") == squad_id:
                fpath = candidate
                break
    if not fpath:
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/squads/<squad_id>", methods=["DELETE"])
def delete_squad(squad_id):
    # 직접 파일명으로 시도
    fpath = os.path.join(SQUADS_DIR, f"{squad_id}.json")
    if not os.path.exists(fpath):
        # 내부 id로 스캔
        fpath = None
        for fname in os.listdir(SQUADS_DIR):
            if not fname.endswith(".json"):
                continue
            candidate = os.path.join(SQUADS_DIR, fname)
            with open(candidate, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") == squad_id:
                fpath = candidate
                break
    if not fpath:
        return jsonify({"error": "Not found"}), 404
    os.remove(fpath)
    return jsonify({"ok": True})


# ── 경기 결과 / H2H / 팀 스탯 API ──────────────────────
RESULTS_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_results_2026.json")
H2H_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_h2h.json")
STATS_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_team_stats.json")

@app.route("/api/results")
def get_results():
    team_id = request.args.get("teamId")
    if not os.path.exists(RESULTS_FILE):
        return jsonify([])
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        all_results = json.load(f)
    if team_id:
        return jsonify(all_results.get(team_id, []))
    return jsonify(all_results)

@app.route("/api/h2h")
def get_h2h():
    team_a = request.args.get("teamA")
    team_b = request.args.get("teamB")
    if not team_a or not team_b:
        return jsonify({"error": "teamA and teamB required"}), 400
    if not os.path.exists(H2H_FILE):
        return jsonify({"w": 0, "d": 0, "l": 0, "total": 0})
    with open(H2H_FILE, "r", encoding="utf-8") as f:
        h2h = json.load(f)
    key = f"{team_a}|{team_b}"
    return jsonify(h2h.get(key, {"w": 0, "d": 0, "l": 0, "total": 0}))

@app.route("/api/h2h-matches")
def get_h2h_matches():
    """두 팀 간 최근 맞대결 경기 목록 + 득점 선수 (events DB 기반)"""
    team_a = request.args.get("teamA")
    team_b = request.args.get("teamB")
    if not team_a or not team_b:
        return jsonify([])
    info_a = next((t for t in TEAMS if t["id"] == team_a), None)
    info_b = next((t for t in TEAMS if t["id"] == team_b), None)
    if not info_a or not info_b:
        return jsonify([])
    ss_a, ss_b = info_a["sofascore_id"], info_b["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify([])

    from datetime import datetime, timezone
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date_ts, home_team_id, away_team_id, home_team_name, away_team_name,
               home_score, away_score
        FROM events
        WHERE tournament_id = 777
          AND home_score IS NOT NULL
          AND ((home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?))
        ORDER BY date_ts DESC
        LIMIT 10
    """, (ss_a, ss_b, ss_b, ss_a))
    rows = cur.fetchall()

    result = []
    for event_id, ts, home_id, away_id, home_name, away_name, hs, as_ in rows:
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        is_home_a = (home_id == ss_a)
        result_a = "W" if (is_home_a and hs > as_) or (not is_home_a and as_ > hs) \
                   else ("D" if hs == as_ else "L")

        # 득점 선수 조회 (자책골 제외: 홈팀 득점자만 홈에, 원정팀 득점자만 원정에)
        cur.execute("""
            SELECT mps.team_id,
                   COALESCE(p.name_ko, mps.player_name) as name,
                   SUM(mps.goals) as g
            FROM match_player_stats mps
            LEFT JOIN players p ON mps.player_id = p.id
            WHERE mps.event_id = ? AND mps.goals > 0
            GROUP BY mps.player_id, mps.team_id
            ORDER BY mps.team_id, g DESC
        """, (event_id,))
        scorer_rows = cur.fetchall()

        # 홈팀 득점자는 home_id와 team_id가 일치하는 선수만
        # 원정팀 득점자는 away_id(= not home_id)와 team_id가 일치하는 선수만
        scorers_home = [{"name": r[1], "goals": r[2]} for r in scorer_rows if r[0] == home_id]
        scorers_away = [{"name": r[1], "goals": r[2]} for r in scorer_rows if r[0] == away_id]

        result.append({
            "date": date_str,
            "home": home_name,
            "away": away_name,
            "home_score": hs,
            "away_score": as_,
            "result_a": result_a,
            "is_home_a": is_home_a,
            "scorers_home": scorers_home,
            "scorers_away": scorers_away,
        })

    conn.close()
    return jsonify(result)

@app.route("/api/team-stats")
def get_team_stats():
    team_id = request.args.get("teamId")
    if not os.path.exists(STATS_FILE):
        return jsonify({})
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)
    if team_id:
        return jsonify(stats.get(team_id, {}))
    return jsonify(stats)


@app.route("/api/team-stats-by-year")
def get_team_stats_by_year():
    """연도별 홈/원정 승무패 (match_player_stats DB 기반)"""
    team_id = request.args.get("teamId")
    if not team_id:
        return jsonify({})

    # slug → sofascore_id 변환
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT strftime('%Y', datetime(e.date_ts, 'unixepoch', 'localtime')) as year,
               CASE WHEN e.home_team_id = ? THEN 1 ELSE 0 END as is_home,
               COUNT(CASE WHEN (e.home_team_id=? AND e.home_score > e.away_score)
                            OR (e.away_team_id=? AND e.away_score > e.home_score) THEN 1 END) as w,
               COUNT(CASE WHEN e.home_score = e.away_score THEN 1 END) as d,
               COUNT(CASE WHEN (e.home_team_id=? AND e.home_score < e.away_score)
                            OR (e.away_team_id=? AND e.away_score < e.home_score) THEN 1 END) as l,
               COUNT(*) as games,
               SUM(CASE WHEN e.home_team_id=? THEN e.home_score ELSE e.away_score END) as gf,
               SUM(CASE WHEN e.home_team_id=? THEN e.away_score ELSE e.home_score END) as ga
        FROM events e
        WHERE (e.home_team_id = ? OR e.away_team_id = ?)
          AND e.home_score IS NOT NULL
          AND e.tournament_id = 777
        GROUP BY year, is_home
        ORDER BY year, is_home
    """, (ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id))
    rows = cur.fetchall()
    conn.close()

    result = {}
    total = {"home": {"w": 0, "d": 0, "l": 0, "games": 0, "gf": 0, "ga": 0},
             "away": {"w": 0, "d": 0, "l": 0, "games": 0, "gf": 0, "ga": 0}}
    for year, is_home, w, d, l, games, gf, ga in rows:
        if year not in result:
            result[year] = {"home": {}, "away": {}}
        key = "home" if is_home else "away"
        result[year][key] = {"w": w, "d": d, "l": l, "games": games, "gf": gf or 0, "ga": ga or 0}
        total[key]["w"] += w
        total[key]["d"] += d
        total[key]["l"] += l
        total[key]["games"] += games
        total[key]["gf"] += gf or 0
        total[key]["ga"] += ga or 0

    result["전체"] = total
    return jsonify(result)


@app.route("/api/team-ranking")
def get_team_ranking():
    """현재 시즌(최신 연도) 리그 순위 계산"""
    team_id = request.args.get("teamId")
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 최신 연도 확인
    cur.execute("""
        SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
        FROM events WHERE tournament_id = 777
    """)
    latest_year = cur.fetchone()[0]

    # 해당 연도 전체 경기
    cur.execute("""
        SELECT home_team_id, away_team_id, home_score, away_score
        FROM events
        WHERE tournament_id = 777
          AND home_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime')) = ?
    """, (latest_year,))
    rows = cur.fetchall()
    conn.close()

    # 팀별 집계
    standings = {}
    for home_id, away_id, hs, as_ in rows:
        for tid, gf, ga, is_home in [(home_id, hs, as_, True), (away_id, as_, hs, False)]:
            if tid not in standings:
                standings[tid] = {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
            s = standings[tid]
            s["gf"] += gf
            s["ga"] += ga
            if gf > ga:
                s["w"] += 1; s["pts"] += 3
            elif gf == ga:
                s["d"] += 1; s["pts"] += 1
            else:
                s["l"] += 1

    # 정렬: 승점 → 득실차 → 득점
    sorted_teams = sorted(standings.items(),
                          key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                          reverse=True)
    rank = next((i + 1 for i, (tid, _) in enumerate(sorted_teams) if tid == ss_id), None)
    total_teams = len(sorted_teams)
    my = standings.get(ss_id, {})

    return jsonify({
        "rank": rank,
        "total": total_teams,
        "year": latest_year,
        "w": my.get("w", 0),
        "d": my.get("d", 0),
        "l": my.get("l", 0),
        "gf": my.get("gf", 0),
        "ga": my.get("ga", 0),
        "pts": my.get("pts", 0),
    })


@app.route("/api/team-top-players")
def get_team_top_players():
    """현재 시즌 팀 득점/어시스트 TOP 3"""
    team_id = request.args.get("teamId")
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 최신 연도
    cur.execute("""
        SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
        FROM events WHERE tournament_id = 777
    """)
    latest_year = cur.fetchone()[0]

    def fetch_top(stat_col, limit=3):
        cur.execute(f"""
            SELECT mps.player_id, mps.player_name,
                   COALESCE(p.name_ko, mps.player_name) as display_name,
                   SUM(mps.{stat_col}) as total
            FROM match_player_stats mps
            JOIN events e ON mps.event_id = e.id
            LEFT JOIN players p ON mps.player_id = p.id
            WHERE mps.team_id = ?
              AND e.tournament_id = 777
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) = ?
              AND mps.{stat_col} > 0
            GROUP BY mps.player_id
            ORDER BY total DESC
            LIMIT ?
        """, (ss_id, latest_year, limit))
        return [{"name": row[2], "val": row[3]} for row in cur.fetchall()]

    scorers = fetch_top("goals")
    assisters = fetch_top("assists")
    conn.close()

    return jsonify({"year": latest_year, "scorers": scorers, "assisters": assisters})


_ENG_TO_KO = {t["sofascore_id"]: t["name"] for t in TEAMS}

def _ko_name_by_ss_id(ss_id):
    """sofascore team id (int 또는 str) → 한국어 팀명"""
    try:
        return _ENG_TO_KO.get(int(ss_id)) or _ENG_TO_KO.get(ss_id)
    except (ValueError, TypeError):
        return _ENG_TO_KO.get(ss_id)


@app.route("/api/team-analytics")
def get_team_analytics():
    """팀별 상대팀 승률 / 월별 승률 / 홈어웨이 분석"""
    team_id = request.args.get("teamId")
    year    = request.args.get("year")          # optional filter
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({}), 404

    ss_id = team_info["sofascore_id"]
    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 사용 가능 연도 목록
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(date_ts,'unixepoch','localtime'))
        FROM events WHERE tournament_id=777
          AND (home_team_id=? OR away_team_id=?)
        ORDER BY 1
    """, (ss_id, ss_id))
    available_years = [r[0] for r in cur.fetchall()]

    year_clause = "AND strftime('%Y', datetime(date_ts,'unixepoch','localtime')) = ?" if year else ""
    yp = (year,) if year else ()

    # 1. 상대팀별 승률 (홈+원정 합산, 팀 ID 포함해 한글명 변환)
    cur.execute("""
        SELECT opp_id, opp_name, SUM(g) games,
               SUM(w) w, SUM(d) d, SUM(l) l,
               SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT away_team_id opp_id, away_team_name opp_name,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY away_team_id
            UNION ALL
            SELECT home_team_id opp_id, home_team_name opp_name,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY home_team_id
        )
        GROUP BY opp_id ORDER BY games DESC, w DESC
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    vs_rows = cur.fetchall()
    vs_opponents = [
        {"name": _ko_name_by_ss_id(r[0]) or r[1],
         "games": r[2], "w": r[3], "d": r[4], "l": r[5],
         "gf": r[6], "ga": r[7]}
        for r in vs_rows
    ]

    # 2. 월별 승률
    cur.execute("""
        SELECT mon, SUM(g) games, SUM(w) w, SUM(d) d, SUM(l) l, SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT) mon,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY mon
            UNION ALL
            SELECT CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT) mon,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY mon
        )
        GROUP BY mon ORDER BY mon
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    month_rows = cur.fetchall()
    by_month = [
        {"month": r[0], "games": r[1], "w": r[2], "d": r[3], "l": r[4],
         "gf": r[5], "ga": r[6]}
        for r in month_rows
    ]

    # 3. 홈/어웨이 연도별 승률
    cur.execute("""
        SELECT yr, side, SUM(g) games, SUM(w) w, SUM(d) d, SUM(l) l, SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT strftime('%Y', datetime(date_ts,'unixepoch','localtime')) yr,
                   'home' side,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY yr
            UNION ALL
            SELECT strftime('%Y', datetime(date_ts,'unixepoch','localtime')) yr,
                   'away' side,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY yr
        )
        GROUP BY yr, side ORDER BY yr, side
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    ha_rows = cur.fetchall()
    by_year_ha = {}
    for yr, side, g, w, d, l, gf, ga in ha_rows:
        if yr not in by_year_ha:
            by_year_ha[yr] = {}
        by_year_ha[yr][side] = {"games": g, "w": w, "d": d, "l": l, "gf": gf, "ga": ga}

    # 4. 날씨별 승률 (기온 / 습도 / 풍속)
    weather_sql = """
        SELECT
            e.id,
            CASE WHEN mps.team_id = ? THEN
                CASE WHEN (mps.is_home=1 AND e.home_score > e.away_score)
                          OR (mps.is_home=0 AND e.away_score > e.home_score) THEN 'w'
                     WHEN e.home_score = e.away_score THEN 'd'
                     ELSE 'l' END
            END result,
            CASE WHEN mps.is_home=1 THEN e.home_score ELSE e.away_score END gf,
            CASE WHEN mps.is_home=1 THEN e.away_score ELSE e.home_score END ga,
            mps.temperature, mps.humidity, mps.wind_speed
        FROM events e
        JOIN match_player_stats mps ON e.id = mps.event_id
        WHERE e.tournament_id = 777
          AND mps.team_id = ?
          AND mps.temperature IS NOT NULL
          {yc_e}
        GROUP BY e.id
    """.format(yc_e="AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) = ?" if year else "")
    cur.execute(weather_sql, (ss_id, ss_id, *yp))
    w_rows = cur.fetchall()

    def bucket_weather(rows, key_fn, labels):
        buckets = {lbl: {"games":0,"w":0,"d":0,"l":0,"gf":0,"ga":0} for lbl in labels}
        for _, result, gf, ga, temp, hum, wind in rows:
            lbl = key_fn(temp, hum, wind)
            if lbl and result:
                b = buckets[lbl]
                b["games"] += 1
                b[result] += 1
                b["gf"] += gf or 0
                b["ga"] += ga or 0
        return [{"label": k, **v} for k, v in buckets.items() if v["games"] > 0]

    temp_labels  = ["영하~5도","5~15도","15~25도","25도~"]
    hum_labels   = ["건조(<40%)","보통(40~65%)","습함(65%+)"]
    wind_labels  = ["약풍(<3)","중풍(3~7)","강풍(7+)"]

    by_temp = bucket_weather(w_rows,
        lambda t,h,w: "영하~5도" if t<5 else "5~15도" if t<15 else "15~25도" if t<25 else "25도~",
        temp_labels)
    by_hum  = bucket_weather(w_rows,
        lambda t,h,w: "건조(<40%)" if h<40 else "보통(40~65%)" if h<65 else "습함(65%+)",
        hum_labels)
    by_wind = bucket_weather(w_rows,
        lambda t,h,w: "약풍(<3)" if w<3 else "중풍(3~7)" if w<7 else "강풍(7+)",
        wind_labels)

    conn.close()
    return jsonify({
        "team": team_info["name"],
        "available_years": available_years,
        "vs_opponents": vs_opponents,
        "by_month": by_month,
        "by_year_ha": by_year_ha,
        "weather": {
            "by_temp": by_temp,
            "by_hum": by_hum,
            "by_wind": by_wind,
        },
    })


@app.route("/api/match-prediction")
def get_match_prediction():
    """두 팀 간 예측 보고서: 승률·유의사항·주요 선수"""
    home_id = request.args.get("homeTeam")
    away_id = request.args.get("awayTeam")
    home_info = next((t for t in TEAMS if t["id"] == home_id), None)
    away_info = next((t for t in TEAMS if t["id"] == away_id), None)
    if not home_info or not away_info:
        return jsonify({}), 404

    hid = home_info["sofascore_id"]
    aid = away_info["sofascore_id"]
    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    import math, datetime
    now_month = datetime.datetime.now().month
    now_year  = str(datetime.datetime.now().year)

    def compute_standings(year):
        """K2 현재 순위표 계산 (최신 시즌)"""
        cur.execute("""
            SELECT home_team_id, away_team_id, home_score, away_score
            FROM events
            WHERE tournament_id=777 AND home_score IS NOT NULL AND away_score IS NOT NULL
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (year,))
        standing = {}
        for home_id, away_id, hs, as_ in cur.fetchall():
            for tid, gf, ga, is_home in [(home_id, hs, as_, True), (away_id, as_, hs, False)]:
                if tid not in standing:
                    standing[tid] = {"played": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
                s = standing[tid]
                s["played"] += 1
                s["gf"] += gf; s["ga"] += ga
                if gf > ga:
                    s["w"] += 1; s["pts"] += 3
                elif gf == ga:
                    s["d"] += 1; s["pts"] += 1
                else:
                    s["l"] += 1
        # 정렬: pts → gd → gf
        ranked = sorted(standing.items(),
                        key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                        reverse=True)
        result = {}
        for rank, (tid, s) in enumerate(ranked, 1):
            result[tid] = {**s, "rank": rank, "gd": s["gf"] - s["ga"]}
        return result

    standings = compute_standings(now_year)

    def team_stats(ss_id, side_home):
        """팀 전반 지표 계산"""
        # 전체 K2 경기 (홈+원정)
        cur.execute("""
            SELECT COUNT(*) g,
                   SUM(CASE WHEN home_score>away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=?
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (ss_id, now_year))
        hrow = cur.fetchone()
        cur.execute("""
            SELECT COUNT(*) g,
                   SUM(CASE WHEN away_score>home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=?
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (ss_id, now_year))
        arow = cur.fetchone()
        hg,hw,hd,hgf,hga = hrow
        ag,aw,ad,agf,aga = arow
        total_g = (hg or 0)+(ag or 0)
        total_w = (hw or 0)+(aw or 0)
        home_wr = hw/(hg or 1)*100
        away_wr = aw/(ag or 1)*100

        # 최근 5경기 폼
        cur.execute("""
            SELECT home_score, away_score, home_team_id FROM events
            WHERE tournament_id=777 AND (home_team_id=? OR away_team_id=?)
            ORDER BY date_ts DESC LIMIT 5
        """, (ss_id, ss_id))
        recent = cur.fetchall()
        form = []
        for hs, as_, ht in recent:
            is_home = ht == ss_id
            gf = hs if is_home else as_
            ga = as_ if is_home else hs
            form.append("W" if gf>ga else "D" if gf==ga else "L")

        # 월별 승률 — 현재 달 기준 과거 데이터
        cur.execute("""
            SELECT SUM(g), SUM(w) FROM (
                SELECT COUNT(*) g, SUM(CASE WHEN home_score>away_score THEN 1 ELSE 0 END) w
                FROM events WHERE tournament_id=777 AND home_team_id=?
                  AND CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT)=?
                UNION ALL
                SELECT COUNT(*) g, SUM(CASE WHEN away_score>home_score THEN 1 ELSE 0 END) w
                FROM events WHERE tournament_id=777 AND away_team_id=?
                  AND CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT)=?
            )
        """, (ss_id, now_month, ss_id, now_month))
        mr = cur.fetchone()
        month_wr = (mr[1] or 0)/(mr[0] or 1)*100 if (mr and mr[0]) else None

        # 홈/원정 격차
        ha_gap = home_wr - away_wr

        # 득점 top3 (현재 시즌)
        cur.execute("""
            SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
            FROM events WHERE tournament_id=777
        """)
        latest_yr = cur.fetchone()[0]
        cur.execute("""
            SELECT mps.player_id, COALESCE(p.name_ko, mps.player_name), SUM(mps.goals) g
            FROM match_player_stats mps
            JOIN events e ON mps.event_id=e.id
            LEFT JOIN players p ON mps.player_id=p.id
            WHERE mps.team_id=? AND e.tournament_id=777
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
              AND mps.goals>0
            GROUP BY mps.player_id ORDER BY g DESC LIMIT 3
        """, (ss_id, latest_yr))
        top_scorers = [{"id": r[0], "name": r[1], "goals": r[2]} for r in cur.fetchall()]

        # 유의사항 도출
        notes = []
        if ha_gap > 20:
            notes.append(f"홈에서 특히 강함 (홈승률 {home_wr:.0f}% vs 원정 {away_wr:.0f}%)")
        elif ha_gap < -10:
            notes.append(f"원정이 오히려 강함 (원정승률 {away_wr:.0f}%)")
        if month_wr is not None:
            mn = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"][now_month-1]
            if month_wr >= 55:
                notes.append(f"{mn} 강세 (역대 {mn} 승률 {month_wr:.0f}%)")
            elif month_wr <= 30:
                notes.append(f"{mn} 약세 (역대 {mn} 승률 {month_wr:.0f}%)")
        form_w = form.count("W")
        form_l = form.count("L")
        if form_w >= 4:
            notes.append("최근 5경기 상승세")
        elif form_l >= 3:
            notes.append("최근 5경기 부진")
        avg_gf = ((hgf or 0)+(agf or 0)) / (total_g or 1)
        avg_ga = ((hga or 0)+(aga or 0)) / (total_g or 1)
        if avg_gf >= 1.6:
            notes.append(f"공격적 (경기당 평균 {avg_gf:.1f}골)")
        if avg_ga >= 1.6:
            notes.append(f"수비 취약 (경기당 평균 {avg_ga:.1f}실점)")

        return {
            "total_games": total_g,
            "win_rate": total_w/(total_g or 1)*100,
            "home_wr": home_wr,
            "away_wr": away_wr,
            "form": form,
            "month_wr": month_wr,
            "notes": notes,
            "top_scorers": top_scorers,
            "avg_gf": avg_gf,
            "avg_ga": avg_ga,
            "standing": standings.get(ss_id),
        }

    # H2H 직접 전적
    cur.execute("""
        SELECT COUNT(*) g,
               SUM(CASE WHEN home_team_id=? THEN
                     CASE WHEN home_score>away_score THEN 1 ELSE 0 END
                   ELSE
                     CASE WHEN away_score>home_score THEN 1 ELSE 0 END
                   END) w,
               SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d
        FROM events WHERE tournament_id=777
          AND ((home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?))
    """, (hid, hid, aid, aid, hid))
    h2h = cur.fetchone()
    h2h_g, h2h_w, h2h_d = h2h
    h2h_l = (h2h_g or 0) - (h2h_w or 0) - (h2h_d or 0)

    home_stats = team_stats(hid, True)
    away_stats = team_stats(aid, False)

    # 승률 예측 (가중 평균)
    # H2H 승률 40% + 홈팀 홈승률 30% + 원정팀 원정승률(역) 30%
    h2h_win_rate = (h2h_w or 0) / (h2h_g or 1) * 100
    home_factor  = home_stats["home_wr"]
    away_factor  = 100 - away_stats["away_wr"]  # 홈팀 유리 관점

    if h2h_g and h2h_g >= 3:
        pred_home = h2h_win_rate * 0.4 + home_factor * 0.35 + away_factor * 0.25
    else:
        pred_home = home_factor * 0.55 + away_factor * 0.45

    # 최근 폼 보정
    home_form_bonus = (home_stats["form"].count("W") - home_stats["form"].count("L")) * 2
    away_form_bonus = (away_stats["form"].count("W") - away_stats["form"].count("L")) * 2
    pred_home = max(5, min(90, pred_home + home_form_bonus - away_form_bonus))
    pred_away = max(5, min(90, 100 - pred_home - 15))
    pred_draw = max(5, 100 - pred_home - pred_away)

    # 정규화
    total = pred_home + pred_draw + pred_away
    pred_home = round(pred_home / total * 100)
    pred_draw = round(pred_draw / total * 100)
    pred_away = 100 - pred_home - pred_draw

    conn.close()
    return jsonify({
        "home": {"id": home_id, "name": home_info["name"], **home_stats},
        "away": {"id": away_id, "name": away_info["name"], **away_stats},
        "h2h": {"games": h2h_g or 0, "home_w": h2h_w or 0, "draw": h2h_d or 0, "away_w": h2h_l},
        "prediction": {"home": pred_home, "draw": pred_draw, "away": pred_away},
    })


KLEAGUE_CODE_MAP = {
    "K01": "ulsan",  "K02": "suwon",    "K03": "pohang",  "K04": "jeju",
    "K05": "jeonbuk","K06": "busan",    "K07": "jeonnam", "K08": "seongnam",
    "K09": "fcseoul","K10": "daejeon",  "K17": "daegu",   "K18": "incheon",
    "K20": "gyeongnam","K21": "gangwon","K22": "gwangju", "K26": "bucheon",
    "K27": "anyang", "K29": "suwon_fc", "K31": "seouland","K32": "ansan",
    "K34": "asan",   "K35": "gimcheon", "K36": "gimpo",   "K37": "cheongju",
    "K38": "cheonan","K39": "hwaseong", "K40": "paju",    "K41": "gimhae",
    "K42": "yongin",
}
TEAMS_BY_ID = {t["id"]: t for t in TEAMS}

@app.route("/api/standings")
def get_standings():
    try:
        req = urllib.request.Request(
            "https://www.kleague.com/api/clubRank.do",
            data=b"{}",
            headers={"Content-Type": "application/json; charset=UTF-8",
                     "Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            raw_data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    result = {}
    for league_key in ("league1", "league2"):
        rows = raw_data.get("data", {}).get(league_key, [])
        cleaned = []
        for row in rows:
            team_code = row.get("teamId", "")
            internal_id = KLEAGUE_CODE_MAP.get(team_code)
            team_info = TEAMS_BY_ID.get(internal_id, {}) if internal_id else {}
            recent = []
            for i in range(1, 7):
                g = row.get(f"game0{i}", "").strip()
                if g:
                    recent.append(g)
            cleaned.append({
                "rank":    row.get("rank"),
                "teamId":  internal_id or team_code,
                "name":    team_info.get("name", team_code),
                "short":   team_info.get("short", team_code),
                "emblem":  team_info.get("emblem", ""),
                "primary": team_info.get("primary", "#333"),
                "games":   row.get("gameCount", 0),
                "w":       row.get("winCnt", 0),
                "d":       row.get("tieCnt", 0),
                "l":       row.get("lossCnt", 0),
                "gf":      row.get("gainGoal", 0),
                "ga":      row.get("lossGoal", 0),
                "gd":      row.get("gapCnt", 0),
                "pts":     row.get("gainPoint", 0),
                "recent":  recent,
            })
        result[league_key] = cleaned
    return jsonify(result)


# ── 히트맵 API ───────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "players.db")

# sofascore_id → 한글 팀명 매핑
_SS_TO_KO = {t["sofascore_id"]: t["name"] for t in TEAMS}

def _ko_team(sofascore_id, fallback):
    return _SS_TO_KO.get(sofascore_id, fallback)

def _year_range(year_str):
    """연도 문자열 → (start_ts, end_ts) UTC 기준"""
    y = int(year_str)
    start = int(datetime(y,   1, 1).timestamp())
    end   = int(datetime(y+1, 1, 1).timestamp())
    return start, end

def _find_player(cur, name):
    """(player_id, team_id, matched_name) 반환, 없으면 (None, None, None)"""
    cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE name_ko = ?", (name,))
    row = cur.fetchone()
    if not row:
        # 공백 제거 후 재시도 (예: '브루노 실바' vs '브루노실바')
        name_no_space = name.replace(" ", "")
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE REPLACE(name_ko, ' ', '') = ?", (name_no_space,))
        row = cur.fetchone()
    if not row:
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE name LIKE ?", (f"%{name}%",))
        row = cur.fetchone()
    if not row:
        return (None, None, None)
    matched = row["name_ko"] or row["name"]
    return (row["id"], row["team_id"], matched)

def _flip_points(rows, player_team_id):
    """away 경기 포인트를 x축 반전 (x→100-x)"""
    result = []
    for r in rows:
        if r["away_team_id"] == player_team_id:
            result.append({"x": 100 - r["x"], "y": r["y"]})
        else:
            result.append({"x": r["x"], "y": r["y"]})
    return result

CURRENT_YEAR = str(datetime.now().year)

@app.route("/api/heatmap")
def get_heatmap():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"points": []})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    player_id, player_team_id, matched_name = _find_player(cur, name)
    if not player_id:
        conn.close()
        return jsonify({"points": [], "found": False})

    event_id    = request.args.get("eventId", "").strip()
    opponent_id = request.args.get("opponentId", "").strip()
    year        = request.args.get("year", CURRENT_YEAR).strip()
    year_start, year_end = _year_range(year)

    # 특정 경기 히트맵 → AWAY면 API에서 flip
    if event_id:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND h.event_id = ?
        """, (player_id, event_id))
        points = _flip_points(cur.fetchall(), player_team_id)
        conn.close()
        return jsonify({"points": points, "found": True, "playerId": player_id,
                        "filtered": True, "matchedName": matched_name})

    # 누적 히트맵 — AWAY 경기도 flip 정규화 (Sofascore와 동일하게)
    if opponent_id:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ?
              AND (e.home_team_id = ? OR e.away_team_id = ?)
              AND e.date_ts >= ? AND e.date_ts < ?
        """, (player_id, opponent_id, opponent_id, year_start, year_end))
    else:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ?
              AND (e.date_ts IS NULL OR (e.date_ts >= ? AND e.date_ts < ?))
        """, (player_id, year_start, year_end))

    points = _flip_points(cur.fetchall(), player_team_id)
    conn.close()
    return jsonify({"points": points, "found": True, "playerId": player_id,
                    "filtered": bool(opponent_id), "matchedName": matched_name})

@app.route("/api/player-matches")
def get_player_matches():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"matches": []})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    player_id, player_team_id, matched_name = _find_player(cur, name)
    if not player_id:
        conn.close()
        return jsonify({"matches": [], "found": False})

    year = request.args.get("year", "all").strip()

    if year == "all":
        cur.execute("""
            SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
                            e.away_team_id, e.away_team_name,
                            e.home_score, e.away_score, e.date_ts
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND e.date_ts IS NOT NULL
            ORDER BY e.date_ts DESC
        """, (player_id,))
    else:
        ys, ye = _year_range(year)
        cur.execute("""
            SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
                            e.away_team_id, e.away_team_name,
                            e.home_score, e.away_score, e.date_ts
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND e.date_ts >= ? AND e.date_ts < ?
            ORDER BY e.date_ts DESC
        """, (player_id, ys, ye))

    matches = []
    for r in cur.fetchall():
        matches.append({
            "id":        r["id"],
            "home":      _ko_team(r["home_team_id"], r["home_team_name"]),
            "away":      _ko_team(r["away_team_id"], r["away_team_name"]),
            "homeScore": r["home_score"],
            "awayScore": r["away_score"],
            "datets":    r["date_ts"],
            "isAway":    r["away_team_id"] == player_team_id,
        })
    conn.close()
    return jsonify({"matches": matches, "found": True, "playerId": player_id})


@app.route("/api/player-stat-report")
def get_player_stat_report():
    """선수 상세 스탯 보고서 - 포지션 대비 퍼센타일 포함"""
    import datetime as _dt
    name      = request.args.get("name", "").strip()
    player_id = request.args.get("playerId", type=int)
    year      = request.args.get("year")

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 선수 찾기
    if player_id:
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE id=?", (player_id,))
        row = cur.fetchone()
        if row:
            pid, team_id_db = row["id"], row["team_id"]
            matched = row["name_ko"] or row["name"]
        else:
            pid, team_id_db, matched = None, None, None
    else:
        pid, team_id_db, matched = _find_player(cur, name)

    if not pid:
        conn.close()
        return jsonify({"found": False}), 404

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 선수 기본 정보
    cur.execute("SELECT * FROM players WHERE id=?", (pid,))
    prow = cur.fetchone()
    pos_raw = None
    height  = prow["height"] if prow else None

    # 출전 포지션 (mps에서 최빈값)
    cur.execute(f"""
        SELECT mps.position, COUNT(*) cnt
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
        GROUP BY mps.position ORDER BY cnt DESC LIMIT 1
    """, (pid,) + yp)
    pr = cur.fetchone()
    pos_raw = pr[0] if pr else (prow["position"] if prow else "?")

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 ORDER BY yr
    """, (pid,))
    available_years = [r[0] for r in cur.fetchall()]

    # 대상 선수 집계 (90분 환산)
    cur.execute(f"""
        SELECT COUNT(*) games,
               SUM(mps.minutes_played) mins,
               SUM(mps.goals) goals, SUM(mps.assists) assists,
               SUM(mps.total_shots) shots, SUM(mps.shots_on_target) sot,
               AVG(mps.expected_goals) xg_avg,
               AVG(mps.accurate_passes_pct) pass_pct,
               SUM(mps.key_passes) key_passes,
               SUM(mps.total_passes) total_passes,
               SUM(mps.successful_dribbles) drib_s, SUM(mps.attempted_dribbles) drib_a,
               SUM(mps.tackles) tackles, SUM(mps.interceptions) ints,
               SUM(mps.clearances) clears, SUM(mps.blocked_shots) blocked,
               SUM(mps.aerial_won) aer_w, SUM(mps.aerial_lost) aer_l,
               SUM(mps.duel_won) duel_w, SUM(mps.duel_lost) duel_l,
               SUM(mps.fouls) fouls, SUM(mps.was_fouled) fouled,
               SUM(mps.yellow_cards) yellows, SUM(mps.red_cards) reds,
               SUM(mps.saves) saves, SUM(mps.goals_conceded) conceded,
               SUM(mps.touches) touches, SUM(mps.possession_lost) poss_lost,
               AVG(mps.rating) rating,
               SUM(mps.accurate_long_balls) long_b_s, SUM(mps.total_long_balls) long_b_a,
               SUM(mps.accurate_crosses) cross_s, SUM(mps.total_crosses) cross_a,
               SUM(mps.big_chances_missed) bcm
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
    """, (pid,) + yp)
    p = cur.fetchone()
    mins = p["mins"] or 1
    games = p["games"] or 0

    def p90(v): return round((v or 0) / mins * 90, 3) if mins else 0
    def pct(a, b): return round((a or 0) / (b or 1) * 100, 1) if b else None

    # 팀명
    cur.execute("SELECT DISTINCT mps.team_id FROM match_player_stats mps WHERE mps.player_id=? LIMIT 1", (pid,))
    tid_row = cur.fetchone()
    ss_team_id = tid_row[0] if tid_row else team_id_db
    team_name = _ko_name_by_ss_id(ss_team_id) or str(ss_team_id)

    # 키 순위 (데이터 있는 경우)
    weight = prow["weight"] if prow and "weight" in prow.keys() else None

    def physical_rank(col, val):
        if not val: return None
        cur.execute(f"""
            SELECT COUNT(*) FROM players p2
            WHERE p2.{col} > ? AND p2.{col} IS NOT NULL AND p2.{col} > 0
              AND EXISTS (SELECT 1 FROM match_player_stats m2 JOIN events e2 ON m2.event_id=e2.id
                          WHERE m2.player_id=p2.id AND e2.tournament_id=777)
        """, (val,))
        above = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM players p2
            WHERE p2.{col} IS NOT NULL AND p2.{col} > 0
              AND EXISTS (SELECT 1 FROM match_player_stats m2 JOIN events e2 ON m2.event_id=e2.id
                          WHERE m2.player_id=p2.id AND e2.tournament_id=777)
        """)
        total = cur.fetchone()[0]
        return {"rank": above+1, "total": total, "pct": round((1 - above/total)*100) if total else None}

    height_rank = physical_rank("height", height)
    weight_rank = physical_rank("weight", weight)

    # ── 같은 포지션 선수 집계 (퍼센타일 기준) ──────────────────
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.minutes_played)              mins,
               SUM(mps.goals)                       goals,
               SUM(mps.assists)                     assists,
               SUM(mps.total_shots)                 shots,
               SUM(mps.shots_on_target)             sot,
               AVG(mps.accurate_passes_pct)         pass_pct,
               SUM(mps.key_passes)                  key_passes,
               SUM(mps.successful_dribbles)         drib_s,
               SUM(mps.attempted_dribbles)          drib_a,
               SUM(mps.tackles)                     tackles,
               SUM(mps.interceptions)               ints,
               SUM(mps.clearances)                  clears,
               SUM(mps.blocked_shots)               blocked,
               SUM(mps.aerial_won)                  aer_w,
               SUM(mps.aerial_lost)                 aer_l,
               SUM(mps.duel_won)                    duel_w,
               SUM(mps.duel_lost)                   duel_l,
               SUM(mps.saves)                       saves,
               SUM(mps.goals_conceded)              conceded,
               SUM(mps.fouls)                       fouls,
               SUM(mps.was_fouled)                  fouled,
               SUM(mps.touches)                     touches,
               COUNT(*)                             games
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777 AND mps.position=? {year_clause}
        GROUP BY mps.player_id
        HAVING mins >= 270 AND games >= 5
    """, (pos_raw,) + yp)

    peers = {}
    for r in cur.fetchall():
        m = r["mins"] or 1
        def v90(col): return (r[col] or 0) / m * 90
        peers[r["player_id"]] = {
            "goals":    v90("goals"),
            "assists":  v90("assists"),
            "shots":    v90("shots"),
            "sot":      v90("sot"),
            "pass_pct": r["pass_pct"] or 0,
            "key_passes": v90("key_passes"),
            "drib_s":   v90("drib_s"),
            "drib_pct": pct(r["drib_s"], r["drib_a"]) or 0,
            "tackles":  v90("tackles"),
            "ints":     v90("ints"),
            "clears":   v90("clears"),
            "blocked":  v90("blocked"),
            "aer_w":    v90("aer_w"),
            "aer_pct":  pct(r["aer_w"], (r["aer_w"] or 0)+(r["aer_l"] or 0)) or 0,
            "duel_w":   v90("duel_w"),
            "duel_pct": pct(r["duel_w"], (r["duel_w"] or 0)+(r["duel_l"] or 0)) or 0,
            "saves":    v90("saves"),
            "touches":  v90("touches"),
            "fouls":    v90("fouls"),
        }

    def percentile(key, val, higher_is_better=True):
        vals = [v[key] for v in peers.values() if v[key] is not None]
        if not vals: return 50
        if higher_is_better:
            below = sum(1 for v in vals if v < val)
        else:
            below = sum(1 for v in vals if v > val)
        return round(below / len(vals) * 100)

    # 대상 선수 90분 환산값
    my = {
        "goals":    p90(p["goals"]),
        "assists":  p90(p["assists"]),
        "shots":    p90(p["shots"]),
        "sot":      p90(p["sot"]),
        "pass_pct": p["pass_pct"] or 0,
        "key_passes": p90(p["key_passes"]),
        "drib_s":   p90(p["drib_s"]),
        "drib_pct": pct(p["drib_s"], p["drib_a"]) or 0,
        "tackles":  p90(p["tackles"]),
        "ints":     p90(p["ints"]),
        "clears":   p90(p["clears"]),
        "blocked":  p90(p["blocked"]),
        "aer_w":    p90(p["aer_w"]),
        "aer_pct":  pct(p["aer_w"], (p["aer_w"] or 0)+(p["aer_l"] or 0)) or 0,
        "duel_w":   p90(p["duel_w"]),
        "duel_pct": pct(p["duel_w"], (p["duel_w"] or 0)+(p["duel_l"] or 0)) or 0,
        "saves":    p90(p["saves"]),
        "touches":  p90(p["touches"]),
        "fouls":    p90(p["fouls"]),
    }

    # 퍼센타일 계산
    pctile = {k: percentile(k, my[k]) for k in my}
    pctile["fouls"] = percentile("fouls", my["fouls"], higher_is_better=False)

    # 포지션별 주요 지표 그룹
    POS_GROUPS = {
        "G": [
            {"key":"saves",    "label":"선방(90분)",         "icon":"🧤"},
            {"key":"aer_pct",  "label":"공중볼 장악률(%)",    "icon":"✈"},
            {"key":"pass_pct", "label":"패스 성공률(%)",      "icon":"🎯"},
            {"key":"touches",  "label":"볼터치(90분)",        "icon":"👟"},
        ],
        "D": [
            {"key":"tackles",  "label":"태클(90분)",          "icon":"🛡"},
            {"key":"ints",     "label":"인터셉트(90분)",       "icon":"✂"},
            {"key":"clears",   "label":"클리어링(90분)",       "icon":"🥊"},
            {"key":"aer_w",    "label":"공중볼 성공(90분)",    "icon":"✈"},
            {"key":"aer_pct",  "label":"공중볼 장악률(%)",     "icon":"📊"},
            {"key":"blocked",  "label":"슈팅 차단(90분)",      "icon":"🚫"},
            {"key":"duel_pct", "label":"지상 듀얼 승률(%)",    "icon":"⚔"},
            {"key":"pass_pct", "label":"패스 성공률(%)",       "icon":"🎯"},
        ],
        "M": [
            {"key":"key_passes","label":"키패스(90분)",        "icon":"🔑"},
            {"key":"pass_pct", "label":"패스 성공률(%)",       "icon":"🎯"},
            {"key":"assists",  "label":"도움(90분)",           "icon":"🎨"},
            {"key":"drib_s",   "label":"드리블 성공(90분)",    "icon":"💨"},
            {"key":"tackles",  "label":"태클(90분)",           "icon":"🛡"},
            {"key":"ints",     "label":"인터셉트(90분)",       "icon":"✂"},
            {"key":"goals",    "label":"득점(90분)",           "icon":"⚽"},
            {"key":"touches",  "label":"볼터치(90분)",         "icon":"👟"},
        ],
        "F": [
            {"key":"goals",    "label":"득점(90분)",           "icon":"⚽"},
            {"key":"assists",  "label":"도움(90분)",           "icon":"🎨"},
            {"key":"shots",    "label":"슈팅(90분)",           "icon":"🎯"},
            {"key":"sot",      "label":"유효슈팅(90분)",       "icon":"🎯"},
            {"key":"drib_s",   "label":"드리블 성공(90분)",    "icon":"💨"},
            {"key":"drib_pct", "label":"드리블 성공률(%)",     "icon":"📊"},
            {"key":"aer_w",    "label":"공중볼 성공(90분)",    "icon":"✈"},
            {"key":"fouls",    "label":"파울 유도(90분)",      "icon":"🤸"},
        ],
    }

    stat_groups = POS_GROUPS.get(pos_raw, POS_GROUPS["M"])
    stat_items = []
    for sg in stat_groups:
        k = sg["key"]
        raw_val = my.get(k, 0)
        stat_items.append({
            "key":     k,
            "label":   sg["label"],
            "icon":    sg["icon"],
            "val":     round(raw_val, 2),
            "pctile":  pctile.get(k, 50),
            "peer_cnt": len(peers),
        })

    # 레이더용 5개 지표 (포지션별)
    RADAR_KEYS = {
        "G": ["saves","aer_pct","pass_pct","touches","duel_pct"],
        "D": ["tackles","ints","aer_pct","blocked","pass_pct"],
        "M": ["key_passes","pass_pct","drib_s","tackles","goals"],
        "F": ["goals","shots","drib_s","aer_w","assists"],
    }
    radar_keys = RADAR_KEYS.get(pos_raw, RADAR_KEYS["M"])
    RADAR_LABELS = {
        "goals":"득점","assists":"도움","shots":"슈팅","sot":"유효슈팅",
        "pass_pct":"패스%","key_passes":"키패스","drib_s":"드리블",
        "tackles":"태클","ints":"인터셉트","aer_pct":"공중볼%",
        "blocked":"슈팅차단","saves":"선방","touches":"터치","duel_pct":"듀얼승률%",
    }
    radar = [{"label": RADAR_LABELS.get(k, k), "pctile": pctile.get(k, 50)} for k in radar_keys]

    # 최근 5경기 폼
    cur.execute("""
        SELECT e.date_ts,
               CASE WHEN mps.is_home=1 THEN e.away_team_id ELSE e.home_team_id END opp_id,
               mps.goals, mps.assists, mps.rating, mps.result, mps.is_home,
               e.home_score, e.away_score,
               mps.tackles, mps.interceptions, mps.clearances, mps.aerial_won,
               mps.saves, mps.shots_on_target, mps.key_passes
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 5
    """, (pid,))
    rm = {1:"W", 0:"D", -1:"L"}
    recent_form = []
    for r in cur.fetchall():
        d = _dt.datetime.utcfromtimestamp(r[0])
        recent_form.append({
            "date":       f"{d.year}/{d.month}/{d.day}",
            "opponent":   _ko_name_by_ss_id(str(r[1])) or str(r[1]),
            "is_home":    bool(r[6]),
            "goals":      r[2] or 0,
            "assists":    r[3] or 0,
            "rating":     round(r[4], 1) if r[4] else None,
            "result":     rm.get(r[5], "?"),
            "score":      f"{r[7]}-{r[8]}",
            "tackles":    r[9] or 0,
            "ints":       r[10] or 0,
            "clears":     r[11] or 0,
            "aer_w":      r[12] or 0,
            "saves":      r[13] or 0,
            "sot":        r[14] or 0,
            "key_passes": r[15] or 0,
        })

    conn.close()
    pos_label = {"G":"GK","D":"DF","M":"MF","F":"FW"}.get(pos_raw, pos_raw or "?")
    return jsonify({
        "found":      True,
        "player": {
            "id":       pid,
            "name":     matched,
            "team":     team_name,
            "pos":      pos_raw,
            "pos_label": pos_label,
            "height":   height,
            "weight":   weight,
            "height_rank": height_rank,
            "weight_rank": weight_rank,
            "games":    games,
            "mins":     int(mins),
            "goals":    p["goals"] or 0,
            "assists":  p["assists"] or 0,
            "rating":   round(p["rating"], 2) if p["rating"] else None,
            "yellows":  p["yellows"] or 0,
            "reds":     p["reds"] or 0,
        },
        "available_years": available_years,
        "stat_items":  stat_items,
        "radar":       radar,
        "recent_form": recent_form,
        "peer_count":  len(peers),
    })


@app.route("/api/player-analytics")
def get_player_analytics():
    """선수 개인 분석 보고서"""
    import datetime as _dt
    player_id = request.args.get("playerId", type=int)
    year      = request.args.get("year")
    if not player_id:
        return jsonify({}), 400

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 선수 기본 정보
    cur.execute("""
        SELECT COALESCE(p.name_ko, p.name) nm, p.position pos, p.team_id, p.height, p.preferred_foot
        FROM players p WHERE p.id=?
    """, (player_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({}), 404

    name, position, team_id, height, preferred_foot = row["nm"], row["pos"], row["team_id"], row["height"], row["preferred_foot"]

    # 팀 한국어명 조회
    cur.execute("SELECT DISTINCT mps.team_id FROM match_player_stats mps WHERE mps.player_id=? LIMIT 1", (player_id,))
    tid_row = cur.fetchone()
    ss_team_id = tid_row[0] if tid_row else team_id
    team_name = _ko_name_by_ss_id(ss_team_id) or str(ss_team_id)

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 AND e.date_ts IS NOT NULL
        ORDER BY yr
    """, (player_id,))
    available_years = [r[0] for r in cur.fetchall()]

    # 시즌별 집계
    cur.execute("""
        SELECT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr,
               COUNT(*) games, SUM(mps.goals) goals, SUM(mps.assists) assists,
               AVG(mps.rating) rating, SUM(mps.minutes_played) minutes
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777
        GROUP BY yr ORDER BY yr
    """, (player_id,))
    season_summary = [
        {"year": r[0], "games": r[1], "goals": r[2] or 0, "assists": r[3] or 0,
         "rating": round(r[4], 2) if r[4] else None, "minutes": r[5] or 0}
        for r in cur.fetchall()
    ]

    # 월별 분석
    cur.execute(f"""
        SELECT CAST(strftime('%m', datetime(e.date_ts,'unixepoch','localtime')) AS INTEGER) mn,
               COUNT(*) games, SUM(mps.goals) goals, SUM(mps.assists) assists,
               AVG(mps.rating) rating
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
        GROUP BY mn ORDER BY mn
    """, (player_id,) + yp)
    monthly = [
        {"month": r[0], "games": r[1], "goals": r[2] or 0, "assists": r[3] or 0,
         "rating": round(r[4], 2) if r[4] else None}
        for r in cur.fetchall()
    ]

    # 최근 10경기 폼
    cur.execute("""
        SELECT e.date_ts,
               CASE WHEN mps.is_home=1 THEN e.away_team_id ELSE e.home_team_id END opp_id,
               mps.goals, mps.assists, mps.rating, mps.result, mps.is_home,
               e.home_score, e.away_score
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 10
    """, (player_id,))
    result_map = {1: "W", 0: "D", -1: "L"}
    recent_form = []
    for r in cur.fetchall():
        d = _dt.datetime.utcfromtimestamp(r[0])
        opp_name = _ko_name_by_ss_id(str(r[1])) or str(r[1])
        recent_form.append({
            "date": f"{d.year}/{d.month}/{d.day}",
            "opponent": opp_name,
            "is_home": bool(r[6]),
            "goals": r[2] or 0,
            "assists": r[3] or 0,
            "rating": round(r[4], 1) if r[4] else None,
            "result": result_map.get(r[5], "?"),
            "score": f"{r[7]}-{r[8]}" if r[7] is not None else "?"
        })

    # 레이더: 전체 선수 대비 백분위 (5경기 이상, 300분 이상)
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.goals) + SUM(mps.assists)        AS ga,
               SUM(mps.minutes_played)                   AS mins,
               AVG(mps.accurate_passes_pct)              AS pass_pct,
               SUM(mps.tackles) + SUM(mps.interceptions) + SUM(mps.clearances) AS def_acts,
               SUM(mps.shots_on_target)                  AS sot,
               SUM(mps.total_shots)                      AS ts,
               SUM(mps.successful_dribbles)              AS sdr,
               SUM(mps.attempted_dribbles)               AS adr,
               COUNT(*)                                  AS games
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777 {year_clause}
        GROUP BY mps.player_id
        HAVING games >= 5 AND mins >= 300
    """, yp)

    all_stats = {}
    for r in cur.fetchall():
        pid, ga, mins, pass_pct, def_acts, sot, ts, sdr, adr, games = r
        if not mins: continue
        all_stats[pid] = {
            "attack":   (ga or 0) / mins * 90,
            "passing":  pass_pct or 0,
            "defense":  (def_acts or 0) / mins * 90,
            "shooting": (sot / ts) * 100 if ts and ts >= 3 else 0,
            "dribble":  (sdr / adr) * 100 if adr and adr >= 3 else 0,
        }

    radar = {}
    if player_id in all_stats:
        p_vals = all_stats[player_id]
        n = len(all_stats)
        for axis in ["attack", "passing", "defense", "shooting", "dribble"]:
            vals = [v[axis] for v in all_stats.values()]
            below = sum(1 for v in vals if v < p_vals[axis])
            radar[axis] = round(below / n * 100)
    else:
        radar = {k: 0 for k in ["attack", "passing", "defense", "shooting", "dribble"]}

    # 전체 집계 (헤더용)
    cur.execute(f"""
        SELECT COUNT(*), SUM(mps.goals), SUM(mps.assists), AVG(mps.rating), SUM(mps.minutes_played),
               SUM(mps.yellow_cards), SUM(mps.red_cards)
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
    """, (player_id,) + yp)
    agg = cur.fetchone()
    conn.close()

    return jsonify({
        "info": {
            "name": name,
            "position": position or "?",
            "team": team_name,
            "height": height,
            "preferred_foot": preferred_foot,
            "games":   agg[0] or 0,
            "goals":   agg[1] or 0,
            "assists": agg[2] or 0,
            "rating":  round(agg[3], 2) if agg[3] else None,
            "minutes": agg[4] or 0,
            "yellow_cards": agg[5] or 0,
            "red_cards":    agg[6] or 0,
        },
        "available_years": available_years,
        "season_summary":  season_summary,
        "monthly":         monthly,
        "recent_form":     recent_form,
        "radar":           radar,
    })


@app.route("/api/league-dashboard")
def get_league_dashboard():
    """K2 리그 전체 선수 인사이트 대시보드"""
    year = request.args.get("year")   # None → 전체

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM events e WHERE e.tournament_id=777 AND e.date_ts IS NOT NULL ORDER BY yr
    """)
    available_years = [r[0] for r in cur.fetchall()]

    # ── 랭킹 공통 쿼리 ─────────────────────────────────────────
    base_sql = f"""
        SELECT mps.player_id,
               COALESCE(p.name_ko, mps.player_name) name,
               mps.position pos,
               mps.team_id,
               COUNT(*)                   games,
               SUM(mps.goals)             goals,
               SUM(mps.assists)           assists,
               AVG(mps.rating)            rating,
               SUM(mps.minutes_played)    minutes,
               SUM(mps.total_shots)       shots,
               SUM(mps.shots_on_target)   sot,
               SUM(mps.key_passes)        key_passes,
               SUM(mps.tackles)           tackles,
               SUM(mps.interceptions)     interceptions,
               SUM(mps.successful_dribbles) dribbles,
               SUM(mps.attempted_dribbles) dribbles_att,
               SUM(mps.duel_won)          duel_won,
               SUM(mps.duel_lost)         duel_lost,
               SUM(mps.yellow_cards)      yellows,
               SUM(mps.red_cards)         reds,
               SUM(mps.saves)             saves
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        LEFT JOIN players p ON mps.player_id=p.id
        WHERE e.tournament_id=777 {year_clause}
        GROUP BY mps.player_id
        HAVING games >= 3
    """
    cur.execute(base_sql, yp)
    rows = cur.fetchall()

    def row_to_dict(r):
        tid = r["team_id"]
        return {
            "id":       r["player_id"],
            "name":     r["name"] or "?",
            "pos":      r["pos"] or "?",
            "team":     _ko_name_by_ss_id(tid) or str(tid),
            "games":    r["games"],
            "goals":    r["goals"] or 0,
            "assists":  r["assists"] or 0,
            "rating":   round(r["rating"], 2) if r["rating"] else None,
            "minutes":  r["minutes"] or 0,
            "shots":    r["shots"] or 0,
            "sot":      r["sot"] or 0,
            "key_passes": r["key_passes"] or 0,
            "tackles":  r["tackles"] or 0,
            "interceptions": r["interceptions"] or 0,
            "dribbles": r["dribbles"] or 0,
            "dribbles_att": r["dribbles_att"] or 0,
            "duel_won":  r["duel_won"] or 0,
            "duel_lost": r["duel_lost"] or 0,
            "duel_pct":  round((r["duel_won"] or 0) / max((r["duel_won"] or 0) + (r["duel_lost"] or 0), 1) * 100, 1),
            "tackles_p90": round((r["tackles"] or 0) / max(r["minutes"] or 1, 1) * 90, 2),
            "ints_p90":    round((r["interceptions"] or 0) / max(r["minutes"] or 1, 1) * 90, 2),
            "yellows":  r["yellows"] or 0,
            "reds":     r["reds"] or 0,
            "saves":    r["saves"] or 0,
        }

    all_players = [row_to_dict(r) for r in rows]

    # 랭킹 TOP20
    top_scorers  = sorted(all_players, key=lambda x: (-x["goals"],  -(x["assists"]), x["name"]))[:20]
    top_assists  = sorted(all_players, key=lambda x: (-x["assists"], -(x["goals"]),  x["name"]))[:20]
    top_rated    = sorted(
        [p for p in all_players if p["rating"] and p["minutes"] >= 270],
        key=lambda x: -x["rating"]
    )[:20]
    top_dribbles = sorted(
        [p for p in all_players if p["dribbles"] > 0],
        key=lambda x: -x["dribbles"]
    )[:20]
    top_defenders = sorted(
        [p for p in all_players if p["pos"] in ("D", "M") and (p["duel_won"] + p["duel_lost"]) >= 10],
        key=lambda x: (-x["duel_pct"], -(x["tackles_p90"] + x["ints_p90"]))
    )[:20]

    # ── 포지션별 평균 스탯 ─────────────────────────────────────
    pos_map = {"G": "GK", "D": "DF", "M": "MF", "F": "FW"}
    pos_stats = {}
    for p in all_players:
        pos = pos_map.get(p["pos"], "기타")
        if pos == "기타": continue
        if pos not in pos_stats:
            pos_stats[pos] = {"goals":0,"assists":0,"rating_sum":0,"rating_cnt":0,
                              "tackles":0,"dribbles":0,"key_passes":0,"shots":0,"cnt":0}
        s = pos_stats[pos]
        s["cnt"] += 1
        mins = p["minutes"] or 1
        s["goals"]    += p["goals"] / mins * 90
        s["assists"]  += p["assists"] / mins * 90
        s["tackles"]  += p["tackles"] / mins * 90
        s["dribbles"] += p["dribbles"] / mins * 90
        s["key_passes"] += p["key_passes"] / mins * 90
        s["shots"]    += p["shots"] / mins * 90
        if p["rating"]:
            s["rating_sum"] += p["rating"]; s["rating_cnt"] += 1

    position_avg = {}
    for pos, s in pos_stats.items():
        n = s["cnt"] or 1
        position_avg[pos] = {
            "goals":     round(s["goals"]/n, 3),
            "assists":   round(s["assists"]/n, 3),
            "tackles":   round(s["tackles"]/n, 3),
            "dribbles":  round(s["dribbles"]/n, 3),
            "key_passes":round(s["key_passes"]/n, 3),
            "shots":     round(s["shots"]/n, 3),
            "rating":    round(s["rating_sum"]/s["rating_cnt"], 2) if s["rating_cnt"] else None,
            "count":     s["cnt"],
        }

    # ── 팀별 공격력 ────────────────────────────────────────────
    team_stats = {}
    for p in all_players:
        t = p["team"]
        if t not in team_stats:
            team_stats[t] = {"goals":0,"assists":0,"rating_sum":0,"rating_cnt":0,
                             "players":0,"minutes":0}
        s = team_stats[t]
        s["goals"]   += p["goals"]
        s["assists"] += p["assists"]
        s["players"] += 1
        s["minutes"] += p["minutes"]
        if p["rating"]: s["rating_sum"] += p["rating"]; s["rating_cnt"] += 1

    team_attack = [
        {"team": t, "goals": s["goals"], "assists": s["assists"],
         "rating": round(s["rating_sum"]/s["rating_cnt"],2) if s["rating_cnt"] else None,
         "players": s["players"]}
        for t, s in team_stats.items()
    ]
    team_attack.sort(key=lambda x: -x["goals"])

    # ── 월별 리그 트렌드 ───────────────────────────────────────
    cur.execute(f"""
        SELECT CAST(strftime('%m', datetime(e.date_ts,'unixepoch','localtime')) AS INTEGER) mn,
               SUM(mps.goals) goals,
               SUM(mps.assists) assists,
               AVG(mps.rating) rating,
               COUNT(DISTINCT e.id) games
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777 {year_clause}
        GROUP BY mn ORDER BY mn
    """, yp)
    monthly_trend = [
        {"month": r[0], "goals": r[1] or 0, "assists": r[2] or 0,
         "rating": round(r[3],2) if r[3] else None, "games": r[4]}
        for r in cur.fetchall()
    ]

    # ── 평점 분포 (히스토그램 버킷) ───────────────────────────
    rating_buckets = {}
    for p in all_players:
        if not p["rating"]: continue
        bucket = f"{int(p['rating']*10)//5 * 5 / 10:.1f}"
        rating_buckets[bucket] = rating_buckets.get(bucket, 0) + 1
    rating_dist = [{"bucket": k, "count": v}
                   for k, v in sorted(rating_buckets.items(), key=lambda x: float(x[0]))]

    conn.close()
    return jsonify({
        "available_years": available_years,
        "top_scorers":     top_scorers,
        "top_assists":     top_assists,
        "top_rated":       top_rated,
        "top_dribbles":    top_dribbles,
        "top_defenders":   top_defenders,
        "position_avg":    position_avg,
        "team_attack":     team_attack,
        "monthly_trend":   monthly_trend,
        "rating_dist":     rating_dist,
    })


@app.route("/api/team-goal-timing")
def get_team_goal_timing():
    """팀 득점/실점 시간대·전후반 분석"""
    team_id_str = request.args.get("teamId")
    year        = request.args.get("year")
    team_info   = next((t for t in TEAMS if t["id"] == team_id_str), None)
    if not team_info:
        return jsonify({"error": "team not found"}), 404

    ss_id   = team_info["sofascore_id"]
    db_path = os.path.join(BASE_DIR, "players.db")
    conn    = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur     = conn.cursor()

    # goal_events 테이블 없으면 빈 데이터 반환
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='goal_events'")
    if not cur.fetchone():
        conn.close()
        return jsonify({"ready": False})

    year_clause = ""
    yp = ()
    if year:
        year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?"
        yp = (year,)

    # 시간대 구간
    BANDS = [(1,15),(16,30),(31,45),(46,60),(61,75),(76,90),(91,120)]
    BAND_LABELS = ["1-15'","16-30'","31-45'","46-60'","61-75'","76-90'","90+'"]

    def count_goals(for_or_against):
        """for_or_against: 'for' = 득점, 'against' = 실점"""
        if for_or_against == "for":
            team_cond = "g.team_id = ?"
        else:
            # 실점 = 상대팀이 우리 팀 경기에서 넣은 골 (team_id != ss_id)
            team_cond = "g.team_id != ? AND (e.home_team_id=? OR e.away_team_id=?)"

        results = []
        for (s, e_min), label in zip(BANDS, BAND_LABELS):
            if for_or_against == "for":
                cur.execute(f"""
                    SELECT COUNT(*) FROM goal_events g
                    JOIN events e ON g.event_id = e.id
                    WHERE {team_cond}
                      AND (e.home_team_id=? OR e.away_team_id=?)
                      AND (g.minute + COALESCE(g.added_time,0)) >= ?
                      AND (g.minute + COALESCE(g.added_time,0)) <= ?
                      {year_clause}
                """, (ss_id, ss_id, ss_id, s, e_min) + yp)
            else:
                cur.execute(f"""
                    SELECT COUNT(*) FROM goal_events g
                    JOIN events e ON g.event_id = e.id
                    WHERE {team_cond}
                      AND (g.minute + COALESCE(g.added_time,0)) >= ?
                      AND (g.minute + COALESCE(g.added_time,0)) <= ?
                      {year_clause}
                """, (ss_id, ss_id, ss_id, s, e_min) + yp)
            results.append({"label": label, "count": cur.fetchone()[0]})
        return results

    gf_bands = count_goals("for")
    ga_bands = count_goals("against")

    # 전후반 집계
    def half_sum(bands, half):
        idxs = range(0, 3) if half == 1 else range(3, len(bands))
        return sum(bands[i]["count"] for i in idxs)

    gf_h1 = half_sum(gf_bands, 1)
    gf_h2 = half_sum(gf_bands, 2)
    ga_h1 = half_sum(ga_bands, 1)
    ga_h2 = half_sum(ga_bands, 2)

    # 전체 경기 수 (비율 계산용)
    cur.execute(f"""
        SELECT COUNT(*) FROM events e
        WHERE tournament_id=777 AND (home_team_id=? OR away_team_id=?)
        {year_clause}
    """, (ss_id, ss_id) + yp)
    total_games = cur.fetchone()[0] or 1

    conn.close()
    return jsonify({
        "ready": True,
        "team": team_info["name"],
        "total_games": total_games,
        "gf_bands":  gf_bands,
        "ga_bands":  ga_bands,
        "half": {
            "gf_h1": gf_h1, "gf_h2": gf_h2,
            "ga_h1": ga_h1, "ga_h2": ga_h2,
        }
    })


@app.route("/api/kleague2/teams")
def get_kleague2_teams():
    """히트맵 데이터가 있는 K리그2 팀 목록 (수원 삼성 제외)"""
    if not os.path.exists(DB_PATH):
        return jsonify([])
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT DISTINCT team_id FROM match_player_stats
        WHERE team_id != 7652
        ORDER BY team_id
    """).fetchall()
    conn.close()
    team_map = {t["sofascore_id"]: t for t in TEAMS}
    result = []
    for (tid,) in rows:
        t = team_map.get(tid)
        if t:
            result.append({"id": t["id"], "sofascore_id": tid, "name": t["name"],
                           "short": t["short"], "emblem": t["emblem"], "primary": t["primary"]})
    result.sort(key=lambda x: x["name"])
    return jsonify(result)


@app.route("/api/kleague2/players")
def get_kleague2_players():
    """팀별 선수 목록 (player_id + 이름)"""
    team_id = request.args.get("teamId", "").strip()
    if not team_id:
        return jsonify({"error": "teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify([])
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT DISTINCT player_id, player_name, position,
               COUNT(DISTINCT event_id) as games,
               ROUND(AVG(rating), 2) as avg_rating
        FROM match_player_stats
        WHERE team_id = ? AND player_name IS NOT NULL
        GROUP BY player_id
        ORDER BY games DESC, player_name
    """, (team_id,)).fetchall()
    conn.close()
    return jsonify([{
        "playerId": r[0], "name": r[1], "position": r[2],
        "games": r[3], "avgRating": r[4]
    } for r in rows])


@app.route("/api/kleague2/heatmap")
def get_kleague2_heatmap():
    """선수 ID 기반 히트맵 (수원 삼성 외 팀)"""
    player_id = request.args.get("playerId", "").strip()
    team_id   = request.args.get("teamId", "").strip()
    event_id  = request.args.get("eventId", "").strip()
    if not player_id or not team_id:
        return jsonify({"error": "playerId and teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"points": []})

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if event_id:
        rows = conn.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND h.event_id = ?
        """, (player_id, event_id)).fetchall()
    else:
        rows = conn.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ?
        """, (player_id,)).fetchall()

    points = _flip_points(rows, int(team_id))

    # 경기 목록
    matches_rows = conn.execute("""
        SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
               e.away_team_id, e.away_team_name,
               e.home_score, e.away_score, e.date_ts
        FROM heatmap_points h
        JOIN events e ON h.event_id = e.id
        WHERE h.player_id = ? AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC
    """, (player_id,)).fetchall()

    matches = [{
        "id":        r["id"],
        "home":      _ko_team(r["home_team_id"], r["home_team_name"]),
        "away":      _ko_team(r["away_team_id"], r["away_team_name"]),
        "homeScore": r["home_score"],
        "awayScore": r["away_score"],
        "datets":    r["date_ts"],
        "isAway":    r["away_team_id"] == int(team_id),
    } for r in matches_rows]

    conn.close()
    return jsonify({"points": points, "matches": matches, "playerId": player_id})


# ── 포지션 인사이트 API ──────────────────────────────────

@app.route("/api/insights/top-performers")
def insights_top_performers():
    """포지션별 TOP 퍼포머 (최소 3경기 이상, 90분 환산)"""
    year = request.args.get("year", "2026")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    date_cond = f"AND match_date >= '{year}-01-01' AND match_date < '{int(year)+1}-01-01'" if year != "all" else ""

    def pinfo(r):
        return {
            "player_id": r["player_id"],
            "name": r["name_ko"] or r["player_name"] or "",
            "team": _ko_team(r["team_id"], ""),
            "games": r["games"], "mins": r["mins"],
        }

    result = {}

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.goals) as goals, SUM(COALESCE(m.expected_goals,0)) as xg,
               AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='F' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY goals DESC LIMIT 15
    """).fetchall()
    result["F"] = [{**pinfo(r),
        "goals": r["goals"] or 0,
        "goals_p90": round((r["goals"] or 0) / r["mins"] * 90, 2),
        "xg": round(r["xg"] or 0, 2),
        "xg_eff": round((r["goals"] or 0) / r["xg"], 2) if (r["xg"] or 0) > 0 else None,
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.total_passes) as tp, SUM(m.accurate_passes) as ap,
               SUM(m.tackles) as tkl, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='M' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90 AND tp>0
        ORDER BY (CAST(ap AS REAL)/tp) DESC LIMIT 15
    """).fetchall()
    result["M"] = [{**pinfo(r),
        "pass_acc": round((r["ap"] or 0) / r["tp"] * 100, 1) if r["tp"] else None,
        "passes_p90": round((r["tp"] or 0) / r["mins"] * 90, 1),
        "tackles_p90": round((r["tkl"] or 0) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.tackles) as tkl, SUM(COALESCE(m.interceptions,0)) as intc,
               SUM(m.clearances) as clr, SUM(m.aerial_won) as aer,
               SUM(m.duel_won) as duel, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='D' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY (tkl + intc*1.5 + clr + aer + duel) / mins DESC LIMIT 15
    """).fetchall()
    result["D"] = [{**pinfo(r),
        "def_score_p90": round(
            ((r["tkl"] or 0) + (r["intc"] or 0)*1.5 + (r["clr"] or 0)
             + (r["aer"] or 0) + (r["duel"] or 0)) / r["mins"] * 90, 2),
        "tackles_p90": round((r["tkl"] or 0) / r["mins"] * 90, 2),
        "clearances_p90": round((r["clr"] or 0) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    conn.close()
    return jsonify(result)


@app.route("/api/insights/xg-efficiency")
def insights_xg_efficiency():
    year = request.args.get("year", "2026")
    date_cond = f"AND match_date >= '{year}-01-01' AND match_date < '{int(year)+1}-01-01'" if year != "all" else ""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.goals) as goals,
               SUM(COALESCE(m.expected_goals,0)) as xg, SUM(m.total_shots) as shots
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='F' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND xg>0.5
        ORDER BY goals DESC LIMIT 20
    """).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"],
        "goals": r["goals"] or 0, "xg": round(r["xg"], 2),
        "diff": round((r["goals"] or 0) - r["xg"], 2),
        "shots": r["shots"] or 0,
    } for r in rows])


@app.route("/api/insights/forward-goals")
def insights_forward_goals():
    player_id = request.args.get("playerId", "").strip()
    year = request.args.get("year", "all")

    if not player_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        date_cond = f"AND match_date >= '{year}-01-01' AND match_date < '{int(year)+1}-01-01'" if year != "all" else ""
        rows = conn.execute(f"""
            SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
                   SUM(m.goals) as total_goals
            FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
            WHERE m.position='F' AND m.minutes_played>0 AND m.goals>0 {date_cond}
            GROUP BY m.player_id ORDER BY total_goals DESC LIMIT 30
        """).fetchall()
        conn.close()
        return jsonify([{
            "player_id": r["player_id"],
            "name": r["name_ko"] or "",
            "team": _ko_team(r["team_id"], ""),
            "goals": r["total_goals"],
        } for r in rows])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    bands = [("1-15",1,15),("16-30",16,30),("31-45",31,45),
             ("46-60",46,60),("61-75",61,75),("76-90",76,120)]
    time_data = []
    for label, lo, hi in bands:
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM goal_events
            WHERE player_id=? AND minute>=? AND minute<=? AND is_own_goal=0
        """, (player_id, lo, hi)).fetchone()
        time_data.append({"band": label, "goals": row["cnt"]})

    opp_rows = conn.execute("""
        SELECT CASE WHEN g.is_home=1 THEN e.away_team_name ELSE e.home_team_name END as opponent,
               COUNT(*) as goals
        FROM goal_events g JOIN events e ON g.event_id = e.id
        WHERE g.player_id=? AND g.is_own_goal=0
        GROUP BY opponent ORDER BY goals DESC
    """, (player_id,)).fetchall()

    info = conn.execute("""
        SELECT COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.player_id=? AND m.player_name IS NOT NULL LIMIT 1
    """, (player_id,)).fetchone()
    conn.close()

    return jsonify({
        "player_id": int(player_id),
        "name": info["name_ko"] if info else "",
        "team": _ko_team(info["team_id"], "") if info else "",
        "time_bands": time_data,
        "by_opponent": [{"opponent": r["opponent"], "goals": r["goals"]} for r in opp_rows],
    })


@app.route("/api/insights/midfielder-pass")
def insights_midfielder_pass():
    year = request.args.get("year", "2026")
    date_cond = f"AND match_date >= '{year}-01-01' AND match_date < '{int(year)+1}-01-01'" if year != "all" else ""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.total_passes) as tp, SUM(m.accurate_passes) as ap,
               AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='M' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND tp>=50
        ORDER BY (CAST(ap AS REAL)/tp) DESC LIMIT 25
    """).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"], "mins": r["mins"],
        "total_passes": r["tp"] or 0, "accurate_passes": r["ap"] or 0,
        "pass_acc": round((r["ap"] or 0) / r["tp"] * 100, 1) if r["tp"] else 0,
        "passes_p90": round((r["tp"] or 0) / r["mins"] * 90, 1) if r["mins"] else 0,
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows])


@app.route("/api/insights/defender-score")
def insights_defender_score():
    year = request.args.get("year", "2026")
    date_cond = f"AND match_date >= '{year}-01-01' AND match_date < '{int(year)+1}-01-01'" if year != "all" else ""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.tackles) as tkl, SUM(COALESCE(m.interceptions,0)) as intc,
               SUM(m.clearances) as clr, SUM(m.aerial_won) as aer,
               SUM(m.duel_won) as duel, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='D' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY (tkl + intc*1.5 + clr + aer + duel) / mins DESC LIMIT 25
    """).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"], "mins": r["mins"],
        "tackles": r["tkl"] or 0, "interceptions": r["intc"] or 0,
        "clearances": r["clr"] or 0, "aerial_won": r["aer"] or 0,
        "duel_won": r["duel"] or 0,
        "def_score": round(
            ((r["tkl"] or 0) + (r["intc"] or 0)*1.5 + (r["clr"] or 0)
             + (r["aer"] or 0) + (r["duel"] or 0)) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
