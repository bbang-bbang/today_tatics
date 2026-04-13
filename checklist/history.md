# Today Tactics 작업 히스토리
> 프로젝트: K리그 전술 분석 웹 애플리케이션
> 시작일: 2026-04-13

---

## 2026-04-13 17:30 | Critical 보안/안정성 수정 (main.py)

### SQL 인젝션 수정 (5건 → 0건)
- `_year_date_params()` 헬퍼 함수 추가: year 파라미터를 안전한 파라미터 바인딩(?)으로 변환
- 수정 대상 엔드포인트:
  - `/api/insights/top-performers` — F/M/D 3개 쿼리 (date_cond × 2, × 1, × 1)
  - `/api/insights/xg-efficiency` — date_cond × 2
  - `/api/insights/forward-goals` — date_cond × 2
  - `/api/insights/midfielder-pass` — date_cond × 1
  - `/api/insights/defender-score` — date_cond × 1
- 기존: f-string으로 year 값을 SQL에 직접 삽입 (`f"AND match_date >= '{year}-01-01'"`)
- 변경: `_year_date_params(year)` → `(sql_condition, params_tuple)` 반환, int 변환 실패 시 빈 조건

### fetchone()[0] 크래시 수정 (5건 → 0건)
- 빈 DB에서 `fetchone()` → `None` → `None[0]` TypeError 방어
- 수정 위치:
  - `/api/team-ranking` — latest_year (line ~533)
  - `/api/team-top-players` — latest_year (line ~605)
  - `/api/match-prediction` — latest_yr (line ~955)
  - `/api/team-goal-timing` — count_goals 내부 (line ~2181)
- 패턴: `row = cur.fetchone(); val = row[0] if row and row[0] else fallback`

### 경로 탈출(Path Traversal) 방어 (7건 → 0건)
- `_safe_path(base_dir, file_id)` 함수 추가:
  - 정규식 `^[a-zA-Z0-9_\-]+$`로 ID 문자 검증
  - `os.path.normpath()` 후 base_dir 프리픽스 확인
  - 위반 시 `None` 반환 → 400 Bad Request
- 적용 엔드포인트: saves CRUD(4건) + squads CRUD(3건)

---

## 2026-04-13 18:10 | 감독 관점 기능 추가 (이미지 내보내기 + 커스텀 포메이션)

### 이미지 내보내기 (PNG 다운로드)
- 변경 파일: `templates/index.html`, `static/js/app.js`, `static/css/style.css`
- 툴바에 "이미지 저장" 버튼 추가 (`#btn-export-png`)
- `canvas.toDataURL("image/png")`으로 현재 전술판 상태(선수+화살표+히트맵) 캡처
- 파일명 자동 생성: `tactics_{팀A}_vs_{팀B}_{날짜시간}.png`
- 코치진 카톡/이메일 공유 즉시 가능

### 커스텀 포메이션 저장
- 변경 파일: `templates/index.html`, `static/js/app.js`, `static/css/style.css`
- 포메이션 select 옆에 "+" 버튼 추가 (`.formation-save-btn`)
- 현재 필드 위 선수 좌표를 포메이션 프리셋으로 저장
- 반대편 팀은 좌표 자동 미러링 + 포지션 L↔R 교체
- localStorage에 영구 저장, 페이지 새로고침 후에도 유지
- select 드롭다운에 "내 포메이션" 그룹으로 표시 + 삭제 옵션

---

## 2026-04-13 19:05 | P2 팬 관점 기능 4건 구현

### #4 시즌 연도 + 리그 표시
- 변경 파일: `templates/index.html`, `static/js/app.js`, `static/css/style.css`
- 팀 배너에 `.team-slot-sub` 영역 추가 (팀명 아래)
- 팀 선택 시 리그 배지(K1/K2) + 시즌 연도(2026) 자동 표시
- 어떤 시즌/리그 데이터를 보고 있는지 혼동 방지

### #5 최근 폼 배지 (W/D/L)
- 변경 파일: `static/js/app.js`, `static/css/style.css`
- `updateTeamSub()` 함수: 팀 선택 시 `/api/results` 호출하여 최근 5경기 폼 표시
- W(초록)/D(황색)/L(적색) 미니 배지, hover 시 상대팀+스코어 tooltip
- 팀 배너에서 즉시 확인 가능

### #1 타팀 스탯 수집 확장 (크롤러)
- 변경 파일: `crawlers/crawl_match_stats.py`
- 하드코딩된 `TEAM_ID = 7652` (수원 삼성) 제거
- CLI 인자 추가: `--team {sofascore_id}` 또는 `--league {K1|K2|all}`
- K1 12팀 + K2 17팀 전체 ID 매핑 (`K1_TEAMS`, `K2_TEAMS` dict)
- `crawl_team()` 함수: 양팀 선수 모두 저장 (기존: 특정 팀만 필터)
- 사용법: `python crawl_match_stats.py --league K2` (K2 전팀 수집)

