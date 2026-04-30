// prediction.js — 경기 예측 보고서 + 다음 경기 일정

(function () {
    // 팀 슬러그 → { p: primary, a: accent, e: emblem }
    const SLUG_COLOR = {
        "ulsan":    { p:"#1d5fa5", a:"#f2a900", e:"emblem_K01.png" },
        "pohang":   { p:"#d41123", a:"#ffffff", e:"emblem_K03.png" },
        "jeju":     { p:"#f47920", a:"#ffffff", e:"emblem_K04.png" },
        "jeonbuk":  { p:"#0a4436", a:"#ffd700", e:"emblem_K05.png" },
        "fcseoul":  { p:"#ef3744", a:"#ffd700", e:"emblem_K09.png" },
        "daejeon":  { p:"#059a86", a:"#ffffff", e:"emblem_K10.png" },
        "incheon":  { p:"#01a0fc", a:"#ffffff", e:"emblem_K18.png" },
        "gangwon":  { p:"#f55947", a:"#f47920", e:"emblem_K21.png" },
        "gwangju":  { p:"#f3ad02", a:"#000000", e:"emblem_K22.png" },
        "bucheon":  { p:"#8e272b", a:"#ffffff", e:"emblem_K26.png" },
        "anyang":   { p:"#501b85", a:"#ffd700", e:"emblem_K27.png" },
        "gimcheon": { p:"#df242b", a:"#ffffff", e:"emblem_K35.png" },
        "suwon":    { p:"#2553a5", a:"#c8102e", e:"emblem_K02.png" },
        "busan":    { p:"#b4050f", a:"#ffffff", e:"emblem_K06.png" },
        "jeonnam":  { p:"#fbea09", a:"#000000", e:"emblem_K07.png" },
        "seongnam": { p:"#0e131b", a:"#ffffff", e:"emblem_K08.png" },
        "daegu":    { p:"#86c5e8", a:"#ffffff", e:"emblem_K17.png" },
        "gyeongnam":{ p:"#ac101b", a:"#ffffff", e:"emblem_K20.png" },
        "suwon_fc": { p:"#07306a", a:"#ffffff", e:"emblem_K29.png" },
        "seouland": { p:"#030a1b", a:"#1e3a8a", e:"emblem_K31.png" },
        "ansan":    { p:"#0087a7", a:"#ffd700", e:"emblem_K32.png" },
        "asan":     { p:"#12122c", a:"#e30613", e:"emblem_K34.png" },
        "gimpo":    { p:"#78bc36", a:"#ffffff", e:"emblem_K36.png" },
        "cheongju": { p:"#0d1026", a:"#ffffff", e:"emblem_K37.png" },
        "cheonan":  { p:"#3e8fb3", a:"#e30613", e:"emblem_K38.png" },
        "hwaseong": { p:"#d45820", a:"#ffffff", e:"emblem_K39.png" },
        "paju":     { p:"#042ba0", a:"#c8102e", e:"emblem_K40.png" },
        "gimhae":   { p:"#ac0d0e", a:"#ffd700", e:"emblem_K41.png" },
        "yongin":   { p:"#910c26", a:"#ffd700", e:"emblem_K42.png" },
    };
    function tc(slug) { return SLUG_COLOR[slug] || { p:"#334", a:"#aaa", e:"" }; }

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
            if (league === "k2" && !k2Loaded) loadSchedule();
        });
    });

    // ── 라운드 일정 (페이지 로드 시 자동) ──────────────────
    let scheduleCache = null;
    let roundsCache   = null;
    let activeRound   = null;
    let k2Loaded      = false;

    let k1ScheduleCache = null;
    let k1RoundsCache   = null;
    let k1ActiveRound   = null;
    let k1Loaded        = false;

    function loadSchedule() {
        k2Loaded = true;
        Promise.all([
            fetch("/api/k2/schedule").then(r => r.json()),
            fetch("/api/k2/rounds").then(r => r.json()),
        ]).then(([sched, rounds]) => {
            scheduleCache = sched;
            roundsCache   = rounds;
            activeRound   = rounds.current_round;
            renderRoundsBanner(rounds, sched, "k2");
        }).catch(() => { k2Loaded = false; });
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
            const finished  = g.finished;
            const canPredict = !finished && g.home_id && g.away_id && g.home_id !== "null" && g.away_id !== "null";
            const hc = tc(g.home_id), ac = tc(g.away_id);
            const dateShort = g.date.replace(/\./g,"/").slice(5);

            const centerContent = finished
                ? `<div class="kmc-score">${g.home_score} <span class="kmc-score-sep">:</span> ${g.away_score}</div>
                   <div class="kmc-meta">${dateShort}</div>
                   <div class="kmc-tag kmc-tag-done">결과</div>`
                : canPredict
                    ? `<div class="kmc-time">${g.time || "-"}</div>
                       <div class="kmc-meta">${dateShort}</div>
                       <div class="kmc-tag kmc-tag-pred">예측 →</div>`
                    : `<div class="kmc-time">-</div>
                       <div class="kmc-meta">${dateShort}</div>`;

            const homeEmb  = hc.e ? `<img class="kmc-emb" src="/static/img/emblems/${hc.e}" alt="" onerror="this.style.display='none'">` : "";
            const awayEmb  = ac.e ? `<img class="kmc-emb" src="/static/img/emblems/${ac.e}" alt="" onerror="this.style.display='none'">` : "";

            return `
            <div class="kmc${finished ? " kmc-done" : canPredict ? " kmc-upcoming" : ""}"
                 data-home="${g.home_id}" data-away="${g.away_id}"
                 data-finished="${finished}"
                 data-full-date="${g.date}">
                <div class="kmc-side kmc-home" style="background:linear-gradient(135deg,${hc.p}55 0%,${hc.p}22 100%)">
                    ${homeEmb}
                    <span class="kmc-name">${g.home_short}</span>
                </div>
                <div class="kmc-mid">${centerContent}</div>
                <div class="kmc-side kmc-away" style="background:linear-gradient(225deg,${ac.p}55 0%,${ac.p}22 100%)">
                    <span class="kmc-name">${g.away_short}</span>
                    ${awayEmb}
                </div>
            </div>`;
        }).join("");

        list.querySelectorAll(".kmc").forEach(item => {
            item.addEventListener("click", () => {
                const homeId = item.dataset.home;
                const awayId = item.dataset.away;
                if (!homeId || !awayId || homeId === "null" || awayId === "null") return;
                section.classList.remove("hidden");
                loadPrediction(homeId, awayId);

                const isFinished = item.dataset.finished === "true";
                const gameDate   = item.dataset.fullDate || null;
                if (isFinished && gameDate) {
                    fetch(`/api/match-lineup?date=${encodeURIComponent(gameDate)}&home_slug=${encodeURIComponent(homeId)}&away_slug=${encodeURIComponent(awayId)}`)
                        .then(r => r.json())
                        .then(data => {
                            if (data && data.ready) {
                                document.dispatchEvent(new CustomEvent("matchLineupLoaded", { detail: data }));
                            }
                        })
                        .catch(() => {});
                }
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
    });


    // 백테스트 정확도 — 리그별 캐시
    let _backtestCache = {};
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

    // 라운드별 적중률 막대 차트
    function backtestChartHtml(perRound) {
        if (!perRound || perRound.length < 2) return "";
        const W = 380, H = 100, PAD_L = 30, PAD_R = 12, PAD_T = 14, PAD_B = 22;
        const innerW = W - PAD_L - PAD_R;
        const innerH = H - PAD_T - PAD_B;
        const n = perRound.length;
        const BAR_GAP = 0.25;
        const barW = (innerW / n) * (1 - BAR_GAP);
        const slotW = innerW / n;
        const yAt = pct => PAD_T + (1 - pct / 100) * innerH;
        const zeroY = yAt(0);

        // 막대 — 성과 구간별 색상
        const bars = perRound.map((r, i) => {
            const pct = r.round_pct || 0;
            const x = (PAD_L + i * slotW + slotW * BAR_GAP / 2).toFixed(1);
            const y = yAt(pct).toFixed(1);
            const bh = Math.max(1, zeroY - yAt(pct)).toFixed(1);
            const fill = pct >= 50 ? "#4ade80" : pct >= 33 ? "#facc15" : "#f87171";
            const isLast = i === n - 1;
            const opacity = isLast ? "1" : "0.75";
            const label = isLast || pct >= 60 || pct === 0
                ? `<text x="${(+x + barW / 2).toFixed(1)}" y="${(+y - 2).toFixed(1)}" font-size="7.5" fill="${fill}" text-anchor="middle" font-weight="700">${pct}%</text>`
                : "";
            return `<rect x="${x}" y="${y}" width="${barW.toFixed(1)}" height="${bh}" rx="2" fill="${fill}" opacity="${opacity}">
                <title>R${r.round} · ${pct}% (${r.hit}/${r.total})</title></rect>${label}`;
        }).join("");

        // 50% / 33% 기준선
        const ref50Y = yAt(50).toFixed(1);
        const ref33Y = yAt(33.3).toFixed(1);

        // y축 라벨
        const yLabels = [0, 50, 100].map(v => `
            <text x="${PAD_L - 4}" y="${(yAt(v) + 3).toFixed(1)}" font-size="8" fill="#4a6a88" text-anchor="end">${v}</text>
            <line x1="${PAD_L}" y1="${yAt(v).toFixed(1)}" x2="${W - PAD_R}" y2="${yAt(v).toFixed(1)}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
        `).join("");

        // x축 라벨 (라운드 수 많으면 짝수만)
        const xLabels = perRound.map((r, i) => {
            if (n > 8 && i % 2 !== 0) return "";
            const cx = (PAD_L + i * slotW + slotW / 2).toFixed(1);
            return `<text x="${cx}" y="${H - PAD_B + 12}" font-size="8" fill="#4a6a88" text-anchor="middle">R${r.round}</text>`;
        }).join("");

        return `
        <div class="pred-backtest-chart">
            <svg class="pbc-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
                ${yLabels}
                <!-- 50% 기준선 -->
                <line x1="${PAD_L}" y1="${ref50Y}" x2="${W - PAD_R}" y2="${ref50Y}" stroke="rgba(255,255,255,0.12)" stroke-width="1" stroke-dasharray="4,3"/>
                <!-- 33% 무작위 기준선 -->
                <line x1="${PAD_L}" y1="${ref33Y}" x2="${W - PAD_R}" y2="${ref33Y}" stroke="#f87171" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>
                <text x="${W - PAD_R - 2}" y="${(+ref33Y - 2).toFixed(1)}" font-size="7" fill="#f87171" text-anchor="end" opacity="0.7">랜덤 33%</text>
                <!-- 라운드별 막대 -->
                ${bars}
                ${xLabels}
            </svg>
            <div class="pbc-legend">
                <span class="pbc-lg"><span class="pbc-lg-bar" style="background:#4ade80"></span>50%↑</span>
                <span class="pbc-lg"><span class="pbc-lg-bar" style="background:#facc15"></span>33~50%</span>
                <span class="pbc-lg"><span class="pbc-lg-bar" style="background:#f87171"></span>33%↓</span>
            </div>
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
        _lastHome = homeId; _lastAway = awayId;
        report.innerHTML = `<div class="pred-loading">분석 중...</div>`;
        const league = _inferLeague(homeId, awayId);
        Promise.all([
            fetch(`/api/match-prediction?homeTeam=${homeId}&awayTeam=${awayId}`).then(r => r.json()),
            loadBacktest(league),
            fetch(`/api/predicted-lineup?teamId=${homeId}`).then(r => r.json()).catch(() => null),
            fetch(`/api/predicted-lineup?teamId=${awayId}`).then(r => r.json()).catch(() => null),
        ])
            .then(([data, bt, hLineup, aLineup]) => render(data, homeId, awayId, bt, hLineup, aLineup))
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
            return `<div class="lu-player">
                <span class="lu-pos" style="background:${POS_COLORS[s.position] || "#666"}33;color:${POS_COLORS[s.position] || "#aaa"}">${POS_LABEL[s.position] || "?"}</span>
                <span class="lu-num">#${s.shirt_number || "-"}</span>
                <span class="lu-name">${s.name}</span>
                ${s.rating ? `<span class="lu-rating">${s.rating}</span>` : ""}
            </div>`;
        };
        const formationStr = d.formation ? `<span class="lu-formation">${d.formation}</span>` : "";
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
    function confidenceBadge(conf, isK1) {
        if (!conf) return "";
        const meta = {
            high: { icon: "🟢", label: "신뢰도 높음", color: "#7bed9f" },
            med:  { icon: "🟡", label: "신뢰도 보통", color: "#facc15" },
            low:  { icon: "🔴", label: "신뢰도 낮음", color: "#f87171" },
        };
        const m = meta[conf.level] || meta.low;
        const badge = `<div class="pred-confidence" style="border-color:${m.color}55">
            <span class="pc-icon">${m.icon}</span>
            <span class="pc-label" style="color:${m.color}">${m.label}</span>
            <span class="pc-sub">H2H ${conf.h2h_games}경기 · 시즌 ${conf.season_games}경기</span>
        </div>`;
        if (!isK1 || conf.level === "high") return badge;
        const warn = conf.level === "low"
            ? { bg: "rgba(239,68,68,0.12)", border: "#ef4444", icon: "⚠️", text: "K1 예측 신뢰도 매우 낮음 — 참고 불가" }
            : { bg: "rgba(251,191,36,0.10)", border: "#f59e0b", icon: "📊", text: "K1 데이터 부족 — 참고용으로만 활용" };
        return `${badge}<div class="pred-uncertainty-warn" style="background:${warn.bg};border-color:${warn.border}">
            <span class="puw-icon">${warn.icon}</span>
            <span class="puw-text">${warn.text}</span>
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
        const isK1 = _inferLeague(homeId, awayId) === "k1";
        const isUncertain = isK1 && d.confidence && d.confidence.level !== "high";

        // 다음 경기 배너에서 이 매치의 정보 가져오기 (K1/K2 모두 참조)
        let nextInfo = null;
        for (const cache of [scheduleCache, k1ScheduleCache]) {
            if (!cache) continue;
            nextInfo = (cache.upcoming || []).find(
                g => g.home_id === homeId && g.away_id === awayId
            );
            if (nextInfo) break;
        }

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
            </div>

            <!-- 중앙 예측 -->
            <div class="pred-center${isUncertain ? " pred-center--uncertain" : ""}">
                ${confidenceBadge(d.confidence, isK1)}
                <div class="pred-center-title">예상 결과</div>
                <div class="pred-prob-bar${isUncertain ? " pred-prob-bar--uncertain" : ""}">
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

    let _lastHome = null, _lastAway = null;

    // 페이지 로드 시 K2 일정 불러오기
    loadSchedule();
})();
