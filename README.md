# today_tatics

K리그 전술 분석 웹 애플리케이션 + 수원 삼성 블루윙즈 데이터 수집 파이프라인

---

## 데이터 수집 프로세스

### 개요

SofaScore에서 수원 삼성 블루윙즈(K리그2)의 경기별 선수 스탯, 히트맵, 경기장 정보를 수집하고, Open-Meteo API로 경기 당시 날씨를 보완하여 SQLite DB(`players.db`)에 저장한다.

```
SofaScore API ──▶ crawl_match_stats.py ──▶ match_player_stats 테이블
                ──▶ crawl_sofascore.py  ──▶ heatmap_points 테이블
SofaScore API ──▶ fetch_venues.py      ──▶ events 테이블 (경기장 좌표)
Open-Meteo    ──▶ fetch_weather.py     ──▶ match_player_stats 테이블 (날씨)
```

---

### 스크립트별 역할

#### `crawl_sofascore.py` — 선수 기본 정보 + 시즌 스탯 + 히트맵
- K리그1/2 전 팀 선수 정보, 시즌 누적 스탯, 경기별 히트맵 좌표 수집
- Playwright로 브라우저를 띄워 SofaScore 내부 API(`/api/v1/...`) 호출 (봇 탐지 우회)
- 저장 테이블: `teams`, `players`, `player_stats`, `heatmap_points`, `events`

#### `crawl_match_stats.py` — 경기별 선수 세부 스탯 (수원 삼성)
- `/api/v1/event/{event_id}/lineups` 엔드포인트에서 경기당 선수 스탯 수집
- 수원 삼성 선수만 필터링 (`teamId == 7652`)
- 이미 수집된 경기는 자동 스킵 (증분 수집)
- 저장 테이블: `match_player_stats`
- 수집 항목: rating, goals, assists, passes, crosses, dribbles, tackles, interceptions, clearances, duels, saves 등 35개 컬럼

#### `fetch_venues.py` — 경기장 정보 수집
- `/api/v1/event/{event_id}` 에서 홈팀 venue 정보 추출
- 경기는 항상 홈팀 경기장에서 열리므로 `homeTeam.venue` 사용
- SofaScore의 일부 좌표가 lat/lon 뒤집혀 있어 자동 교정 로직 포함
- 좌표 없는 경우 Nominatim(OpenStreetMap) 무료 지오코딩으로 보완
- 한국 좌표 유효 범위: 위도 33~39, 경도 124~132
- 저장 위치: `events.venue_name`, `venue_city`, `venue_lat`, `venue_lon`

#### `fetch_weather.py` — 경기 당시 날씨 수집
- Open-Meteo Archive API 사용 (무료, API 키 불필요)
- `events.venue_lat/lon` 기준으로 경기장 위치별 날씨 조회
- 경기 시작 시각(KST 시간 기준)의 시간별 날씨 데이터 추출
- 수집 항목: 기온(°C), 습도(%), 풍속(m/s), 날씨 코드/설명
- 저장 위치: `match_player_stats.temperature`, `humidity`, `wind_speed`, `weather_code`, `weather_desc`, `match_date`

#### `fetch_events.py` — 누락 이벤트 메타데이터 보완
- `heatmap_points`에는 있지만 `events` 테이블에 없는 event_id 탐지 후 보완
- `/api/v1/event/{event_id}` 호출로 홈/원정팀 정보 저장

#### `update_data.py` — 증분 업데이트 (통합 실행)
- 새 경기가 생겼을 때 4단계를 순서대로 자동 실행
  1. 신규 경기 선수 스탯 수집 (`match_player_stats`)
  2. 신규 경기 히트맵 수집 (`heatmap_points`)
  3. 신규 경기 경기장 정보 수집 (`events`)
  4. 신규 경기 날씨 수집 (`match_player_stats`)
- `match_player_stats`에는 있지만 `events` 테이블에 없는 orphan 경기 자동 복구

---

### DB 스키마 요약

| 테이블 | 주요 컬럼 | 비고 |
|---|---|---|
| `teams` | id, name, league, tournament_id, season_id | K리그1/2 전 팀 |
| `players` | id, team_id, name, position, nationality | 선수 기본 정보 |
| `player_stats` | player_id, tournament_id, season_id, rating, goals... | 시즌 누적 스탯 |
| `events` | id, home/away_team, date_ts, home/away_score, venue_* | 경기 메타데이터 + 경기장 |
| `heatmap_points` | player_id, event_id, x, y | 경기별 히트맵 좌표 |
| `match_player_stats` | event_id, player_id, is_home, result, match_date, temperature... | 경기별 선수 세부 스탯 + 날씨 |

#### `match_player_stats` 추가 필드
- `is_home`: 1=홈, 0=원정
- `result`: 2=승, 1=무, 0=패
- `match_date`: 경기 시작 일시 (KST)
- `temperature` / `humidity` / `wind_speed` / `weather_desc`: 경기장 기준 날씨

---

### 수집 현황 (2026-04-08 기준)

| 항목 | 수치 |
|---|---|
| 수원 삼성 수집 경기 수 | 82경기 (2024시즌 ~ 2026시즌) |
| 경기별 선수 스탯 레코드 | 533건 |
| 히트맵 좌표 | 158,432점 |
| 수집 경기장 수 | 18개 |
| 기온 범위 | -0.1°C ~ 34.7°C |

---

### 초기 실행 순서

```bash
# 1. 선수 기본 정보 + 히트맵 (전 팀, 시간 오래 걸림)
python crawl_sofascore.py

# 2. 수원 삼성 경기별 선수 세부 스탯
python crawl_match_stats.py

# 3. 경기장 좌표 수집
python fetch_venues.py

# 4. 날씨 수집
python fetch_weather.py
```

### 이후 정기 업데이트

```bash
# 새 경기가 생기면 이것만 실행
python update_data.py
```

---

### 주의사항

- SofaScore 일부 경기장의 `venueCoordinates`가 lat/lon 뒤집혀 있음 → `fetch_venues.py`에서 자동 교정
- `crawl_match_stats.py` 실행 시 Flask 서버(`main.py`)를 같이 종료하지 않도록 별도 터미널에서 실행 권장
- Nominatim API는 초당 1건 제한 → `fetch_venues.py`에서 1.1초 딜레이 적용
- Open-Meteo Archive API는 당일 데이터가 없을 수 있으므로 경기 후 1~2일 뒤 실행 권장
