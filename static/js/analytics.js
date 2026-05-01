// analytics.js — 팀 분석 모달 (Chart.js 기반)

(function () {
    // ── DOM refs ──────────────────────────────────────────────────
    const modal      = document.getElementById("analytics-modal");
    const backdrop   = modal.querySelector(".modal-backdrop");
    const closeBtn   = document.getElementById("analytics-close");
    const teamSelect = document.getElementById("analytics-team-select");
    const tabBtns    = modal.querySelectorAll(".analytics-tab-btn");
    const panels     = modal.querySelectorAll(".analytics-panel");
    const titleEl    = document.getElementById("analytics-team-title");

    let charts = {};
    let currentTeamId = null;
    let currentYear = "전체";

    // ── 팀 목록 채우기 ────────────────────────────────────────────
    let teamsLoaded = false;
    function populateTeamSelect() {
        if (teamsLoaded) return;
        fetch("/api/teams").then(r => r.json()).then(teams => {
            teamsLoaded = true;
            const grouped = { K1: [], K2: [] };
            teams.forEach(t => {
                if (grouped[t.league]) grouped[t.league].push(t);
            });
            Object.values(grouped).forEach(arr =>
                arr.sort((a, b) => a.name.localeCompare(b.name, "ko"))
            );
            teamSelect.innerHTML = '<option value="">팀 선택...</option>';
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
                teamSelect.appendChild(og);
            });
        });
    }

    // ── 탭 전환 ──────────────────────────────────────────────────
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            panels.forEach(p => p.classList.add("hidden"));
            btn.classList.add("active");
            const panel = document.getElementById("analytics-panel-" + btn.dataset.tab);
            if (panel) panel.classList.remove("hidden");
        });
    });

    // ── 연도 필터 빌드 ────────────────────────────────────────────
    function buildYearFilter(years, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = "";
        ["전체", ...years].forEach(y => {
            const btn = document.createElement("button");
            btn.className = "year-filter-btn" + (y === currentYear ? " active" : "");
            btn.textContent = y === "전체" ? "전체" : y + "년";
            btn.dataset.year = y;
            btn.addEventListener("click", () => {
                currentYear = y;
                modal.querySelectorAll(".year-filter-btn").forEach(b => {
                    b.classList.toggle("active", b.dataset.year === y);
                });
                if (currentTeamId) loadAnalytics(currentTeamId);
            });
            container.appendChild(btn);
        });
    }

    // ── 열기 ─────────────────────────────────────────────────────
    document.getElementById("btn-analytics").addEventListener("click", () => {
        modal.classList.remove("hidden");
        populateTeamSelect();
    });

    function closeModal() { modal.classList.add("hidden"); }
    closeBtn.addEventListener("click", closeModal);
    backdrop.addEventListener("click", closeModal);

    teamSelect.addEventListener("change", () => {
        currentTeamId = teamSelect.value || null;
        currentYear = "전체";
        if (currentTeamId) loadAnalytics(currentTeamId);
    });

    function loadAnalytics(teamId) {
        titleEl.textContent = "불러오는 중...";
        const yp = currentYear !== "전체" ? "&year=" + currentYear : "";
        Promise.all([
            fetch(`/api/team-analytics?teamId=${teamId}${yp}`).then(r => r.json()),
            fetch(`/api/goal-timing?teamId=${teamId}${yp}`).then(r => r.json()),
        ]).then(([data, goalData]) => {
            titleEl.textContent = data.team + " 분석";
            const years = data.available_years || [];
            buildYearFilter(years, "year-filter-global");
            renderVsOpponents(data.vs_opponents || []);
            renderByMonth(data.by_month || []);
            renderByYearHA(data.by_year_ha || {});
            renderWeather(data.weather || {});
            renderGoalTiming(goalData);
        });
    }

    // ── 헬퍼 ─────────────────────────────────────────────────────
    function destroyChart(key) {
        if (charts[key]) { charts[key].destroy(); delete charts[key]; }
    }
    function winPct(w, g) { return g > 0 ? Math.round(w / g * 100) : 0; }

    // 승률에 따른 색상 (0%=빨강 ~ 100%=초록)
    function winColor(pct, alpha = 0.85) {
        const r = Math.round(220 - pct * 1.2);
        const g = Math.round(60 + pct * 1.6);
        const b = 80;
        return `rgba(${r},${g},${b},${alpha})`;
    }

    // 캔버스 세로 그라디언트
    function vertGrad(ctx, top, bottom) {
        const grad = ctx.createLinearGradient(0, 0, 0, 300);
        grad.addColorStop(0, top);
        grad.addColorStop(1, bottom);
        return grad;
    }

    // 공통 Chart 기본 옵션
    const BASE_OPTS = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500, easing: "easeOutQuart" },
        plugins: {
            legend: {
                labels: { color: "#b0c4d8", font: { size: 11 }, padding: 14, usePointStyle: true, pointStyleWidth: 10 }
            },
            tooltip: {
                backgroundColor: "rgba(10,18,40,0.92)",
                borderColor: "rgba(100,160,255,0.25)",
                borderWidth: 1,
                titleColor: "#7eb8ff",
                bodyColor: "#cdd8e8",
                padding: 10,
                cornerRadius: 8,
            }
        }
    };

    function mergeOpts(extra) {
        return Object.assign({}, BASE_OPTS, extra,
            { plugins: Object.assign({}, BASE_OPTS.plugins, extra.plugins || {}) });
    }

    // ── 1. 상대팀별 (수평 바) ──────────────────────────────────────
    function renderVsOpponents(rows) {
        destroyChart("vs");
        const el = document.getElementById("chart-vs");
        if (!rows.length) { el.closest(".chart-wrap").innerHTML = "<p class='chart-empty'>데이터 없음</p>"; return; }

        rows = [...rows].sort((a, b) => winPct(a.w, a.games) - winPct(b.w, b.games));

        const labels  = rows.map(r => r.name);
        const wPct    = rows.map(r => winPct(r.w, r.games));
        const dPct    = rows.map(r => winPct(r.d, r.games));
        const lPct    = rows.map(r => winPct(r.l, r.games));
        const barH    = Math.max(28, Math.min(42, 360 / rows.length));

        // 차트 높이 동적 조절
        el.closest(".chart-wrap").style.height = (rows.length * barH + 60) + "px";

        charts["vs"] = new Chart(el, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label: "승", data: wPct, backgroundColor: rows.map(r => winColor(winPct(r.w,r.games))), borderRadius: { topLeft:0, topRight:4, bottomLeft:0, bottomRight:4 }, borderSkipped: false },
                    { label: "무", data: dPct, backgroundColor: "rgba(120,130,150,0.6)", borderRadius: 0 },
                    { label: "패", data: lPct, backgroundColor: "rgba(220,70,70,0.7)", borderRadius: { topLeft:4, topRight:0, bottomLeft:4, bottomRight:0 }, borderSkipped: false },
                ]
            },
            options: mergeOpts({
                indexAxis: "y",
                plugins: {
                    tooltip: {
                        ...BASE_OPTS.plugins.tooltip,
                        callbacks: {
                            label(ctx) {
                                return ctx.dataset.label + ": " + ctx.parsed.x + "%";
                            },
                            afterBody(ctx) {
                                const r = rows[ctx[0].dataIndex];
                                return [`${r.games}경기  ${r.w}승 ${r.d}무 ${r.l}패`, `득실차: +${r.gf-r.ga} (${r.gf}득 ${r.ga}실)`];
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, max: 100, ticks: { color: "#7a8fa8", callback: v => v + "%", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.06)" } },
                    y: { stacked: true, ticks: { color: "#c0d0e0", font: { size: 11 } }, grid: { display: false } }
                }
            })
        });

        // 테이블
        const tbl = document.getElementById("table-vs");
        tbl.innerHTML = `<tr><th>상대팀</th><th>경기</th><th>승</th><th>무</th><th>패</th><th>득</th><th>실</th><th>승률</th></tr>`;
        [...rows].reverse().forEach(r => {
            const pct = winPct(r.w, r.games);
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${r.name}</td><td>${r.games}</td>
                <td style="color:#7bed9f">${r.w}</td>
                <td style="color:#aab">${r.d}</td>
                <td style="color:#e05c5c">${r.l}</td>
                <td>${r.gf}</td><td>${r.ga}</td>
                <td><span class="wr-badge" style="background:${winColor(pct,0.25)};color:${winColor(pct,1)};border:1px solid ${winColor(pct,0.5)}">${pct}%</span></td>
            `;
            tbl.appendChild(tr);
        });
    }

    // ── 2. 월별 (면적 + 라인) ─────────────────────────────────────
    function renderByMonth(rows) {
        destroyChart("month");
        const el = document.getElementById("chart-month");
        if (!rows.length) { el.closest(".chart-wrap").innerHTML = "<p class='chart-empty'>데이터 없음</p>"; return; }

        const MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const labels = rows.map(r => MONTHS[r.month - 1]);
        const wPct   = rows.map(r => winPct(r.w, r.games));
        const avgGf  = rows.map(r => r.games > 0 ? +(r.gf / r.games).toFixed(2) : 0);
        const avgGa  = rows.map(r => r.games > 0 ? +(r.ga / r.games).toFixed(2) : 0);

        charts["month"] = new Chart(el, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "승률(%)",
                        data: wPct,
                        backgroundColor: (ctx) => {
                            const chart = ctx.chart;
                            const {ctx: c, chartArea} = chart;
                            if (!chartArea) return "rgba(78,164,248,0.5)";
                            const grad = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                            grad.addColorStop(0, "rgba(78,164,248,0.75)");
                            grad.addColorStop(1, "rgba(78,164,248,0.1)");
                            return grad;
                        },
                        borderColor: "#4ea4f8",
                        borderWidth: 1.5,
                        borderRadius: 5,
                        yAxisID: "yLeft",
                        order: 2,
                    },
                    {
                        label: "평균 득점",
                        data: avgGf,
                        type: "line",
                        borderColor: "#7bed9f",
                        backgroundColor: "rgba(123,237,159,0.12)",
                        fill: true,
                        pointBackgroundColor: "#7bed9f",
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        tension: 0.4,
                        borderWidth: 2,
                        yAxisID: "yRight",
                        order: 1,
                    },
                    {
                        label: "평균 실점",
                        data: avgGa,
                        type: "line",
                        borderColor: "#f87171",
                        backgroundColor: "rgba(248,113,113,0.08)",
                        fill: true,
                        pointBackgroundColor: "#f87171",
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        tension: 0.4,
                        borderWidth: 2,
                        yAxisID: "yRight",
                        order: 1,
                    }
                ]
            },
            options: mergeOpts({
                plugins: {
                    tooltip: {
                        ...BASE_OPTS.plugins.tooltip,
                        callbacks: {
                            afterBody(ctx) {
                                const r = rows[ctx[0].dataIndex];
                                return [`${r.games}경기  ${r.w}승 ${r.d}무 ${r.l}패`];
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { color: "#8a9fb8", font: { size: 11 } }, grid: { color: "rgba(255,255,255,0.05)" } },
                    yLeft: {
                        position: "left", min: 0, max: 100,
                        ticks: { color: "#4ea4f8", callback: v => v + "%", font: { size: 10 } },
                        grid: { color: "rgba(255,255,255,0.06)" }
                    },
                    yRight: {
                        position: "right", min: 0, max: 5,
                        ticks: { color: "#7bed9f", font: { size: 10 } },
                        grid: { drawOnChartArea: false }
                    }
                }
            })
        });
    }

    // ── 3. 홈/어웨이 연도별 ───────────────────────────────────────
    function renderByYearHA(data) {
        destroyChart("ha");
        const el = document.getElementById("chart-ha");
        const years = Object.keys(data).sort();
        if (!years.length) { el.closest(".chart-wrap").innerHTML = "<p class='chart-empty'>데이터 없음</p>"; return; }

        const homeWPct = years.map(y => data[y].home ? winPct(data[y].home.w, data[y].home.games) : 0);
        const awayWPct = years.map(y => data[y].away ? winPct(data[y].away.w, data[y].away.games) : 0);

        charts["ha"] = new Chart(el, {
            type: "bar",
            data: {
                labels: years,
                datasets: [
                    {
                        label: "홈 승률",
                        data: homeWPct,
                        backgroundColor: (ctx) => {
                            const {ctx: c, chartArea} = ctx.chart;
                            if (!chartArea) return "rgba(78,164,248,0.7)";
                            const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                            g.addColorStop(0, "rgba(78,164,248,0.85)");
                            g.addColorStop(1, "rgba(78,164,248,0.25)");
                            return g;
                        },
                        borderColor: "#4ea4f8",
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.5,
                    },
                    {
                        label: "원정 승률",
                        data: awayWPct,
                        backgroundColor: (ctx) => {
                            const {ctx: c, chartArea} = ctx.chart;
                            if (!chartArea) return "rgba(184,126,248,0.7)";
                            const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                            g.addColorStop(0, "rgba(184,126,248,0.85)");
                            g.addColorStop(1, "rgba(184,126,248,0.25)");
                            return g;
                        },
                        borderColor: "#b87ef8",
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.5,
                    },
                ]
            },
            options: mergeOpts({
                plugins: {
                    tooltip: {
                        ...BASE_OPTS.plugins.tooltip,
                        callbacks: {
                            afterBody(ctx) {
                                const y = years[ctx[0].dataIndex];
                                const h = data[y].home, a = data[y].away;
                                return [
                                    h ? `홈  ${h.games}경기  ${h.w}승 ${h.d}무 ${h.l}패  (${h.gf}득 ${h.ga}실)` : "",
                                    a ? `원정 ${a.games}경기  ${a.w}승 ${a.d}무 ${a.l}패  (${a.gf}득 ${a.ga}실)` : "",
                                ].filter(Boolean);
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { color: "#8a9fb8" }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: {
                        min: 0, max: 100,
                        ticks: { color: "#8a9fb8", callback: v => v + "%", font: { size: 10 } },
                        grid: { color: "rgba(255,255,255,0.06)" }
                    }
                }
            })
        });

        const tbl = document.getElementById("table-ha");
        tbl.innerHTML = `<tr><th>연도</th><th>홈경기</th><th>홈승률</th><th>홈득실</th><th>원정경기</th><th>원정승률</th><th>원정득실</th></tr>`;
        years.forEach(y => {
            const h = data[y].home || {}, a = data[y].away || {};
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${y}</td>
                <td>${h.games||0} (${h.w||0}승${h.d||0}무${h.l||0}패)</td>
                <td><span class="wr-badge" style="background:rgba(78,164,248,0.15);color:#4ea4f8;border:1px solid rgba(78,164,248,0.3)">${winPct(h.w||0,h.games||1)}%</span></td>
                <td>${h.gf||0}득 ${h.ga||0}실</td>
                <td>${a.games||0} (${a.w||0}승${a.d||0}무${a.l||0}패)</td>
                <td><span class="wr-badge" style="background:rgba(184,126,248,0.15);color:#b87ef8;border:1px solid rgba(184,126,248,0.3)">${winPct(a.w||0,a.games||1)}%</span></td>
                <td>${a.gf||0}득 ${a.ga||0}실</td>
            `;
            tbl.appendChild(tr);
        });
    }

    // ── 4. 날씨별 ────────────────────────────────────────────────
    function renderWeather(data) {
        ["temp","hum","wind"].forEach(k => destroyChart("weather_" + k));
        renderWeatherChart("chart-temp", "weather_temp", data.by_temp || [], "rgba(249,160,63,0.8)",  "rgba(249,100,63,0.8)");
        renderWeatherChart("chart-hum",  "weather_hum",  data.by_hum  || [], "rgba(78,164,248,0.8)",  "rgba(78,200,248,0.8)");
        renderWeatherChart("chart-wind", "weather_wind", data.by_wind || [], "rgba(123,237,159,0.8)", "rgba(123,200,240,0.8)");
    }

    function renderWeatherChart(canvasId, chartKey, rows, colorW, colorL) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        if (!rows.length) { el.closest(".chart-wrap").innerHTML = "<p class='chart-empty'>데이터 없음</p>"; return; }

        const labels = rows.map(r => r.label);
        const wPct   = rows.map(r => winPct(r.w, r.games));
        const dPct   = rows.map(r => winPct(r.d, r.games));
        const lPct   = rows.map(r => winPct(r.l, r.games));
        const avgGf  = rows.map(r => r.games > 0 ? +(r.gf / r.games).toFixed(2) : 0);

        charts[chartKey] = new Chart(el, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label: "승", data: wPct, backgroundColor: colorW, borderRadius: 4, stack: "s" },
                    { label: "무", data: dPct, backgroundColor: "rgba(130,145,165,0.6)", borderRadius: 0, stack: "s" },
                    { label: "패", data: lPct, backgroundColor: "rgba(220,80,80,0.75)", borderRadius: 4, stack: "s" },
                    {
                        label: "평균득점",
                        data: avgGf,
                        type: "line",
                        borderColor: "rgba(255,255,255,0.7)",
                        backgroundColor: "transparent",
                        pointBackgroundColor: "#fff",
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        tension: 0.4,
                        borderWidth: 2,
                        yAxisID: "yRight",
                    }
                ]
            },
            options: mergeOpts({
                plugins: {
                    tooltip: {
                        ...BASE_OPTS.plugins.tooltip,
                        callbacks: {
                            afterBody(ctx) {
                                const r = rows[ctx[0].dataIndex];
                                return [`${r.games}경기  ${r.w}승 ${r.d}무 ${r.l}패`, `득실: ${r.gf}득 ${r.ga}실`];
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, ticks: { color: "#8a9fb8", font: { size: 11 } }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: { stacked: true, min: 0, max: 100, ticks: { color: "#8a9fb8", callback: v => v + "%", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.06)" } },
                    yRight: {
                        position: "right", min: 0, max: 5,
                        ticks: { color: "rgba(255,255,255,0.5)", font: { size: 10 } },
                        grid: { drawOnChartArea: false }
                    }
                }
            })
        });
    }

    // ── 골 타이밍 ──────────────────────────────────────────────────
    function renderGoalTiming(data) {
        destroyChart("goal-timing");
        const el = document.getElementById("chart-goal-timing");
        const summaryEl = document.getElementById("goal-timing-summary");

        if (!data || !data.buckets || (!data.total_for && !data.total_against)) {
            el.closest(".chart-wrap").innerHTML = "<p class='chart-empty'>데이터 없음 (K2 전용)</p>";
            if (summaryEl) summaryEl.innerHTML = "";
            return;
        }

        const labels  = data.buckets.map(b => b.label + "'");
        const forData = data.buckets.map(b => b.for);
        const agData  = data.buckets.map(b => b.against);

        charts["goal-timing"] = new Chart(el, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "득점",
                        data: forData,
                        backgroundColor: "rgba(78,164,248,0.82)",
                        borderColor:     "rgba(78,164,248,1)",
                        borderWidth: 1, borderRadius: 4,
                    },
                    {
                        label: "실점",
                        data: agData,
                        backgroundColor: "rgba(248,90,78,0.75)",
                        borderColor:     "rgba(248,90,78,1)",
                        borderWidth: 1, borderRadius: 4,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: "#c8d0e8", font: { size: 12 }, boxWidth: 14 } },
                    tooltip: {
                        backgroundColor: "rgba(15,20,40,0.92)",
                        titleColor: "#e2e8f0", bodyColor: "#8892b0",
                        callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}골` }
                    }
                },
                scales: {
                    x: { ticks: { color: "#8a9fb8", font: { size: 11 } }, grid: { color: "rgba(255,255,255,0.04)" } },
                    y: { beginAtZero: true, ticks: { color: "#8a9fb8", precision: 0, font: { size: 11 } }, grid: { color: "rgba(255,255,255,0.07)" } }
                }
            }
        });

        if (summaryEl) {
            const peakFor = forData.indexOf(Math.max(...forData));
            const peakAg  = agData.indexOf(Math.max(...agData));
            const diff    = data.total_for - data.total_against;
            const diffStr = diff > 0 ? `+${diff}` : String(diff);
            summaryEl.innerHTML = `
                <span class="gt-stat">총 득점<strong>${data.total_for}</strong></span>
                <span class="gt-stat">총 실점<strong>${data.total_against}</strong></span>
                <span class="gt-stat">득실차<strong class="${diff >= 0 ? "gt-pos" : "gt-neg"}">${diffStr}</strong></span>
                <span class="gt-stat">최다 득점 구간<strong>${labels[peakFor]}</strong></span>
                <span class="gt-stat">최다 실점 구간<strong>${labels[peakAg]}</strong></span>
            `;
        }
    }

})();
