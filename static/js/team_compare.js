// team_compare.js — 두 팀 주요 스탯 비교 모달 (Chart.js 레이더 오버레이)

(function () {
    function loadChartJS(cb) {
        if (window.Chart) { cb(); return; }
        const s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
        s.onload = cb;
        document.head.appendChild(s);
    }

    const modal      = document.getElementById("team-compare-modal");
    if (!modal) return;
    const backdrop   = modal.querySelector(".modal-backdrop");
    const closeBtn   = document.getElementById("tc-close");
    const selA       = document.getElementById("tc-team-a");
    const selB       = document.getElementById("tc-team-b");
    const body       = document.getElementById("tc-body");
    const empty      = document.getElementById("tc-empty");
    const yearFilter = document.getElementById("tc-year-filter");

    let teamsLoaded = false;
    let currentYear = "전체";
    let radarChart  = null;
    // 조회 최적화 상태
    const _cache = new Map();           // key: `${teamA}|${teamB}|${year}` → data
    const _matchesCache = new Map();    // key: `${teamA}|${teamB}|${year}` → matches[]
    let _inFlight = null;               // AbortController for team-compare
    let _matchesInFlight = null;        // AbortController for h2h-matches
    let _debounceTimer = null;

    function populateSelects() {
        if (teamsLoaded) return;
        fetch("/api/teams").then(r => r.json()).then(teams => {
            teamsLoaded = true;
            const grouped = { K1: [], K2: [] };
            teams.forEach(t => { if (grouped[t.league]) grouped[t.league].push(t); });
            Object.values(grouped).forEach(arr => arr.sort((a, b) => a.name.localeCompare(b.name, "ko")));
            [selA, selB].forEach(sel => {
                sel.innerHTML = '<option value="">팀 선택...</option>';
                [["K1", "K리그1"], ["K2", "K리그2"]].forEach(([key, label]) => {
                    if (!grouped[key].length) return;
                    const og = document.createElement("optgroup");
                    og.label = label;
                    grouped[key].forEach(t => {
                        const opt = document.createElement("option");
                        opt.value = t.id;
                        opt.textContent = t.name;
                        og.appendChild(opt);
                    });
                    sel.appendChild(og);
                });
            });
        });
    }

    function buildYearFilter(years) {
        yearFilter.innerHTML = "";
        ["전체", ...years].forEach(y => {
            const btn = document.createElement("button");
            btn.className = "year-filter-btn" + (y === currentYear ? " active" : "");
            btn.textContent = y === "전체" ? "전체" : y + "년";
            btn.dataset.year = y;
            btn.addEventListener("click", () => {
                currentYear = y;
                yearFilter.querySelectorAll(".year-filter-btn").forEach(b => {
                    b.classList.toggle("active", b.dataset.year === y);
                });
                loadIfReady();
            });
            yearFilter.appendChild(btn);
        });
    }

    function open() {
        loadChartJS(() => {
            modal.classList.remove("hidden");
            populateSelects();
        });
    }
    function close() { modal.classList.add("hidden"); }

    document.getElementById("btn-team-compare").addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    backdrop.addEventListener("click", close);

    selA.addEventListener("change", debouncedLoad);
    selB.addEventListener("change", debouncedLoad);

    function debouncedLoad() {
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(loadIfReady, 180);
    }

    function loadIfReady() {
        const a = selA.value, b = selB.value;
        if (!a || !b || a === b) {
            body.classList.add("hidden");
            empty.classList.remove("hidden");
            if (a && b && a === b) empty.textContent = "같은 팀은 비교할 수 없습니다.";
            else empty.textContent = "좌/우 팀을 선택하면 비교가 표시됩니다.";
            return;
        }
        const yp = currentYear !== "전체" ? `&year=${currentYear}` : "";
        const cacheKey = `${a}|${b}|${currentYear}`;
        const matchesKey = `${a}|${b}|${currentYear}`;

        // 캐시 히트: 즉시 렌더 (네트워크 스킵)
        if (_cache.has(cacheKey)) {
            render(_cache.get(cacheKey));
            if (_matchesCache.has(matchesKey)) renderMatches(_matchesCache.get(matchesKey));
            else fetchMatches(a, b, matchesKey);
            return;
        }

        // in-flight 취소
        if (_inFlight) _inFlight.abort();
        _inFlight = new AbortController();

        empty.classList.remove("hidden");
        empty.textContent = "불러오는 중...";

        fetch(`/api/team-compare?teamA=${a}&teamB=${b}${yp}`, { signal: _inFlight.signal })
            .then(r => r.json())
            .then(data => {
                _cache.set(cacheKey, data);
                render(data);
                // 캐시 크기 제한 (가장 오래된 항목 제거)
                if (_cache.size > 30) _cache.delete(_cache.keys().next().value);
            })
            .catch(err => {
                if (err.name === "AbortError") return; // 취소는 무시
                empty.textContent = "데이터를 가져오지 못했습니다.";
            });

        // 맞대결 경기 리스트는 병렬 fetch
        if (_matchesCache.has(matchesKey)) renderMatches(_matchesCache.get(matchesKey));
        else fetchMatches(a, b, matchesKey);
    }

    function fetchMatches(a, b, cacheKey) {
        if (_matchesInFlight) _matchesInFlight.abort();
        _matchesInFlight = new AbortController();
        const yp = currentYear !== "전체" ? `&year=${currentYear}` : "";
        fetch(`/api/h2h-matches?teamA=${a}&teamB=${b}${yp}&limit=20`, { signal: _matchesInFlight.signal })
            .then(r => r.json())
            .then(matches => {
                _matchesCache.set(cacheKey, matches);
                renderMatches(matches);
                if (_matchesCache.size > 30) _matchesCache.delete(_matchesCache.keys().next().value);
            })
            .catch(err => {
                if (err.name === "AbortError") return;
                renderMatches([]);
            });
    }

    function render(data) {
        if (!data || !data.teamA || !data.teamB) return;
        empty.classList.add("hidden");
        body.classList.remove("hidden");
        buildYearFilter(data.available_years || []);
        renderHeader(data);
        renderRadar(data);
        renderForm(data);
        renderHA(data);
        renderBars(data);
    }

    // hex → "r,g,b" 문자열
    function hexRgb(hex, fallback) {
        const m = /^#?([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})$/i.exec(hex || "");
        if (!m) return fallback;
        return `${parseInt(m[1],16)},${parseInt(m[2],16)},${parseInt(m[3],16)}`;
    }

    function renderHeader(data) {
        const a = data.teamA, b = data.teamB, h = data.h2h || {};
        document.getElementById("tc-name-a").textContent = a.name || "";
        document.getElementById("tc-name-b").textContent = b.name || "";
        document.getElementById("tc-league-a").textContent = a.league || "";
        document.getElementById("tc-league-b").textContent = b.league || "";
        const embA = document.getElementById("tc-emblem-a");
        const embB = document.getElementById("tc-emblem-b");
        embA.src = a.emblem ? `/static/img/${a.emblem}` : "";
        embB.src = b.emblem ? `/static/img/${b.emblem}` : "";

        // 매치업 포스터 배경에 팀 컬러 라디얼 그라디언트 주입
        const titleRow = document.querySelector(".tc-title-row");
        if (titleRow) {
            const rgbA = hexRgb(a.primary, "78,164,248");
            const rgbB = hexRgb(b.primary, "184,126,248");
            titleRow.style.setProperty("--tc-color-a", `rgba(${rgbA},0.32)`);
            titleRow.style.setProperty("--tc-color-b", `rgba(${rgbB},0.32)`);
        }

        const h2h = document.getElementById("tc-h2h-summary");
        if (h.games > 0) {
            h2h.textContent = `${h.a_wins}  ${h.draws}  ${h.b_wins}`;
            h2h.title = `${h.games}경기 · ${a.short}기준 ${h.a_wins}승 ${h.draws}무 ${h.b_wins}패, 득실 ${h.a_gf}:${h.a_ga}`;
        } else {
            h2h.textContent = "— vs —";
            h2h.title = "맞대결 기록 없음";
        }
    }

    // 팀 색상 → 레이더 데이터셋 색상
    function teamColors(team, isSecond) {
        const base = team.primary || (isSecond ? "#b87ef8" : "#4ea4f8");
        // hex → rgb
        const m = /^#?([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})$/i.exec(base);
        const rgb = m ? [parseInt(m[1],16), parseInt(m[2],16), parseInt(m[3],16)] : [78,164,248];
        return {
            border: `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.95)`,
            fill:   `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.18)`,
            point:  `rgba(${rgb[0]},${rgb[1]},${rgb[2]},1)`,
        };
    }

    function renderRadar(data) {
        const el = document.getElementById("tc-radar");
        if (!el) return;

        const a = data.teamA, b = data.teamB;
        const labels = ["승률(%)", "경기당 승점×30", "평균 득점×30", "평균 실점⁻¹×50", "홈 승률(%)", "원정 승률(%)"];
        const pct = (n, g) => g > 0 ? (n / g * 100) : 0;

        const toRow = (t) => {
            const homeG = t.home && t.home.games || 0;
            const awayG = t.away && t.away.games || 0;
            return [
                t.win_pct || 0,
                (t.ppg || 0) * 30,
                (t.avg_gf || 0) * 30,
                t.avg_ga > 0 ? Math.min(100, 50 / t.avg_ga) : 50,
                pct((t.home && t.home.w) || 0, homeG),
                pct((t.away && t.away.w) || 0, awayG),
            ];
        };

        const cA = teamColors(a, false);
        const cB = teamColors(b, true);
        const rowA = toRow(a), rowB = toRow(b);

        // 인스턴스 재사용 (destroy 없이 data만 교체 → 렌더 비용 절감)
        if (radarChart) {
            radarChart.data.datasets[0].label = a.short || a.name;
            radarChart.data.datasets[0].data  = rowA;
            radarChart.data.datasets[0].borderColor = cA.border;
            radarChart.data.datasets[0].backgroundColor = cA.fill;
            radarChart.data.datasets[0].pointBackgroundColor = cA.point;
            radarChart.data.datasets[1].label = b.short || b.name;
            radarChart.data.datasets[1].data  = rowB;
            radarChart.data.datasets[1].borderColor = cB.border;
            radarChart.data.datasets[1].backgroundColor = cB.fill;
            radarChart.data.datasets[1].pointBackgroundColor = cB.point;
            radarChart.update();
            return;
        }

        radarChart = new Chart(el, {
            type: "radar",
            data: {
                labels,
                datasets: [
                    {
                        label: a.short || a.name,
                        data: rowA,
                        borderColor: cA.border,
                        backgroundColor: cA.fill,
                        pointBackgroundColor: cA.point,
                        pointRadius: 4,
                        borderWidth: 2,
                    },
                    {
                        label: b.short || b.name,
                        data: rowB,
                        borderColor: cB.border,
                        backgroundColor: cB.fill,
                        pointBackgroundColor: cB.point,
                        pointRadius: 4,
                        borderWidth: 2,
                        borderDash: [6, 4],
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 600, easing: "easeOutQuart" },
                plugins: {
                    legend: { labels: { color: "#1f2d47", font: { weight: "600" }, usePointStyle: true, padding: 12 } },
                    tooltip: {
                        backgroundColor: "#ffffff",
                        borderColor: "rgba(74,130,199,0.35)",
                        borderWidth: 1,
                        titleColor: "#1f2d47",
                        bodyColor: "#1f2d47",
                        padding: 10,
                        cornerRadius: 8,
                        boxShadow: "0 6px 18px rgba(70,90,140,0.15)",
                        callbacks: {
                            label: (c) => `${c.dataset.label}: ${(+c.parsed.r).toFixed(1)}`
                        }
                    }
                },
                scales: {
                    r: {
                        min: 0, max: 100,
                        angleLines: { color: "rgba(90,110,140,0.18)" },
                        grid: { color: "rgba(90,110,140,0.14)" },
                        pointLabels: { color: "#1f2d47", font: { size: 11, weight: "600" } },
                        ticks: { color: "#8592a8", backdropColor: "rgba(255,255,255,0.7)", stepSize: 25, font: { size: 9 } }
                    }
                }
            }
        });
    }

    function renderForm(data) {
        const render = (team, el) => {
            el.innerHTML = `<span style="min-width:60px;font-weight:600">${team.short || team.name}</span>`;
            (team.form || []).forEach(r => {
                const span = document.createElement("span");
                span.className = "tc-form-badge tc-form-" + r;
                span.textContent = r;
                el.appendChild(span);
            });
            if (!(team.form || []).length) {
                el.innerHTML += '<span style="color:#6a7e98">경기 기록 없음</span>';
            }
        };
        render(data.teamA, document.getElementById("tc-form-a"));
        render(data.teamB, document.getElementById("tc-form-b"));
    }

    function renderHA(data) {
        const a = data.teamA, b = data.teamB;
        const pct = (n, g) => g > 0 ? Math.round(n / g * 100) : 0;
        const ha = (t, side) => {
            const r = (t[side] || {});
            return { games: r.games||0, w: r.w||0, d: r.d||0, l: r.l||0, pct: pct(r.w||0, r.games||0) };
        };
        const aHome = ha(a,"home"), aAway = ha(a,"away"), bHome = ha(b,"home"), bAway = ha(b,"away");
        const pctBadge = (p) => `<span class="tc-ha-pct" style="color:${p>=50?'#7bed9f':p>=30?'#ffd77a':'#f87171'}">${p}%</span>`;
        const tbl = document.getElementById("tc-ha-table");
        tbl.innerHTML = `
            <tr><th>팀</th><th>홈 승률</th><th>홈 전적</th><th>원정 승률</th><th>원정 전적</th></tr>
            <tr>
                <td style="color:${a.primary||'#4ea4f8'};font-weight:700">${a.short||a.name}</td>
                <td>${pctBadge(aHome.pct)}</td>
                <td>${aHome.w}-${aHome.d}-${aHome.l}</td>
                <td>${pctBadge(aAway.pct)}</td>
                <td>${aAway.w}-${aAway.d}-${aAway.l}</td>
            </tr>
            <tr>
                <td style="color:${b.primary||'#b87ef8'};font-weight:700">${b.short||b.name}</td>
                <td>${pctBadge(bHome.pct)}</td>
                <td>${bHome.w}-${bHome.d}-${bHome.l}</td>
                <td>${pctBadge(bAway.pct)}</td>
                <td>${bAway.w}-${bAway.d}-${bAway.l}</td>
            </tr>`;
    }

    // 숫자 카운트업 애니메이션 (integer/decimal 모두 처리)
    function animateCount(el, target, duration = 700) {
        const isInt = Number.isInteger(target);
        const start = performance.now();
        function tick(now) {
            const t = Math.min(1, (now - start) / duration);
            // easeOutCubic
            const eased = 1 - Math.pow(1 - t, 3);
            const v = target * eased;
            el.textContent = isInt ? Math.round(v).toString() : (+v.toFixed(2)).toString();
            if (t < 1) requestAnimationFrame(tick);
            else el.textContent = fmtNum(target);
        }
        requestAnimationFrame(tick);
    }

    function renderBars(data) {
        const a = data.teamA, b = data.teamB;
        const metrics = [
            { label: "경기",        va: a.games,   vb: b.games,   higher: "higher" },
            { label: "승",          va: a.w,       vb: b.w,       higher: "higher" },
            { label: "무",          va: a.d,       vb: b.d,       higher: "neutral" },
            { label: "패",          va: a.l,       vb: b.l,       higher: "lower" },
            { label: "승점",        va: a.pts,     vb: b.pts,     higher: "higher" },
            { label: "승점/경기",   va: a.ppg,     vb: b.ppg,     higher: "higher" },
            { label: "승률 %",      va: a.win_pct, vb: b.win_pct, higher: "higher" },
            { label: "평균 득점",   va: a.avg_gf,  vb: b.avg_gf,  higher: "higher" },
            { label: "평균 실점",   va: a.avg_ga,  vb: b.avg_ga,  higher: "lower" },
            { label: "득실차",      va: a.gd,      vb: b.gd,      higher: "higher" },
        ];
        if (a.xg_home != null || b.xg_home != null) {
            metrics.push({ label: "홈 xG(경기당)", va: a.xg_home || 0, vb: b.xg_home || 0, higher: "higher" });
        }

        const host = document.getElementById("tc-bars");
        host.innerHTML = "";
        const colorA = a.primary || "#4ea4f8";
        const colorB = b.primary || "#b87ef8";
        // 팀 컬러를 살짝 어둡게 (그라디언트 끝 쪽)
        const darken = (hex) => {
            const m = /^#?([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})$/i.exec(hex || "");
            if (!m) return hex;
            const r = Math.max(0, parseInt(m[1],16) - 40);
            const g = Math.max(0, parseInt(m[2],16) - 40);
            const b2 = Math.max(0, parseInt(m[3],16) - 40);
            return `rgb(${r},${g},${b2})`;
        };
        const colorAD = darken(colorA), colorBD = darken(colorB);

        metrics.forEach(m => {
            const max = Math.max(Math.abs(m.va), Math.abs(m.vb), 0.0001);
            const pctA = Math.abs(m.va) / max * 100;
            const pctB = Math.abs(m.vb) / max * 100;

            let winner = "none";
            if (m.higher === "higher") {
                winner = m.va > m.vb ? "A" : m.va < m.vb ? "B" : "none";
            } else if (m.higher === "lower") {
                winner = m.va < m.vb ? "A" : m.va > m.vb ? "B" : "none";
            }

            const wDotA = winner === "A" ? '<span class="tc-bar-winner-indicator" title="우위"></span>' : '';
            const wDotB = winner === "B" ? '<span class="tc-bar-winner-indicator" title="우위"></span>' : '';

            const row = document.createElement("div");
            row.className = "tc-bar-row";
            row.innerHTML = `
                <div class="tc-bar-side tc-bar-side-a" style="--tc-fill-from:${colorA};--tc-fill-to:${colorAD}">
                    ${wDotA}<span class="tc-bar-val ${winner==='A'?'tc-bar-winner':''}" data-target="${m.va}">0</span>
                    <div class="tc-bar-fill" style="width:0"></div>
                </div>
                <div class="tc-bar-label">${m.label}</div>
                <div class="tc-bar-side" style="--tc-fill-from:${colorB};--tc-fill-to:${colorBD}">
                    <div class="tc-bar-fill" style="width:0"></div>
                    <span class="tc-bar-val ${winner==='B'?'tc-bar-winner':''}" data-target="${m.vb}">0</span>${wDotB}
                </div>`;
            host.appendChild(row);

            // 바 너비 트랜지션 (다음 프레임에 적용해 애니메이션 발동)
            const fills = row.querySelectorAll(".tc-bar-fill");
            requestAnimationFrame(() => {
                fills[0].style.width = pctA + "%";
                fills[1].style.width = pctB + "%";
            });
            // 숫자 카운트업
            const vals = row.querySelectorAll(".tc-bar-val");
            animateCount(vals[0], +m.va || 0);
            animateCount(vals[1], +m.vb || 0);
        });
    }

    function fmtNum(v) {
        if (v == null) return "-";
        if (typeof v !== "number") return String(v);
        if (Number.isInteger(v)) return v.toString();
        return (+v.toFixed(2)).toString();
    }

    // ─── 경기별 뷰 (H2H 맞대결 리스트) ─────────────────────
    function renderMatches(matches) {
        const list  = document.getElementById("tc-matches-list");
        const count = document.getElementById("tc-matches-count");
        if (!list) return;
        list.innerHTML = "";
        const n = (matches || []).length;
        count.textContent = n > 0 ? `${n}경기` : "";
        if (!n) {
            list.innerHTML = `<div class="tc-matches-empty">해당 조건의 맞대결 기록이 없습니다.</div>`;
            return;
        }

        const aId = selA.value;
        const bId = selB.value;
        // teamA의 sofascore 관점에서 결과를 결정하려면 data.teamA 필요, 단순화: is_home_a 플래그 활용

        matches.forEach((m, idx) => {
            const card = document.createElement("div");
            card.className = "tc-match-card tc-match-" + m.result_a.toLowerCase();
            const resultText = m.result_a === "W" ? "승" : m.result_a === "D" ? "무" : "패";
            // 홈/원정 박스 - A가 홈이면 왼쪽이 A
            const homeScorerHTML = (m.scorers_home || []).map(s =>
                `<span class="tc-scorer">${escapeHtml(s.name)}${s.goals > 1 ? ` ⚽×${s.goals}` : " ⚽"}</span>`
            ).join("");
            const awayScorerHTML = (m.scorers_away || []).map(s =>
                `<span class="tc-scorer">${escapeHtml(s.name)}${s.goals > 1 ? ` ⚽×${s.goals}` : " ⚽"}</span>`
            ).join("");

            card.innerHTML = `
                <div class="tc-match-date">${m.date}</div>
                <div class="tc-match-body">
                    <div class="tc-match-team tc-match-team-home">
                        <span class="tc-match-team-name">${escapeHtml(m.home)}</span>
                        <div class="tc-match-scorers">${homeScorerHTML || '<span class="tc-scorer-empty">—</span>'}</div>
                    </div>
                    <div class="tc-match-score">
                        <span class="tc-match-score-num">${m.home_score}</span>
                        <span class="tc-match-score-sep">:</span>
                        <span class="tc-match-score-num">${m.away_score}</span>
                    </div>
                    <div class="tc-match-team tc-match-team-away">
                        <span class="tc-match-team-name">${escapeHtml(m.away)}</span>
                        <div class="tc-match-scorers">${awayScorerHTML || '<span class="tc-scorer-empty">—</span>'}</div>
                    </div>
                </div>
                <div class="tc-match-result tc-match-result-${m.result_a.toLowerCase()}" title="${selA.selectedOptions[0]?.textContent || ''} 기준">${resultText}</div>`;
            card.style.animationDelay = (idx * 0.04) + "s";
            list.appendChild(card);
        });
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s).replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }
})();
