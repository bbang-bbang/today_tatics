// prediction.js — 경기 예측 보고서 + 다음 경기 일정

(function () {
    const section   = document.getElementById("prediction-section");
    const report    = document.getElementById("prediction-report");
    const closeBtn  = document.getElementById("prediction-close");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => section.classList.add("hidden"));
    }

    // ── 리그 탭 전환 ─────────────────────────────────────
    document.querySelectorAll(".league-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".league-tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".league-tab-panel").forEach(p => p.classList.remove("active"));
            btn.classList.add("active");
            const league = btn.dataset.league;
            document.getElementById(`${league}-schedule-banner-wrap`).classList.add("active");
            if (league === "k1" && !k1Loaded) loadScheduleK1();
        });
    });

    // ── 라운드 일정 (페이지 로드 시 자동) ──────────────────
    let scheduleCache = null;
    let roundsCache   = null;
    let activeRound   = null;

    let k1ScheduleCache = null;
    let k1RoundsCache   = null;
    let k1ActiveRound   = null;
    let k1Loaded        = false;

    function loadSchedule() {
        Promise.all([
            fetch("/api/k2/schedule").then(r => r.json()),
            fetch("/api/k2/rounds").then(r => r.json()),
        ]).then(([sched, rounds]) => {
            scheduleCache = sched;
            roundsCache   = rounds;
            activeRound   = rounds.current_round;
            renderRoundsBanner(rounds, sched, "k2");
        }).catch(() => {});
    }

    function loadScheduleK1() {
        k1Loaded = true;
        Promise.all([
            fetch("/api/k1/schedule").then(r => r.json()),
            fetch("/api/k1/rounds").then(r => r.json()),
        ]).then(([sched, rounds]) => {
            k1ScheduleCache = sched;
            k1RoundsCache   = rounds;
            k1ActiveRound   = rounds.current_round;
            renderRoundsBanner(rounds, sched, "k1");
        }).catch(() => {});
    }

    // ── 시즌 시뮬레이션 (lazy, 리그별 캐시) ─────────────────
    const _seasonSimCache = {};
    function loadSeasonSim(league) {
        const key = (league || "k2").toLowerCase();
        if (_seasonSimCache[key]) return Promise.resolve(_seasonSimCache[key]);
        return fetch(`/api/season-simulation?league=${key}&iter=10000`)
            .then(r => r.json())
            .then(d => { _seasonSimCache[key] = d; return d; })
            .catch(() => null);
    }
    function seasonSimHtml(d) {
        if (!d || !d.ready || !d.teams) return `<div class="sim-empty">데이터 없음</div>`;
        const top = d.teams;
        const maxWin = Math.max(...top.map(t => t.win_pct), 1);
        return `
        <div class="season-sim-body">
            <div class="ssb-header">
                <span class="ssb-meta">잔여 ${d.remaining_games}경기 · ${d.iter.toLocaleString()}회 시뮬</span>
                <span class="ssb-zone">🏆 ${d.top_zone_label} · 🔻 ${d.rel_zone_label}</span>
            </div>
            <div class="ssb-table">
                <div class="ssb-row ssb-head">
                    <span class="sst-rank">순위</span>
                    <span class="sst-team">팀</span>
                    <span class="sst-pts">현재</span>
                    <span class="sst-bar">우승확률</span>
                    <span class="sst-pct">우승</span>
                    <span class="sst-pct">TOP</span>
                    <span class="sst-pct">강등</span>
                </div>
                ${top.map((t, i) => {
                    const winColor = t.win_pct > 30 ? "#facc15" : t.win_pct > 5 ? "#7bed9f" : "#4ea4f8";
                    const relColor = t.rel_pct > 30 ? "#f87171" : t.rel_pct > 5 ? "#fda4af" : "#6a8aa8";
                    return `<div class="ssb-row">
                        <span class="sst-rank">${i+1}</span>
                        <span class="sst-team">${t.name}</span>
                        <span class="sst-pts">${t.current_pts}pt (${t.current_played}경기)</span>
                        <span class="sst-bar"><span class="sst-bar-fill" style="width:${(t.win_pct/maxWin*100).toFixed(0)}%;background:${winColor}"></span></span>
                        <span class="sst-pct" style="color:${winColor};font-weight:${t.win_pct>0?700:400}">${t.win_pct}%</span>
                        <span class="sst-pct">${t.top_pct}%</span>
                        <span class="sst-pct" style="color:${relColor};font-weight:${t.rel_pct>10?700:400}">${t.rel_pct}%</span>
                    </div>`;
                }).join("")}
            </div>
        </div>`;
    }
    function attachSeasonSimToggle(wrap, league) {
        const btn  = wrap.querySelector(`.season-sim-toggle`);
        const body = wrap.querySelector(`.season-sim-container`);
        if (!btn || !body) return;
        btn.addEventListener("click", () => {
            const isOpen = body.classList.toggle("open");
            btn.textContent = isOpen ? "▼ 시즌 시뮬레이션 닫기" : "🎲 시즌 시뮬레이션 (우승/TOP/강등 확률)";
            if (isOpen && !body.dataset.loaded) {
                body.innerHTML = `<div class="sim-empty">시뮬레이션 중... (~3초)</div>`;
                loadSeasonSim(league).then(d => {
                    body.innerHTML = seasonSimHtml(d);
                    body.dataset.loaded = "1";
                });
            }
        });
    }

    function renderRoundsBanner(roundsData, schedData, league) {
        const wrapId = league === "k1" ? "k1-schedule-banner-wrap" : "k2-schedule-banner-wrap";
        const wrap = document.getElementById(wrapId);
        if (!wrap) return;

        const rounds = roundsData.rounds || [];
        if (!rounds.length) return;

        const curRound = league === "k1" ? k1ActiveRound : activeRound;
        const leagueLabel = league === "k1" ? "K리그1 2026" : "K리그2 2026";

        wrap.innerHTML = `
        <div class="ksb-banner" id="${league}-schedule-banner">
            <div class="ksb-header">
                <span class="ksb-title">${leagueLabel}</span>
                <span class="ksb-sub">라운드 선택 후 경기 클릭 → 예측 보고서</span>
            </div>
            <div class="ksb-round-tabs" id="${league}-round-tabs">
                ${rounds.map(r => `
                <button class="ksb-round-btn${r.round === curRound ? " active" : ""}" data-round="${r.round}" data-league="${league}">
                    R${r.round}
                    <span class="ksb-round-done">${r.finished}/${r.total}</span>
                </button>`).join("")}
            </div>
            <div class="ksb-list" id="${league}-game-list"></div>
            <button class="season-sim-toggle">🎲 시즌 시뮬레이션 (우승/TOP/강등 확률)</button>
            <div class="season-sim-container"></div>
        </div>`;

        renderRoundGames(curRound, rounds, league);
        attachSeasonSimToggle(wrap, league);

        wrap.querySelectorAll(".ksb-round-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                wrap.querySelectorAll(".ksb-round-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const rnd = parseInt(btn.dataset.round);
                if (league === "k1") k1ActiveRound = rnd;
                else activeRound = rnd;
                renderRoundGames(rnd, rounds, league);
            });
        });
    }

    function renderRoundGames(roundNum, rounds, league) {
        const list = document.getElementById(`${league}-game-list`);
        if (!list) return;
        const rndData = rounds.find(r => r.round === roundNum);
        if (!rndData) return;

        list.innerHTML = rndData.games.map(g => {
            const finished = g.finished;
            const scoreHtml = finished
                ? `<span class="ksb-score">${g.home_score} - ${g.away_score}</span>`
                : `<span class="ksb-time">${g.time}</span>`;
            const canPredict = !finished && g.home_id && g.away_id && g.home_id !== "null" && g.away_id !== "null";
            const finishedCls = finished ? " ksb-item-done" : (canPredict ? " ksb-item-upcoming" : "");
            return `
            <div class="ksb-item${finishedCls}"
                 data-home="${g.home_id}" data-away="${g.away_id}"
                 data-finished="${finished}">
                <span class="ksb-date">${g.date.replace(/\./g,"/").slice(5)}</span>
                <span class="ksb-match">
                    <span class="ksb-team ksb-home">${g.home_short}</span>
                    ${scoreHtml}
                    <span class="ksb-team ksb-away">${g.away_short}</span>
                </span>
                <span class="ksb-venue">${g.venue}</span>
                ${!finished && canPredict ? `<span class="ksb-pred-hint">예측 →</span>` : ""}
            </div>`;
        }).join("");

        list.querySelectorAll(".ksb-item").forEach(item => {
            item.addEventListener("click", () => {
                const homeId = item.dataset.home;
                const awayId = item.dataset.away;
                if (!homeId || !awayId || homeId === "null" || awayId === "null") return;
                section.classList.remove("hidden");
                loadPrediction(homeId, awayId);
                section.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    // ── 팀 선택 이벤트 수신 (기존 info.js 연동) ─────────────
    document.addEventListener("teamsSelected", (e) => {
        if (!e.detail || e.detail.home.id === e.detail.away.id) {
            section.classList.add("hidden");
            return;
        }
        section.classList.remove("hidden");
        loadPrediction(e.detail.home.id, e.detail.away.id);
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    let _playerStatusCache = null;
    function loadPlayerStatus() {
        if (_playerStatusCache) return Promise.resolve(_playerStatusCache);
        return fetch("/api/player-status").then(r => r.json()).then(d => { _playerStatusCache = d; return d; }).catch(() => ({}));
    }

    // 백테스트 정확도 — 리그별 캐시
    const _backtestCache = {};
    function loadBacktest(league) {
        const key = (league || "k2").toLowerCase();
        if (_backtestCache[key]) return Promise.resolve(_backtestCache[key]);
        return fetch(`/api/prediction-backtest?league=${key}&year=2026`)
            .then(r => r.json())
            .then(d => { _backtestCache[key] = d; return d; })
            .catch(() => null);
    }
    function backtestBannerHtml(d) {
        if (!d || !d.ready) return "";
        const leagueLabel = d.league === "K1" ? "K리그1 2026" : "K리그2 2026";
        return `<div class="pred-backtest">
            <span class="pbt-label">📊 ${leagueLabel} 모델 정확도</span>
            <span class="pbt-stat"><span class="pbt-v">${d.hit_1x2_pct}%</span><span class="pbt-k">1X2</span></span>
            <span class="pbt-stat"><span class="pbt-v">${d.exact_score_pct}%</span><span class="pbt-k">정확 스코어</span></span>
            <span class="pbt-stat"><span class="pbt-v">${d.top3_score_pct}%</span><span class="pbt-k">TOP3</span></span>
            <span class="pbt-stat"><span class="pbt-v">${d.brier_score}</span><span class="pbt-k">Brier</span></span>
            <span class="pbt-sub">${d.n_total}경기 rolling · 무작위 ${d.baseline_random}%</span>
            ${backtestChartHtml(d.per_round)}
        </div>`;
    }

    // 라운드별 누적 적중률 SVG 라인차트
    function backtestChartHtml(perRound) {
        if (!perRound || perRound.length < 2) return "";
        const W = 360, H = 80, PAD_L = 28, PAD_R = 10, PAD_T = 10, PAD_B = 20;
        const innerW = W - PAD_L - PAD_R;
        const innerH = H - PAD_T - PAD_B;
        const rounds = perRound.map(r => r.round);
        const rMin = rounds[0], rMax = rounds[rounds.length - 1];
        const xAt = r => rounds.length === 1 ? PAD_L + innerW / 2 : PAD_L + ((r - rMin) / (rMax - rMin)) * innerW;
        const yAt = pct => PAD_T + (1 - pct / 100) * innerH;

        // 누적선 좌표
        const cumPts = perRound.map(r => `${xAt(r.round).toFixed(1)},${yAt(r.cum_pct || 0).toFixed(1)}`).join(" ");
        // 라운드별 점
        const dots = perRound.map(r => {
            const cx = xAt(r.round).toFixed(1);
            const cy = yAt(r.round_pct || 0).toFixed(1);
            return `<circle cx="${cx}" cy="${cy}" r="3" fill="#facc15" stroke="#0d1530" stroke-width="1"><title>R${r.round} · 라운드 ${r.round_pct}% (${r.hit}/${r.total})</title></circle>`;
        }).join("");
        // 33% 무작위 기준선
        const baselineY = yAt(33.3).toFixed(1);
        // y축 라벨
        const yLabels = [0, 50, 100].map(v => `
            <text x="${PAD_L - 4}" y="${yAt(v) + 3}" font-size="8" fill="#6a8aa8" text-anchor="end">${v}</text>
            <line x1="${PAD_L}" y1="${yAt(v)}" x2="${W - PAD_R}" y2="${yAt(v)}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
        `).join("");
        // x축 라벨
        const xLabels = perRound.map(r => `<text x="${xAt(r.round)}" y="${H - PAD_B + 11}" font-size="8" fill="#6a8aa8" text-anchor="middle">R${r.round}</text>`).join("");

        return `
        <div class="pred-backtest-chart">
            <div class="pbc-title">라운드별 적중률</div>
            <svg class="pbc-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
                ${yLabels}
                <line x1="${PAD_L}" y1="${baselineY}" x2="${W - PAD_R}" y2="${baselineY}" stroke="#f87171" stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>
                <text x="${W - PAD_R - 2}" y="${baselineY - 2}" font-size="7" fill="#f87171" text-anchor="end">33% (무작위)</text>
                <polyline points="${cumPts}" fill="none" stroke="#4ea4f8" stroke-width="2" stroke-linejoin="round"/>
                ${dots}
                ${xLabels}
            </svg>
            <div class="pbc-legend">
                <span class="pbc-lg"><span class="pbc-lg-line" style="background:#4ea4f8"></span>누적 적중률</span>
                <span class="pbc-lg"><span class="pbc-lg-dot" style="background:#facc15"></span>라운드별</span>
            </div>
        </div>`;
    }
    function statusBadgeHtml(teamId) {
        if (!_playerStatusCache) return "";
        const entries = Object.values(_playerStatusCache).filter(s => s.teamId === teamId && s.status !== "available");
        if (!entries.length) return "";
        const icons = { injured: "🏥", suspended: "🟥", doubtful: "🔶" };
        const labels = { injured: "부상", suspended: "출전정지", doubtful: "출전 의문" };
        return `<div class="pred-status">
            <div class="pred-status-title">부상/결장</div>
            ${entries.map(s => `<div class="pred-status-row">
                <span class="ps-icon">${icons[s.status] || "❓"}</span>
                <span class="ps-name">${s.name}</span>
                <span class="ps-label">${labels[s.status] || s.status}</span>
                ${s.returnDate ? `<span class="ps-return">~${s.returnDate}</span>` : ""}
                ${s.note ? `<span class="ps-note">${s.note}</span>` : ""}
            </div>`).join("")}
        </div>`;
    }

    function _inferLeague(homeId, awayId) {
        // teamId → league 매핑: K1 스케줄 캐시에 있으면 k1, 아니면 k2
        const scan = (cache) => cache && (cache.upcoming || []).some(
            g => g.home_id === homeId || g.away_id === homeId || g.home_id === awayId || g.away_id === awayId
        );
        if (scan(k1ScheduleCache)) return "k1";
        return "k2";
    }

    function loadPrediction(homeId, awayId) {
        report.innerHTML = `<div class="pred-loading">분석 중...</div>`;
        const league = _inferLeague(homeId, awayId);
        Promise.all([
            fetch(`/api/match-prediction?homeTeam=${homeId}&awayTeam=${awayId}`).then(r => r.json()),
            loadPlayerStatus(),
            loadBacktest(league),
            fetch(`/api/predicted-lineup?teamId=${homeId}`).then(r => r.json()).catch(() => null),
            fetch(`/api/predicted-lineup?teamId=${awayId}`).then(r => r.json()).catch(() => null),
        ])
            .then(([data, _ps, bt, hLineup, aLineup]) => render(data, homeId, awayId, bt, hLineup, aLineup))
            .catch(() => { report.innerHTML = ""; });
    }

    // ── 예상 라인업 카드 ───────────────────────────────────
    function lineupCardHtml(d, label, colorClass) {
        if (!d || !d.ready || !d.starters || !d.starters.length) return "";
        const POS_COLORS = { G: "#facc15", D: "#4ea4f8", M: "#7bed9f", F: "#f87171" };
        const POS_LABEL  = { G: "골", D: "수", M: "미", F: "공" };
        const grouped = { G: [], D: [], M: [], F: [], "?": [] };
        for (const s of d.starters) (grouped[s.position] || grouped["?"]).push(s);
        const renderRow = (s) => {
            const inj = s.injury_status;
            const injIcon = inj === "injured" ? "🏥" : inj === "suspended" ? "🟥" : inj === "doubtful" ? "🔶" : "";
            return `<div class="lu-player${inj ? " lu-injured" : ""}">
                <span class="lu-pos" style="background:${POS_COLORS[s.position] || "#666"}33;color:${POS_COLORS[s.position] || "#aaa"}">${POS_LABEL[s.position] || "?"}</span>
                <span class="lu-num">#${s.shirt_number || "-"}</span>
                <span class="lu-name">${s.name}${injIcon ? ` <span class="lu-inj-icon">${injIcon}</span>` : ""}</span>
                ${s.rating ? `<span class="lu-rating">${s.rating}</span>` : ""}
            </div>`;
        };
        const formationStr = d.formation ? `<span class="lu-formation">${d.formation}</span>` : "";
        const outHtml = (d.out_players && d.out_players.length) ? `
            <div class="lu-out">
                <div class="lu-out-title">⚠️ 결장 예정 (${d.out_players.length}명)</div>
                ${d.out_players.map(o => `<div class="lu-out-row">${o.name} (${o.status}${o.return_date ? ` ~${o.return_date}` : ""})</div>`).join("")}
            </div>` : "";
        return `<div class="pred-lineup ${colorClass || ""}">
            <div class="lu-header">
                <span class="lu-label">예상 라인업 — ${label}</span>
                ${formationStr}
            </div>
            <div class="lu-section"><div class="lu-section-title">GK</div>${grouped.G.map(renderRow).join("")}</div>
            <div class="lu-section"><div class="lu-section-title">DF</div>${grouped.D.map(renderRow).join("")}</div>
            <div class="lu-section"><div class="lu-section-title">MF</div>${grouped.M.map(renderRow).join("")}</div>
            <div class="lu-section"><div class="lu-section-title">FW</div>${grouped.F.map(renderRow).join("")}</div>
            <div class="lu-based">기준: ${d.based_on_date} 경기</div>
            ${outHtml}
        </div>`;
    }

    // ── 순위 뱃지 ────────────────────────────────────────────
    function standingBadge(st) {
        if (!st) return "";
        return `<div class="pred-standing">
            <span class="pst-rank">${st.rank}위</span>
            <span class="pst-pts">${st.pts}pts</span>
            <span class="pst-record">${st.w}승 ${st.d}무 ${st.l}패</span>
            <span class="pst-gd" style="color:${st.gd>0?"#4ade80":st.gd<0?"#f87171":"#9ab"}">GD ${st.gd>0?"+":""}${st.gd}</span>
        </div>`;
    }

    // ── 예상 스코어 (포아송 λ 우선, fallback = 평균 득실) ───────
    function predictedScore(home, away, predHome, poisson) {
        if (poisson && typeof poisson.lambda_home === "number" && typeof poisson.lambda_away === "number") {
            return {
                home: poisson.lambda_home.toFixed(1),
                away: poisson.lambda_away.toFixed(1),
            };
        }
        const hAvg = home.avg_gf || 0;
        const aAvg = away.avg_gf || 0;
        const hGA  = home.avg_ga || 0;
        const aGA  = away.avg_ga || 0;
        const expH = Math.max(0, (hAvg + aGA) / 2);
        const expA = Math.max(0, (aAvg + hGA) / 2);
        const bias = (predHome - 50) / 100;
        const adjH = Math.round((expH + bias * 0.5) * 10) / 10;
        const adjA = Math.round((expA - bias * 0.5) * 10) / 10;
        return { home: Math.max(0, adjH).toFixed(1), away: Math.max(0, adjA).toFixed(1) };
    }

    // ── 핵심 매치업 ───────────────────────────────────────────
    function keyMatchups(home, away) {
        const items = [];
        const hGF = home.avg_gf, aGF = away.avg_gf;
        const hGA = home.avg_ga, aGA = away.avg_ga;
        if (hGF && aGA) {
            const advantage = hGF - aGA;
            if (Math.abs(advantage) >= 0.3) {
                items.push(advantage > 0
                    ? `${home.name} 공격(${hGF.toFixed(1)}) > ${away.name} 수비(${aGA.toFixed(1)})`
                    : `${away.name} 수비(${aGA.toFixed(1)}) > ${home.name} 공격(${hGF.toFixed(1)})`);
            }
        }
        if (aGF && hGA) {
            const advantage = aGF - hGA;
            if (Math.abs(advantage) >= 0.3) {
                items.push(advantage > 0
                    ? `${away.name} 공격(${aGF.toFixed(1)}) > ${home.name} 수비(${hGA.toFixed(1)})`
                    : `${home.name} 수비(${hGA.toFixed(1)}) > ${away.name} 공격(${aGF.toFixed(1)})`);
            }
        }
        return items;
    }

    // ── 신뢰도 배지 ─────────────────────────────────────────
    function confidenceBadge(conf) {
        if (!conf) return "";
        const meta = {
            high: { icon: "🟢", label: "신뢰도 높음", color: "#7bed9f" },
            med:  { icon: "🟡", label: "신뢰도 보통", color: "#facc15" },
            low:  { icon: "🔴", label: "신뢰도 낮음", color: "#f87171" },
        };
        const m = meta[conf.level] || meta.low;
        return `<div class="pred-confidence" style="border-color:${m.color}55">
            <span class="pc-icon">${m.icon}</span>
            <span class="pc-label" style="color:${m.color}">${m.label}</span>
            <span class="pc-sub">H2H ${conf.h2h_games}경기 · 시즌 ${conf.season_games}경기</span>
        </div>`;
    }

    // ── 스코어 매트릭스 히트맵 (6x6) ───────────────────────
    function scoreMatrixHtml(matrix, topScores) {
        if (!matrix || !matrix.length) return "";
        // 최대값으로 색 강도 정규화
        let maxP = 0;
        for (const row of matrix) for (const v of row) if (v > maxP) maxP = v;
        const N = matrix.length;
        const topSet = new Set((topScores || []).slice(0, 3).map(s => `${s.home}-${s.away}`));
        const cells = [];
        // 헤더
        cells.push(`<div class="psm-cell psm-corner"></div>`);
        for (let j = 0; j < N; j++) {
            cells.push(`<div class="psm-cell psm-head psm-head-away">${j}${j===N-1?"+":""}</div>`);
        }
        for (let i = 0; i < N; i++) {
            cells.push(`<div class="psm-cell psm-head psm-head-home">${i}${i===N-1?"+":""}</div>`);
            for (let j = 0; j < N; j++) {
                const p = matrix[i][j];
                const intensity = maxP ? p / maxP : 0;
                const diag = i === j;
                const homeWin = i > j;
                const base = diag ? "148,163,184" : homeWin ? "78,164,248" : "184,126,248";
                const bg = `rgba(${base}, ${Math.max(0.05, intensity).toFixed(2)})`;
                const isTop = topSet.has(`${i}-${j}`);
                cells.push(`<div class="psm-cell psm-val${isTop ? " psm-top" : ""}" style="background:${bg}" title="${i}-${j}: ${p.toFixed(1)}%">${p.toFixed(1)}</div>`);
            }
        }
        return `
        <div class="pred-score-matrix">
            <div class="psm-title">스코어 확률 매트릭스</div>
            <div class="psm-axis-label psm-axis-away">원정 →</div>
            <div class="psm-axis-label psm-axis-home">↓ 홈</div>
            <div class="psm-grid" style="grid-template-columns: repeat(${N+1}, 1fr)">
                ${cells.join("")}
            </div>
        </div>`;
    }

    // ── 상위 예측 스코어 ───────────────────────────────────
    function topScoresHtml(top) {
        if (!top || !top.length) return "";
        return `
        <div class="pred-top-scores">
            <div class="pts-title">유력 스코어 TOP 5</div>
            <div class="pts-list">
                ${top.map((s, i) => `
                <div class="pts-row${i === 0 ? " pts-best" : ""}">
                    <span class="pts-rank">${i+1}</span>
                    <span class="pts-score"><span class="pts-h">${s.home}</span>-<span class="pts-a">${s.away}</span></span>
                    <span class="pts-bar-wrap"><span class="pts-bar" style="width:${Math.min(100, s.pct*6)}%"></span></span>
                    <span class="pts-pct">${s.pct}%</span>
                </div>`).join("")}
            </div>
        </div>`;
    }

    // ── 부상자 영향 카드 ───────────────────────────────────
    function injuryCardHtml(inj, teamName, colorClass) {
        if (!inj || !inj.players || !inj.players.length) return "";
        const labels = { injured: "부상", suspended: "정지", doubtful: "의문" };
        const icons  = { injured: "🏥", suspended: "🟥", doubtful: "🔶" };
        return `
        <div class="pred-injury-impact ${colorClass || ""}">
            <div class="pii-header">
                <span class="pii-icon">🩹</span>
                <span class="pii-title">${teamName} 전력 손실</span>
                <span class="pii-loss">공격력 -${inj.xg_loss_pct || 0}%</span>
            </div>
            <div class="pii-list">
                ${inj.players.map(p => `
                <div class="pii-row">
                    <span class="pii-p-icon">${icons[p.status] || "❓"}</span>
                    <span class="pii-p-name">${p.name}</span>
                    <span class="pii-p-tag">${labels[p.status] || p.status}</span>
                    <span class="pii-p-stat">${p.goals}골 ${p.assists}A</span>
                    ${p.return_date ? `<span class="pii-p-ret">~${p.return_date}</span>` : ""}
                </div>`).join("")}
            </div>
        </div>`;
    }

    // ── 폼 트렌드 라인 (최근 10경기 누적 승점 SVG) ──────────
    function trendLineSvg(points, color) {
        if (!points || points.length < 2) return "";
        const W = 140, H = 36, PAD = 2;
        // 누적 승점
        let cum = 0;
        const cums = points.map(p => (cum += p));
        const maxCum = Math.max(...cums, 1);
        const coords = cums.map((v, i) => {
            const x = PAD + (i / (cums.length - 1)) * (W - PAD*2);
            const y = H - PAD - (v / maxCum) * (H - PAD*2);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(" ");
        return `<svg class="pred-trend-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
            <polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
            ${cums.map((v, i) => {
                const x = PAD + (i / (cums.length - 1)) * (W - PAD*2);
                const y = H - PAD - (v / maxCum) * (H - PAD*2);
                return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="1.8" fill="${color}"/>`;
            }).join("")}
        </svg>`;
    }

    function trendBlockHtml(points, label, color) {
        if (!points || !points.length) return "";
        const total = points.reduce((a, b) => a + b, 0);
        const maxPts = points.length * 3;
        const pct = maxPts ? Math.round(total / maxPts * 100) : 0;
        return `<div class="pred-trend-block">
            <div class="ptb-head"><span class="ptb-label">${label}</span><span class="ptb-pct">${total}/${maxPts}pt · ${pct}%</span></div>
            ${trendLineSvg(points, color)}
        </div>`;
    }

    // ── 휴식일 + 심판 인포 카드 ──────────────────────────
    function restRefereeCardHtml(home, away, referee) {
        const hr = home.rest_days, ar = away.rest_days;
        if (hr == null && ar == null && !referee) return "";

        const restColor = (d) => {
            if (d == null) return "#6a8aa8";
            if (d <= 3) return "#f87171";
            if (d <= 7) return "#7bed9f";
            if (d <= 14) return "#facc15";
            return "#fbbf24";
        };
        const restLabel = (d) => {
            if (d == null) return "—";
            if (d <= 3) return "🥱 연전";
            if (d <= 7) return "✅ 적정";
            if (d <= 14) return "⚡ 충분";
            return "💤 길음";
        };

        const refHtml = referee ? `
            <div class="rrc-ref">
                <div class="rrc-ref-head">
                    <span class="rrc-ref-icon">👨‍⚖️</span>
                    <span class="rrc-ref-name">${referee.name}</span>
                    <span class="rrc-ref-strict rrc-strict-${referee.strictness === '엄격' ? 'strict' : referee.strictness === '관대' ? 'lenient' : 'normal'}">${referee.strictness || '?'}</span>
                </div>
                <div class="rrc-ref-stats">
                    🟨 ${referee.yellow_per_game}/경기 · 🟥 ${referee.red_per_game}/경기 · 통산 ${referee.career_games}경기
                </div>
            </div>` : "";

        return `<div class="pred-rest-ref">
            <div class="rrc-rest">
                <div class="rrc-rest-block">
                    <div class="rrc-rest-label">${home.name} 휴식</div>
                    <div class="rrc-rest-val" style="color:${restColor(hr)}">${hr != null ? hr + '일' : '—'}</div>
                    <div class="rrc-rest-tag">${restLabel(hr)}</div>
                </div>
                <div class="rrc-rest-block">
                    <div class="rrc-rest-label">${away.name} 휴식</div>
                    <div class="rrc-rest-val" style="color:${restColor(ar)}">${ar != null ? ar + '일' : '—'}</div>
                    <div class="rrc-rest-tag">${restLabel(ar)}</div>
                </div>
            </div>
            ${refHtml}
        </div>`;
    }

    // ── 세트피스 매치업 카드 ──────────────────────────────
    function setpieceCardHtml(home, away) {
        const h = home.setpiece, a = away.setpiece;
        if (!h || !a) return "";
        if (!h.goals_total && !a.goals_total) return "";
        // 인사이트: 매치업 강/약점
        const insights = [];
        if (h.setpiece_pct !== null && a.setpiece_conceded_pct !== null) {
            if (h.setpiece_pct >= 20 && a.setpiece_conceded_pct >= 25) {
                insights.push(`⚡ ${home.name} 세트피스 강세 (${h.setpiece_pct}%) × ${away.name} 세트피스 수비 약점 (${a.setpiece_conceded_pct}%)`);
            }
        }
        if (a.setpiece_pct !== null && h.setpiece_conceded_pct !== null) {
            if (a.setpiece_pct >= 20 && h.setpiece_conceded_pct >= 25) {
                insights.push(`⚡ ${away.name} 세트피스 강세 (${a.setpiece_pct}%) × ${home.name} 세트피스 수비 약점 (${h.setpiece_conceded_pct}%)`);
            }
        }
        const teamCol = (name, sp, cls) => `
            <div class="sp-team ${cls}">
                <div class="sp-team-name">${name}</div>
                <div class="sp-stat">
                    <div class="sp-stat-bar">
                        <div class="sp-stat-bar-fill sp-off" style="width:${Math.min(100, (sp.setpiece_pct || 0) * 3)}%"></div>
                        <span class="sp-stat-val">${sp.setpiece_pct !== null ? sp.setpiece_pct + "%" : "—"}</span>
                    </div>
                    <div class="sp-stat-lbl">세트피스 득점 비율 <span class="sp-stat-sub">(${sp.setpiece_goals}/${sp.goals_total}골)</span></div>
                </div>
                <div class="sp-stat">
                    <div class="sp-stat-bar">
                        <div class="sp-stat-bar-fill sp-def" style="width:${Math.min(100, (sp.setpiece_conceded_pct || 0) * 3)}%"></div>
                        <span class="sp-stat-val">${sp.setpiece_conceded_pct !== null ? sp.setpiece_conceded_pct + "%" : "—"}</span>
                    </div>
                    <div class="sp-stat-lbl">세트피스 실점 비율 <span class="sp-stat-sub">(${sp.setpiece_conceded}/${sp.conceded_total}골)</span></div>
                </div>
                <div class="sp-split">
                    <span class="sp-tag sp-pk">PK ${sp.penalty_goals}</span>
                    <span class="sp-tag sp-fk">FK/세트 ${sp.freekick_goals}</span>
                </div>
            </div>`;
        return `
        <div class="pred-setpiece">
            <div class="sp-title">⚽ 세트피스 매치업</div>
            <div class="sp-grid">
                ${teamCol(home.name, h, "sp-home")}
                ${teamCol(away.name, a, "sp-away")}
            </div>
            ${insights.length ? `<div class="sp-insights">${insights.map(i => `<div class="sp-insight">${i}</div>`).join("")}</div>` : ""}
        </div>`;
    }

    // ── 골 타이밍 바 (전·후반) ──────────────────────────────
    function timingBarsHtml(timing, label) {
        if (!timing) return "";
        const tf = timing["for"]     || [0, 0];
        const ta = timing["against"] || [0, 0];
        const maxVal = Math.max(...tf, ...ta, 1);
        const bar = (v, c) => `<span class="ptm-bar" style="width:${(v/maxVal*100).toFixed(0)}%;background:${c}" title="${v}골"></span>`;
        return `<div class="pred-timing">
            <div class="ptm-head">${label} 골 타이밍</div>
            <div class="ptm-row"><span class="ptm-lbl">전반 득점</span>${bar(tf[0], "#4ea4f8")}<span class="ptm-v">${tf[0]}</span></div>
            <div class="ptm-row"><span class="ptm-lbl">후반 득점</span>${bar(tf[1], "#4ea4f8")}<span class="ptm-v">${tf[1]}</span></div>
            <div class="ptm-row"><span class="ptm-lbl">전반 실점</span>${bar(ta[0], "#f87171")}<span class="ptm-v">${ta[0]}</span></div>
            <div class="ptm-row"><span class="ptm-lbl">후반 실점</span>${bar(ta[1], "#f87171")}<span class="ptm-v">${ta[1]}</span></div>
        </div>`;
    }

    // ── 렌더링 ───────────────────────────────────────────────
    function render(d, homeId, awayId, backtest, hLineup, aLineup) {
        const { home, away, h2h, prediction } = d;
        const MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const nowMonth = new Date().getMonth();
        const score = predictedScore(home, away, prediction.home, d.poisson);
        const matchups = keyMatchups(home, away);

        // 다음 경기 배너에서 이 매치의 정보 가져오기 (K1/K2 모두 참조)
        let nextInfo = null;
        for (const cache of [scheduleCache, k1ScheduleCache]) {
            if (!cache) continue;
            nextInfo = (cache.upcoming || []).find(
                g => g.home_id === homeId && g.away_id === awayId
            );
            if (nextInfo) break;
        }

        const homeInj = (d.injuries || {}).home;
        const awayInj = (d.injuries || {}).away;

        report.innerHTML = `
        ${nextInfo ? `
        <div class="pred-match-header">
            <span class="pmh-round">R${nextInfo.round || "-"}</span>
            <span class="pmh-date">${nextInfo.date.replace(/\./g,"/")} ${nextInfo.time}</span>
            <span class="pmh-venue">${nextInfo.venue}</span>
        </div>` : ""}
        ${backtestBannerHtml(backtest)}

        <div class="pred-grid">

            <!-- 홈팀 -->
            <div class="pred-team-panel pred-home">
                <div class="pred-team-name">${home.name}</div>
                ${standingBadge(home.standing)}
                <div class="pred-badges">${formBadges(home.form)}</div>
                ${trendBlockHtml(home.form_points, "최근 10경기 승점", "#4ea4f8")}
                <div class="pred-stats-row">
                    <div class="pred-stat"><span class="ps-val">${home.home_wr.toFixed(0)}%</span><span class="ps-lbl">홈 승률</span></div>
                    <div class="pred-stat"><span class="ps-val">${home.avg_gf.toFixed(1)}</span><span class="ps-lbl">경기당 득점</span></div>
                    <div class="pred-stat"><span class="ps-val">${home.avg_ga.toFixed(1)}</span><span class="ps-lbl">경기당 실점</span></div>
                    ${home.month_wr !== null ? `<div class="pred-stat"><span class="ps-val" style="color:${monthColor(home.month_wr)}">${home.month_wr.toFixed(0)}%</span><span class="ps-lbl">${MONTHS[nowMonth]} 승률</span></div>` : ""}
                    ${typeof home.xg_for === "number" ? `<div class="pred-stat"><span class="ps-val">${home.xg_for.toFixed(2)}</span><span class="ps-lbl">경기당 xG</span></div>` : ""}
                </div>
                <div class="pred-notes">
                    ${home.notes.map(n => `<div class="pred-note">• ${n}</div>`).join("") || "<div class='pred-note pred-note-none'>특이사항 없음</div>"}
                </div>
                ${home.top_scorers.length ? `
                <div class="pred-scorers">
                    <div class="pred-scorers-title">이번 시즌 득점</div>
                    ${home.top_scorers.map(s => `<div class="pred-scorer-row"><span class="scorer-name scorer-link" data-player-id="${s.id}">${s.name}</span><span class="scorer-g">${s.goals}골</span></div>`).join("")}
                </div>` : ""}
                ${injuryCardHtml(homeInj, home.name, "pii-home")}
                ${statusBadgeHtml(homeId)}
            </div>

            <!-- 중앙 예측 -->
            <div class="pred-center">
                ${confidenceBadge(d.confidence)}
                <div class="pred-center-title">예상 결과</div>
                <div class="pred-prob-bar">
                    <div class="ppb-home" style="width:${prediction.home}%">${prediction.home}%</div>
                    <div class="ppb-draw" style="width:${prediction.draw}%">${prediction.draw}%</div>
                    <div class="ppb-away" style="width:${prediction.away}%">${prediction.away}%</div>
                </div>
                <div class="pred-prob-labels">
                    <span style="color:#4ea4f8">홈 승</span>
                    <span style="color:#888">무승부</span>
                    <span style="color:#b87ef8">원정 승</span>
                </div>

                <div class="pred-score-est">
                    <span class="pse-label">예상 스코어 (λ)</span>
                    <span class="pse-score">${score.home} - ${score.away}</span>
                </div>

                <div class="pred-h2h">
                    <div class="pred-h2h-title">직접 전적 (K2)</div>
                    ${h2h.games > 0 ? `
                    <div class="pred-h2h-row">
                        <span class="h2h-val" style="color:#4ea4f8">${h2h.home_w}승</span>
                        <span class="h2h-sep">${h2h.games}경기</span>
                        <span class="h2h-val" style="color:#b87ef8">${h2h.away_w}승</span>
                    </div>
                    <div class="pred-h2h-draw">${h2h.draw}무</div>
                    ` : `<div class="pred-note-none">전적 없음</div>`}
                </div>

                ${matchups.length ? `
                <div class="pred-matchup-keys">
                    <div class="pmk-title">핵심 지표</div>
                    ${matchups.map(m => `<div class="pmk-item">⚡ ${m}</div>`).join("")}
                </div>` : ""}
            </div>

            <!-- 원정팀 -->
            <div class="pred-team-panel pred-away">
                <div class="pred-team-name">${away.name}</div>
                ${standingBadge(away.standing)}
                <div class="pred-badges">${formBadges(away.form)}</div>
                ${trendBlockHtml(away.form_points, "최근 10경기 승점", "#b87ef8")}
                <div class="pred-stats-row">
                    <div class="pred-stat"><span class="ps-val">${away.away_wr.toFixed(0)}%</span><span class="ps-lbl">원정 승률</span></div>
                    <div class="pred-stat"><span class="ps-val">${away.avg_gf.toFixed(1)}</span><span class="ps-lbl">경기당 득점</span></div>
                    <div class="pred-stat"><span class="ps-val">${away.avg_ga.toFixed(1)}</span><span class="ps-lbl">경기당 실점</span></div>
                    ${away.month_wr !== null ? `<div class="pred-stat"><span class="ps-val" style="color:${monthColor(away.month_wr)}">${away.month_wr.toFixed(0)}%</span><span class="ps-lbl">${MONTHS[nowMonth]} 승률</span></div>` : ""}
                    ${typeof away.xg_for === "number" ? `<div class="pred-stat"><span class="ps-val">${away.xg_for.toFixed(2)}</span><span class="ps-lbl">경기당 xG</span></div>` : ""}
                </div>
                <div class="pred-notes">
                    ${away.notes.map(n => `<div class="pred-note">• ${n}</div>`).join("") || "<div class='pred-note pred-note-none'>특이사항 없음</div>"}
                </div>
                ${away.top_scorers.length ? `
                <div class="pred-scorers">
                    <div class="pred-scorers-title">이번 시즌 득점</div>
                    ${away.top_scorers.map(s => `<div class="pred-scorer-row"><span class="scorer-name scorer-link" data-player-id="${s.id}">${s.name}</span><span class="scorer-g">${s.goals}골</span></div>`).join("")}
                </div>` : ""}
                ${injuryCardHtml(awayInj, away.name, "pii-away")}
                ${statusBadgeHtml(awayId)}
            </div>

        </div>

        <!-- 확장 분석 섹션 -->
        <div class="pred-extras">
            <div class="pred-extras-row">
                ${scoreMatrixHtml(d.score_matrix, d.top_scores)}
                ${topScoresHtml(d.top_scores)}
            </div>
            <div class="pred-extras-row">
                ${timingBarsHtml(home.goal_timing, home.name)}
                ${timingBarsHtml(away.goal_timing, away.name)}
            </div>
            ${restRefereeCardHtml(home, away, d.referee)}
            ${setpieceCardHtml(home, away)}
            ${(hLineup && hLineup.ready) || (aLineup && aLineup.ready) ? `
            <div class="pred-extras-row pred-lineup-row">
                ${lineupCardHtml(hLineup, home.name, "pred-lineup-home")}
                ${lineupCardHtml(aLineup, away.name, "pred-lineup-away")}
            </div>` : ""}
        </div>`;

        // 선수 클릭 → 모달
        report.addEventListener("click", (e) => {
            const el = e.target.closest(".scorer-link");
            if (!el) return;
            const pid = parseInt(el.dataset.playerId);
            if (!pid) return;
            document.dispatchEvent(new CustomEvent("playerSelected", {
                detail: { playerId: pid, playerName: el.textContent.trim() }
            }));
        });
    }

    function formBadges(form) {
        return (form || []).map(r => {
            const cls = r === "W" ? "fb-w" : r === "D" ? "fb-d" : "fb-l";
            const lbl = r === "W" ? "승" : r === "D" ? "무" : "패";
            return `<span class="form-badge ${cls}">${lbl}</span>`;
        }).join("");
    }

    function monthColor(pct) {
        if (pct >= 55) return "#7bed9f";
        if (pct <= 30) return "#f87171";
        return "#c8d8f0";
    }

    // 페이지 로드 시 K2 일정 불러오기
    loadSchedule();
})();
