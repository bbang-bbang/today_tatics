import re

# HTML 파일 읽기 (curl 출력 사용)
import sys
content = sys.stdin.read()

print(f"File size: {len(content)} bytes", file=sys.stderr)

pos_pattern = re.compile(r'<h1 class="club-playerPosition-title">(\w+)</h1>(.*?)(?=<h1 class="club-playerPosition-title">|\Z)', re.DOTALL)
player_name_pattern = re.compile(r'<li class="club-playerlist-nm-k">(\d+)\.\s*([^<]+)</li>')
player_info_pattern = re.compile(r'<li class="club-playerlist-nm-e">([^<]+)</li>')
team_id_pattern = re.compile(r"moveMainFrameMcPlayer\('[^']*','[^']*','([^']+)'\)")

players_by_team = {}

for pos_match in pos_pattern.finditer(content):
    pos = pos_match.group(1)
    section = pos_match.group(2)
    player_blocks = re.split(r'<div[^>]+class="club-playerlist-box"[^>]*>', section)
    for block in player_blocks[1:]:
        name_match = player_name_pattern.search(block)
        info_match = player_info_pattern.search(block)
        team_match = team_id_pattern.search(block)
        if name_match and info_match and team_match:
            number = name_match.group(1)
            name = name_match.group(2).strip()
            info = info_match.group(1).strip()
            team_id = team_match.group(1)
            date_match = re.search(r'(\d{4}/\d{2}/\d{2})', info)
            dob = date_match.group(1) if date_match else ''
            if team_id not in players_by_team:
                players_by_team[team_id] = []
            players_by_team[team_id].append({'number': number, 'name': name, 'position': pos, 'dob': dob})

for team_id, players in sorted(players_by_team.items()):
    print(f"\n{team_id} - {len(players)}명")
    for p in players:
        print(f"  {p['number']}. {p['name']} [{p['position']}] {p['dob']}")
