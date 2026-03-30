import json
import os
import uuid
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
    players_file = os.path.join(BASE_DIR, "kleague_players_2026.json")
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
    {"id": "ulsan",    "name": "울산 HD FC",        "short": "울산",   "league": "K1", "primary": "#1d5fa5", "secondary": "#ffffff", "accent": "#f2a900", "emblem": "emblem_K01.png", "border_home": "#fbf500", "border_away": "#6294c1"},
    {"id": "pohang",   "name": "포항 스틸러스",      "short": "포항",   "league": "K1", "primary": "#d41123", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K03.png", "border_home": "#191e24", "border_away": "#c70027"},
    {"id": "jeju",     "name": "제주 유나이티드",     "short": "제주",   "league": "K1", "primary": "#f47920", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K04.png", "border_home": "#121928", "border_away": "#121928"},
    {"id": "jeonbuk",  "name": "전북 현대 모터스",    "short": "전북",   "league": "K1", "primary": "#0a4436", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K05.png", "border_home": "#50b79a", "border_away": "#214b4f"},
    {"id": "fcseoul",  "name": "FC 서울",           "short": "서울",   "league": "K1", "primary": "#ef3744", "secondary": "#e8e7ef", "accent": "#ffd700", "emblem": "emblem_K09.png", "border_home": "#161516", "border_away": "#1f2125"},
    {"id": "daejeon",  "name": "대전 하나 시티즌",    "short": "대전",   "league": "K1", "primary": "#059a86", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K10.png", "border_home": "#771e34", "border_away": "#771e34"},
    {"id": "incheon",  "name": "인천 유나이티드",     "short": "인천",   "league": "K1", "primary": "#01a0fc", "secondary": "#bac6d4", "accent": "#ffffff", "emblem": "emblem_K18.png", "border_home": "#1f2521", "border_away": "#52b3f7"},
    {"id": "gangwon",  "name": "강원 FC",           "short": "강원",   "league": "K1", "primary": "#f55947", "secondary": "#e4e3f3", "accent": "#f47920", "emblem": "emblem_K21.png", "border_home": "#191e24", "border_away": "#191e24"},
    {"id": "gwangju",  "name": "광주 FC",           "short": "광주",   "league": "K1", "primary": "#f3ad02", "secondary": "#e4e3ed", "accent": "#000000", "emblem": "emblem_K22.png", "border_home": "#121621", "border_away": "#0f1b2f"},
    {"id": "bucheon",  "name": "부천 FC 1995",      "short": "부천",   "league": "K1", "primary": "#8e272b", "secondary": "#e1d8db", "accent": "#ffffff", "emblem": "emblem_K26.png", "border_home": "#170f0c", "border_away": "##a31822"},
    {"id": "anyang",   "name": "FC 안양",           "short": "안양",   "league": "K1", "primary": "#501b85", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K27.png", "border_home": "#ffffff", "border_away": "#501b85"},
    {"id": "gimcheon", "name": "김천 상무 FC",       "short": "김천",   "league": "K1", "primary": "#df242b", "secondary": "#eeeeee", "accent": "#ffffff", "emblem": "emblem_K35.png", "border_home": "#1d1e2e", "border_away": "#262d3d"},
    # K2 리그 (17팀)
    {"id": "suwon",    "name": "수원 삼성 블루윙즈",  "short": "수원",   "league": "K2", "primary": "#2553a5", "secondary": "#e7e6ec", "accent": "#c8102e", "emblem": "emblem_K02.png", "border_home": "#253052", "border_away": "#1f4183"},
    {"id": "busan",    "name": "부산 아이파크",      "short": "부산",   "league": "K2", "primary": "#b4050f", "secondary": "#b7c6ca", "accent": "#ffffff", "emblem": "emblem_K06.png", "border_home": "#120d11", "border_away": "#ffffff"},
    {"id": "jeonnam",  "name": "전남 드래곤즈",      "short": "전남",   "league": "K2", "primary": "#fbea09", "secondary": "#f0f0f2", "accent": "#000000", "emblem": "emblem_K07.png", "border_home": "#000000", "border_away": "#000000"},
    {"id": "seongnam", "name": "성남 FC",           "short": "성남",   "league": "K2", "primary": "#0e131b", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K08.png", "border_home": "#ffffff", "border_away": "#1a222d"},
    {"id": "daegu",    "name": "대구 FC",           "short": "대구",   "league": "K2", "primary": "#86c5e8", "secondary": "#e2e5ea", "accent": "#ffffff", "emblem": "emblem_K17.png", "border_home": "#e2e5ea", "border_away": "#86c5e8"},
    {"id": "gyeongnam","name": "경남 FC",           "short": "경남",   "league": "K2", "primary": "#ac101b", "secondary": "#d9d9d9", "accent": "#ffffff", "emblem": "emblem_K20.png", "border_home": "#121211", "border_away": "#121211"},
    {"id": "suwon_fc", "name": "수원 FC",           "short": "수원FC", "league": "K2", "primary": "#07306a", "secondary": "#cac3c3", "accent": "#ffffff", "emblem": "emblem_K29.png", "border_home": "#c9232e", "border_away": "#0b3972"},
    {"id": "seouland", "name": "서울 이랜드 FC",     "short": "이랜드", "league": "K2", "primary": "#030a1b", "secondary": "#d7dddd", "accent": "#1e3a8a", "emblem": "emblem_K31.png", "border_home": "#051025", "border_away": "#051025"},
    {"id": "ansan",    "name": "안산 그리너스 FC",    "short": "안산",   "league": "K2", "primary": "#0087a7", "secondary": "#eaedf4", "accent": "#ffd700", "emblem": "emblem_K32.png", "border_home": "#272c3d", "border_away": "#00677f"},
    {"id": "asan",     "name": "충남 아산 FC",       "short": "아산",   "league": "K2", "primary": "#12122c", "secondary": "#dfdfdf", "accent": "#e30613", "emblem": "emblem_K34.png", "border_home": "#d3a84c", "border_away": "#d3a84c"},
    {"id": "gimpo",    "name": "김포 FC",           "short": "김포",   "league": "K2", "primary": "#78bc36", "secondary": "#ebebeb", "accent": "#ffffff", "emblem": "emblem_K36.png", "border_home": "#0f2716", "border_away": "#0f2716"},
    {"id": "cheongju", "name": "충북 청주 FC",       "short": "청주",   "league": "K2", "primary": "#0d1026", "secondary": "#f0f0f0", "accent": "#ffffff", "emblem": "emblem_K37.png", "border_home": "#ae1d25", "border_away": "#0d1026"},    
    {"id": "cheonan",  "name": "천안 시티 FC",       "short": "천안",   "league": "K2", "primary": "#3e8fb3", "secondary": "#e2e2e2", "accent": "#e30613", "emblem": "emblem_K38.png", "border_home": "#201d1d", "border_away": "#3e8fb3"},
    {"id": "hwaseong", "name": "화성 FC",           "short": "화성",   "league": "K2", "primary": "#d45820", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K39.png", "border_home": "#fbf5f6", "border_away": "#090811"},
    {"id": "paju",     "name": "파주 시민축구단",     "short": "파주",   "league": "K2", "primary": "#042ba0", "secondary": "#f8f8f8", "accent": "#c8102e", "emblem": "emblem_K40.png", "border_home": "#d381a2", "border_away": "#d381a2"},
    {"id": "gimhae",   "name": "김해 FC",           "short": "김해",   "league": "K2", "primary": "#ac0d0e", "secondary": "#f3f3f3", "accent": "#ffd700", "emblem": "emblem_K41.png", "border_home": "#2c2c2c", "border_away": "#bba473"},
    {"id": "yongin",   "name": "용인 시민축구단",     "short": "용인",   "league": "K2", "primary": "#910c26", "secondary": "#dddddd", "accent": "#ffd700", "emblem": "emblem_K42.png", "border_home": "#54bfe1", "border_away": "#8c0e29"},
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
