/* insights.js — 포지션별 인사이트 섹션 */
(function () {
  "use strict";

  let currentYear = "2026";
  let currentPos = "F";
  let xgChart = null, fwdTimeChart = null, fwdOppChart = null;
  let midPassChart = null, defScoreChart = null;

  function shortName(name) {
    if (!name) return "";
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return name;
    return parts[parts.length - 1] + " " + parts[0][0] + ".";
  }

  function destroyChart(c) { if (c) { try { c.destroy(); } catch (_) {} } }

  const CHART_DEFAULTS = {
    plugins: { legend: { labels: { color: "#ccc", font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
      y: { ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
    },
  };

  /* 블록 표시/숨김 */
  function showBlock(id, hasData) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("hidden", !hasData);
  }

  /* ── 연도 필터 ── */
  function initYearFilter() {
    const wrap = document.getElementById("insights-year-filter");
    if (!wrap) return;
    const years = ["2026", "2025", "2024", "all"];
    wrap.innerHTML = years.map(y =>
      `<button class="ld-year-btn${y === currentYear ? " active" : ""}" data-year="${y}">${y === "all" ? "전체" : y}</button>`
    ).join("");
    wrap.addEventListener("click", e => {
      const btn = e.target.closest(".ld-year-btn");
      if (!btn) return;
      currentYear = btn.dataset.year;
      wrap.querySelectorAll(".ld-year-btn").forEach(b => b.classList.toggle("active", b === btn));
      loadAll();
    });
  }

  /* ── 포지션 탭 ── */
  function initPosTab() {
    document.querySelectorAll(".ins-pos-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".ins-pos-tab").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentPos = btn.dataset.pos;
        renderTopTable(window._insTopData);
      });
    });
  }

  /* ══════════════════════════════════════════════════
     1. TOP 퍼포머
  ══════════════════════════════════════════════════ */
  function loadTopPerformers() {
    return fetch(`/api/insights/top-performers?year=${currentYear}`)
      .then(r => r.json())
      .then(data => {
        window._insTopData = data;
        const hasData = (data.F?.length || data.M?.length || data.D?.length) > 0;
        showBlock("ins-panel-top", hasData);
        if (hasData) renderTopTable(data);
      });
  }

  function renderTopTable(data) {
    const body = document.getElementById("ins-top-body");
    if (!body || !data) return;
    const rows = data[currentPos] || [];
    if (!rows.length) { body.innerHTML = '<p class="ins-empty">데이터 없음</p>'; return; }

    let html = "";
    if (currentPos === "F") {
      html = `<table class="ins-table">
        <thead><tr><th>#</th><th>선수</th><th>구단</th><th>경기</th><th>골</th><th>골/90</th><th>xG</th><th>xG효율</th><th>평점</th></tr></thead><tbody>`;
      rows.forEach((r, i) => {
        const eff = r.xg_eff != null ? `${r.xg_eff > 1 ? "+" : ""}${(r.xg_eff - 1).toFixed(2)}` : "-";
        const effClass = r.xg_eff > 1 ? "ins-pos" : r.xg_eff < 1 ? "ins-neg" : "";
        html += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td><strong>${r.goals}</strong></td>
          <td>${r.goals_p90}</td><td>${r.xg}</td>
          <td class="${effClass}">${eff}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    } else if (currentPos === "M") {
      html = `<table class="ins-table">
        <thead><tr><th>#</th><th>선수</th><th>구단</th><th>경기</th><th>패스성공률</th><th>패스/90</th><th>태클/90</th><th>평점</th></tr></thead><tbody>`;
      rows.forEach((r, i) => {
        html += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td><strong>${r.pass_acc ?? "-"}%</strong></td>
          <td>${r.passes_p90}</td><td>${r.tackles_p90}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    } else if (currentPos === "D") {
      html = `<table class="ins-table">
        <thead><tr><th>#</th><th>선수</th><th>구단</th><th>경기</th><th>수비점수/90</th><th>태클/90</th><th>클리어/90</th><th>평점</th></tr></thead><tbody>`;
      rows.forEach((r, i) => {
        html += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td><strong>${r.def_score_p90}</strong></td>
          <td>${r.tackles_p90}</td><td>${r.clearances_p90}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    }
    html += "</tbody></table>";
    body.innerHTML = html;
  }

  /* ══════════════════════════════════════════════════
     2. xG 효율
  ══════════════════════════════════════════════════ */
  function loadXgEfficiency() {
    return fetch(`/api/insights/xg-efficiency?year=${currentYear}`)
      .then(r => r.json())
      .then(data => {
        showBlock("ins-panel-xg", data.length > 0);
        if (data.length) renderXgChart(data);
        else destroyChart(xgChart);
      });
  }

  function renderXgChart(data) {
    destroyChart(xgChart);
    const ctx = document.getElementById("ins-chart-xg");
    if (!ctx) return;
    const labels = data.map(d => shortName(d.name));
    const diffs = data.map(d => d.diff);
    xgChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "실제 득점", data: data.map(d => d.goals), backgroundColor: "rgba(100,200,100,0.75)", order: 2 },
          { label: "xG", data: data.map(d => d.xg), backgroundColor: "rgba(255,180,50,0.55)", order: 3 },
          {
            label: "득점-xG", data: diffs, type: "line",
            borderColor: "rgba(100,180,255,0.9)", backgroundColor: "transparent",
            pointBackgroundColor: diffs.map(v => v >= 0 ? "rgba(100,220,100,0.9)" : "rgba(255,100,100,0.9)"),
            borderWidth: 2, pointRadius: 5, order: 1,
          },
        ],
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: { callbacks: { afterBody: (items) => {
            const d = data[items[0].dataIndex];
            return [
              `구단: ${d.team || "-"}`,
              `xG 효율: ${d.xg > 0 ? (d.goals / d.xg).toFixed(2) : "-"}`,
              `슈팅: ${d.shots}회`, `경기: ${d.games}`,
            ];
          }}},
        },
      },
    });
  }

  /* ══════════════════════════════════════════════════
     3. 공격수 골 분석
  ══════════════════════════════════════════════════ */
  function loadFwdGoalsList() {
    return fetch(`/api/insights/forward-goals?year=${currentYear}`)
      .then(r => r.json())
      .then(list => {
        showBlock("ins-panel-fwd-goals", list.length > 0);
        if (!list.length) { destroyChart(fwdTimeChart); destroyChart(fwdOppChart); return; }
        const sel = document.getElementById("ins-fwd-select");
        if (!sel) return;
        sel.innerHTML = list.map(p => `<option value="${p.player_id}">${p.name}${p.team ? " · " + p.team : ""} (${p.goals}골)</option>`).join("");
        loadFwdGoalsDetail(list[0].player_id);
      });
  }

  function loadFwdGoalsDetail(playerId) {
    fetch(`/api/insights/forward-goals?playerId=${playerId}`)
      .then(r => r.json())
      .then(data => {
        destroyChart(fwdTimeChart);
        const ctxTime = document.getElementById("ins-chart-fwd-time");
        if (ctxTime) {
          fwdTimeChart = new Chart(ctxTime, {
            type: "bar",
            data: {
              labels: data.time_bands.map(b => b.band),
              datasets: [{ label: "골", data: data.time_bands.map(b => b.goals),
                backgroundColor: data.time_bands.map(b =>
                  b.goals === Math.max(...data.time_bands.map(x => x.goals))
                    ? "rgba(255,200,50,0.85)" : "rgba(100,180,255,0.6)") }],
            },
            options: { ...CHART_DEFAULTS, plugins: { legend: { display: false } } },
          });
        }
        destroyChart(fwdOppChart);
        const ctxOpp = document.getElementById("ins-chart-fwd-opp");
        const oppData = data.by_opponent.slice(0, 10);
        if (ctxOpp && oppData.length) {
          fwdOppChart = new Chart(ctxOpp, {
            type: "bar",
            data: { labels: oppData.map(o => o.opponent),
              datasets: [{ label: "골", data: oppData.map(o => o.goals), backgroundColor: "rgba(255,120,80,0.75)" }] },
            options: { ...CHART_DEFAULTS, indexAxis: "y", plugins: { legend: { display: false } } },
          });
        }
      });
  }

  /* ══════════════════════════════════════════════════
     4. 미드필더 패스 성공률
  ══════════════════════════════════════════════════ */
  function loadMidPass() {
    return fetch(`/api/insights/midfielder-pass?year=${currentYear}`)
      .then(r => r.json())
      .then(data => {
        showBlock("ins-panel-mid-pass", data.length > 0);
        if (data.length) renderMidPassChart(data);
        else destroyChart(midPassChart);
      });
  }

  function renderMidPassChart(data) {
    destroyChart(midPassChart);
    const ctx = document.getElementById("ins-chart-mid-pass");
    if (!ctx) return;
    midPassChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map(d => shortName(d.name)),
        datasets: [
          { label: "패스 성공률(%)", data: data.map(d => d.pass_acc),
            backgroundColor: data.map(d => d.pass_acc >= 85 ? "rgba(80,220,120,0.8)" : d.pass_acc >= 75 ? "rgba(100,180,255,0.7)" : "rgba(255,160,60,0.7)"),
            yAxisID: "yAcc" },
          { label: "패스/90", data: data.map(d => d.passes_p90), type: "line",
            borderColor: "rgba(255,220,80,0.8)", backgroundColor: "transparent",
            pointRadius: 3, borderWidth: 1.5, yAxisID: "yP90" },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { labels: { color: "#ccc", font: { size: 11 } } },
          tooltip: { callbacks: { afterBody: (items) => {
            const d = data[items[0].dataIndex];
            return [`구단: ${d.team || "-"}`, `총 패스: ${d.total_passes}`, `성공: ${d.accurate_passes}`, `경기: ${d.games}`, `평점: ${d.rating ?? "-"}`];
          }}}},
        scales: {
          x: { display: false },
          y: { ticks: { color: "#aaa", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.07)" } },
          yAcc: { position: "bottom", display: false, min: 0, max: 100 },
          yP90: { position: "right", display: false },
        },
      },
    });
  }

  /* ══════════════════════════════════════════════════
     5. 수비수 종합 기여도
  ══════════════════════════════════════════════════ */
  function loadDefScore() {
    return fetch(`/api/insights/defender-score?year=${currentYear}`)
      .then(r => r.json())
      .then(data => {
        showBlock("ins-panel-def-score", data.length > 0);
        if (data.length) renderDefScoreChart(data);
        else destroyChart(defScoreChart);
      });
  }

  function renderDefScoreChart(data) {
    destroyChart(defScoreChart);
    const ctx = document.getElementById("ins-chart-def-score");
    if (!ctx) return;
    defScoreChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map(d => shortName(d.name)),
        datasets: [
          { label: "태클", data: data.map(d => +(d.tackles / d.mins * 90).toFixed(2)), backgroundColor: "rgba(100,160,255,0.75)", stack: "s" },
          { label: "인터셉션×1.5", data: data.map(d => +(d.interceptions * 1.5 / d.mins * 90).toFixed(2)), backgroundColor: "rgba(80,220,160,0.75)", stack: "s" },
          { label: "클리어런스", data: data.map(d => +(d.clearances / d.mins * 90).toFixed(2)), backgroundColor: "rgba(255,200,60,0.75)", stack: "s" },
          { label: "공중볼승리", data: data.map(d => +(d.aerial_won / d.mins * 90).toFixed(2)), backgroundColor: "rgba(255,120,80,0.75)", stack: "s" },
          { label: "듀얼승리", data: data.map(d => +(d.duel_won / d.mins * 90).toFixed(2)), backgroundColor: "rgba(200,100,255,0.7)", stack: "s" },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { labels: { color: "#ccc", font: { size: 11 } } },
          tooltip: { callbacks: { afterBody: (items) => {
            const d = data[items[0].dataIndex];
            return [`구단: ${d.team || "-"}`, `종합점수/90: ${d.def_score}`, `경기: ${d.games} | 평점: ${d.rating ?? "-"}`];
          }}}},
        scales: {
          x: { stacked: true, ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
          y: { stacked: true, ticks: { color: "#aaa", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.07)" } },
        },
      },
    });

    const tableWrap = document.getElementById("ins-def-table-wrap");
    if (tableWrap) {
      let html = `<table class="ins-table">
        <thead><tr><th>#</th><th>선수</th><th>구단</th><th>경기</th><th>점수/90</th><th>태클</th><th>인터셉션</th><th>클리어</th><th>공중볼</th><th>듀얼</th><th>평점</th></tr></thead><tbody>`;
      data.forEach((d, i) => {
        html += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${d.name}</td>
          <td class="ins-team">${d.team || "-"}</td>
          <td>${d.games}</td><td><strong>${d.def_score}</strong></td>
          <td>${d.tackles}</td><td>${d.interceptions}</td><td>${d.clearances}</td>
          <td>${d.aerial_won}</td><td>${d.duel_won}</td><td>${d.rating ?? "-"}</td>
        </tr>`;
      });
      html += "</tbody></table>";
      tableWrap.innerHTML = html;
    }
  }

  /* ── 전체 로드 ── */
  function loadAll() {
    loadTopPerformers();
    loadXgEfficiency();
    loadFwdGoalsList();
    loadMidPass();
    loadDefScore();
  }

  function init() {
    initYearFilter();
    initPosTab();
    document.getElementById("ins-fwd-select")?.addEventListener("change", e => loadFwdGoalsDetail(e.target.value));
    loadAll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
