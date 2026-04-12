# DEV LOG — today_tatics

코드 수정/추가 시 간략한 요약을 기록합니다.

---

## 2026-04-11

### 선수 활동량 지수 (proxy activity metrics) 추가 `20:50`

**배경**
Sofascore API는 이동거리·스프린트 등 GPS 기반 피지컬 데이터를 제공하지 않음.
대신 기존 `match_player_stats` 에서 수집 가능한 지표들로 활동량 대체 지수를 만들기로 결정.

**변경 파일**
- `main.py` — `/api/player-analytics` 응답에 `activity` 블록 추가
- `static/js/player_analytics.js` — 활동량 차트 섹션 및 `renderActivity()` 함수 추가
- `static/css/style.css` — `.pa-activity-wrap` 관련 스타일 추가

**지표 정의 (90분 환산)**

| 지표 | 설명 | 가중치 |
|------|------|--------|
| `touches_p90` | 90분당 터치 수 | 35% |
| `duels_p90` | 90분당 듀얼(공중+지상) 참여 횟수 | 25% |
| `passes_p90` | 90분당 패스 시도 수 | 20% |
| `def_p90` | 90분당 태클+인터셉트 합계 | 10% |
| `dribbles_p90` | 90분당 드리블 시도 수 | 10% |

- **종합 활동량 점수**: 각 지표의 리그 내 백분위를 가중 합산 (0~100)
- 기준: 최소 3경기, 150분 이상 출전 선수만 포함
- UI: 선수 분석 모달 내 막대 차트로 표시 (선수 값 vs 리그 평균 비교)

---

### 선수 개별 분석 모달 너비 확장 `21:00`

---

### 선수 개별 분석 패널 차트 레이아웃 개선 `21:13`

**문제**
`#player-report-section` 내부 폭(최대 428px)에서 `.pr-main-grid`가 `260px 1fr` 2열 구조여서
스탯 바 차트 열이 최소 52px까지 좁아져 차트가 뭉개지는 현상 발생.

**변경 파일**
- `static/css/style.css`
- `static/js/player_report.js`

**변경 내용**
- `.pr-main-grid`: `grid 260px 1fr` → `flex column` (기존 2열 → 세로 스택 제거)
- `.pr-radar-card`: 레이더(160px) + 스탯 리스트를 한 카드 안에서 가로 배치로 변경
- `#pr-radar-canvas`: `220px` → `160px` (좁은 패널에 맞게 축소)
- `#player-report-section` 폭: `clamp(300px, 28vw, 460px)` → `clamp(360px, 32vw, 520px)`

---

### 선수 개별 분석 패널 레이더 차트 추가 확장 `21:17`

**문제**
레이더 160px로 줄이고 가로 배치했지만 여전히 뭉개짐.

**변경 파일**
- `static/css/style.css`

**변경 내용**
- `#player-report-section` 폭: `clamp(360px, 32vw, 520px)` → `clamp(420px, 36vw, 600px)`
- `.pr-radar-card`: `flex row` → `grid 220px 1fr` (레이더 220px 고정, 스탯 나머지)
- `#pr-radar-canvas`: `160px` → `220px`

---

### 우측 선수 보고서 패널에 활동량 지수 추가 `21:29`

**변경 파일**
- `main.py` — `/api/player-stat-report` 응답에 `activity` 블록 추가
- `static/js/player_report.js` — 활동량 카드 + `renderActivity()` 함수 추가
- `static/css/style.css` — `.pr-activity-card`, `.pr-activity-score` 스타일 추가

**변경 내용**
- 레이더+스탯 카드 아래에 활동량 지수 카드 추가
- 종합 활동량 점수(0~100) 섹션 타이틀 우측에 표시
- 막대 차트: 터치·듀얼·패스·수비액션·드리블 (선수 vs 리그 평균)
- 백분위는 포지션 무관 리그 전체 기준

---

### 최근 경기 결과(W/D/L) 계산 버그 수정 `21:49`

**문제**
`match_player_stats.result` 컬럼에 `2` 같은 비정상 값이 저장돼 있어 매핑 `{1:"W", 0:"D", -1:"L"}`에서 누락 → `?` 표시.

**변경 파일**
- `main.py`

**변경 내용**
- `/api/player-stat-report`, `/api/player-analytics` 두 곳 모두 수정
- `result` 컬럼 사용 중단 → `home_score`, `away_score`, `is_home`으로 직접 계산
  - `is_home=1`: `home_score > away_score` → W, 동점 → D, 미만 → L
  - `is_home=0`: 반전 적용

---

### K2 다음 경기 예측 보고서 강화 `00:21`