### #3 부상자/출전 가능 여부 관리 시스템
- 변경 파일: `main.py`, `static/js/prediction.js`, `static/css/style.css`
- `data/player_status.json` 기반 수동 관리 시스템
- API 3종: `GET/POST /api/player-status`, `DELETE /api/player-status/{id}`
- 상태: available(정상), injured(부상), suspended(출전정지), doubtful(출전의문)
- 경기 예측 모달에서 홈/어웨이 양팀 부상자 자동 표시
- 🏥 부상 / 🟥 출전정지 / 🔶 출전의문 아이콘 + 복귀 예정일 + 메모

---

## 2026-04-13 19:30 | 부상자 UI 관리 패널 (벤치 패널 통합)

### 벤치 패널 선수 상태 토글
- 변경 파일: `static/js/app.js`, `static/css/style.css`
- 벤치 선수 목록에 상태 토글 버튼 추가 (배치/미배치 모두)
- 클릭할 때마다 상태 순환: 정상 → 🏥부상 → 🟥출전정지 → 🔶출전의문 → 정상
- `/api/player-status` API 연동하여 서버에 즉시 저장
- 부상 선수: 반투명 + 취소선(빨강), 출전정지: 반투명 + 취소선(주황), 출전의문: 노랑
- 상태 캐시(`_statusCache`)로 벤치 렌더링 시 즉시 반영
- 경기 예측 모달에서도 자동 연동 (이전 작업에서 구현한 statusBadgeHtml)

---

## 2026-04-13 20:00 | 부상 정보 자동 수집 크롤러 + 한계 확인

### 크롤러 구현
- 신규 파일: `crawlers/fetch_injuries.py`
- SofaScore `/api/v1/team/{id}/players` → `injury` 객체 파싱
- injury 구조: `{reason, status("out"/"dayToDay"), expectedReturn, endDateTimestamp}`
- CLI: `--league K1/K2/all` 또는 `--team {sofascore_id}`
- 수동 등록(source 없음)과 자동 수집(source="sofascore") 병합, 수동이 우선

### SofaScore K리그 부상 데이터 한계 확인
- **K리그: injury 필드 미제공** (field 자체가 응답에 없음)
- J리그(카와사키 등)도 동일하게 미제공
- 유럽 빅리그(맨유 등)에서는 정상 동작 확인 (6명 부상자 수집 성공)
- **결론: K리그 부상 정보는 수동 관리가 유일한 현실적 방법**
- 크롤러는 향후 SofaScore 데이터 확대 시 즉시 활용 가능하도록 유지

---

## 2026-04-13 20:30 | P3 선수 + P5 코치 + QA + P4 분석가 일괄 구현

### P3 개인 강조 모드
- 변경 파일: `static/js/app.js`
- `state.highlightPlayerId` 추가, 선수 클릭 시 토글
- 강조된 선수: 금색 테두리 + 글로우, 나머지: globalAlpha 0.25로 반투명
- 빈 영역 클릭 시 강조 해제

### P3 롤 태그 표시
- 변경 파일: `templates/index.html`, `static/js/app.js`
- 툴바에 "롤 태그" 토글 버튼 추가 (`#btn-role-tag`)
- `state.showRoleTags` 토글 시 선수 원 위에 포지션 레이블(GK/CB/ST 등) 표시
- 이름 옆 중복 표시 자동 제거

### P5 전술 노트 첨부
- 변경 파일: `static/js/app.js`
- 화살표 더블클릭 → prompt로 노트 입력/수정/삭제
- `l.note` 필드로 저장/불러오기 직렬화 포함
- 화살표 중간점에 검정 배경 + 금색 텍스트로 노트 렌더링
- 곡선/꺾기 화살표도 중간점 자동 계산

### QA JS 에러 핸들링
- 변경 파일: `templates/index.html`, `static/js/info.js`
- 전역 `window.fetch` 래퍼: 4xx/5xx 로깅 + network error 로깅
- `unhandledrejection` 전역 핸들러 추가
- info.js `renderSameTeam`, `renderMatchup`, `renderSingle` 3개 함수에 try/catch 추가
- 에러 시 "데이터를 불러올 수 없습니다" 사용자 피드백 표시

### P4 DB 인덱스 생성
- 변경 파일: `main.py`
- `_ensure_indexes()` 함수: 앱 시작 시 8개 인덱스 자동 생성
- 추가 인덱스: events(tournament_id, date_ts), match_player_stats(position, team_player, match_date), heatmap_points(player_event), players(name_ko), goal_events(player_id)
- 기존 3개 + 신규 8개 = 총 11개 커스텀 인덱스 확인

---