**변경 파일**
- `main.py` — `/api/k2/schedule`, `/api/player-vs-teams` API 추가
- `static/js/prediction.js` — 전면 재작성
- `static/js/player_report.js` — 상대팀별 성적 섹션 추가
- `static/css/style.css` — 일정 배너·매치 헤더·예상 스코어 스타일 추가

**주요 내용**

1. **K2 다음 경기 일정 배너** — 페이지 로드 시 K리그 공식 API에서 K2 예정 경기 자동 수집, 카드 형태로 표시. 클릭하면 예측 보고서 오픈
2. **예측 보고서 강화** — 경기 라운드/시간/구장 헤더, 예상 스코어(팀 득/실점 평균 기반), 핵심 지표 매치업 섹션 추가
3. **선수 상대팀별 성적** — 우측 선수 보고서 패널에 팀별 평균 평점 막대차트 + 경기수/골/도움 테이블 추가. 평점 높을수록 좋은 상대

---

### K2 라운드별 경기 조회 + 지난 경기 결과 표시 `00:53`

**변경 파일**
- `main.py` — `/api/k2/rounds` API 추가, `_fetch_k2_all_games` / `_parse_k2_game` 헬퍼 추출
- `static/js/prediction.js` — 라운드 탭 UI (`renderRoundsBanner`, `renderRoundGames`) 추가
- `static/css/style.css` — 라운드 탭/경기 목록 스타일 추가

**주요 내용**
- K2 전 라운드(R1~현재) 탭 버튼으로 조회
- 완료 경기: 스코어 표시, 클릭 시 예측 보고서 열림
- 예정 경기: 시간 + "예측 →" 힌트 표시, 클릭 시 예측 보고서
- 현재 라운드(가장 최근 완료 라운드)를 기본 선택

---

### 레이아웃 반응형(responsive) 적용 `21:54`

**변경 파일**
- `static/css/style.css`

**변경 내용**
- `#main-area height: 600px` → `clamp(400px, 62vh, 820px)` (뷰포트 높이 기준 유동적)
- `#player-report-section height: 600px` → `clamp(400px, 62vh, 820px)` (동일 기준)
- `#board-report-wrap align-items: flex-start` → `stretch` (두 패널 높이 동기화)
- 캔버스 JS resize는 이미 `window.addEventListener("resize")` 연결돼 있어 자동 반영

**변경 파일**
- `static/css/style.css`

**변경 내용**
- `.pa-modal-body` 너비: `860px` → `1200px`
- `.pa-charts-row` 그리드: `220px 1fr` → `260px 1fr`, gap `16px` → `24px`
- `#chart-pa-radar` 최대 크기: `200px` → `240px`

---

## 2026-04-12

### K리그2 R7 경기 데이터 최신화 `23:01`

**작업 내용**
- `crawlers/crawl_kleague2_all.py` 실행 → R7 신규 경기 10개 스탯 수집 완료
- `crawlers/fetch_r7_heatmap.py` 신규 작성 → R7 8경기 315건 히트맵만 타겟 수집

**R7 수집 경기 (2026-04-11~12)**
- 부산 2-0 용인, 수원FC 2-2 대구, 파주 1-3 서울이랜드, 화성 1-0 전남
- 수원삼성 0-1 김포, 천안 2-2 청주, 성남 0-1 안산, 충남아산 1-1 김해

---

### K리그1 2026 데이터 세팅 `23:57`

**변경 파일**
- `crawlers/crawl_kleague1_2026.py` — 신규 작성 (시즌 엔드포인트 기반, tournament_id=410)
- `main.py` — K1 팀 코드 추가, `_fetch_k1_all_games`, `_parse_k1_game`, `/api/k1/schedule`, `/api/k1/rounds` 추가, `/api/match-prediction` K1/K2 분기 처리
- `static/js/prediction.js` — K1/K2 리그 탭 전환, `loadScheduleK1()`, `renderRoundsBanner`/`renderRoundGames` 공용화
- `templates/index.html` — 리그 탭 UI (`#league-schedule-wrap`, `.league-tab-btn`)
- `static/css/style.css` — 리그 탭 스타일, `.ksb-banner` 공통 클래스

**주요 내용**
1. K리그1 Sofascore 시즌 ID 88606 기반으로 2026 완료 경기 41개 수집
2. 경기 스탯·히트맵·날씨 수집 완료 (events 358개 → 2026 시즌 40경기 포함)
3. 예측 보고서: `league` 필드로 K1(tid=410)/K2(tid=777) 자동 분기
4. 웹 상단에 K리그2/K리그1 탭 버튼 추가 — K1 탭 클릭 시 Lazy 로드

---

