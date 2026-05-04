/* insights.js — 포지션별 인사이트 섹션 */
(function () {
  "use strict";

  let currentYear = "2026";
  let currentLeague = "all";  // "all" | "k1" | "k2"
  let currentPos = "F";

  // 포지션별 다중 정렬 상태: [{ key, dir }, ...] 우선순위 순
  const sortState = {
    F: [{ key: "goals", dir: -1 }],
    M: [{ key: "pass_acc", dir: -1 }],
    D: [{ key: "def_score_p90", dir: -1 }],
  };

  // 정렬 컬럼 정의
  const SORT_COLS = {
    F: [
      { label: "#",        key: null },
      { label: "선수",      key: "name" },
      { label: "구단",      key: "team" },
      { label: "경기",      key: "games" },
      { label: "총 골",     key: "goals" },
      { label: "PK",       key: "pk_goals" },
      { label: "PK제외",   key: "np_goals" },
      { label: "PK제외/90",key: "np_goals_p90" },
      { label: "xG효율",   key: "xg_eff" },
      { label: "평점",      key: "rating" },
    ],
    M: [
      { label: "#",        key: null },
      { label: "선수",      key: "name" },
      { label: "구단",      key: "team" },
      { label: "경기",      key: "games" },
      { label: "패스성공률", key: "pass_acc" },
      { label: "패스/90",  key: "passes_p90" },
      { label: "태클/90",  key: "tackles_p90" },
      { label: "평점",      key: "rating" },
    ],
    D: [
      { label: "#",        key: null },
      { label: "선수",      key: "name" },
      { label: "구단",      key: "team" },
      { label: "경기",      key: "games" },
      { label: "수비점수/90", key: "def_score_p90" },
      { label: "태클/90",  key: "tackles_p90" },
      { label: "클리어/90", key: "clearances_p90" },
      { label: "평점",      key: "rating" },
    ],
  };

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

  /* ── 연도 + 리그 필터 ── */
  function initYearFilter() {
    const wrap = document.getElementById("insights-year-filter");
    if (!wrap) return;
    const years = ["2026", "2025", "2024", "all"];
    const leagues = [
      { v: "all", label: "전체" },
      { v: "k1",  label: "K1" },
      { v: "k2",  label: "K2" },
    ];
    wrap.innerHTML =
      `<div class="ld-filter-row">
         <span class="ld-filter-label">리그</span>
         ${leagues.map(l =>
           `<button class="ld-league-btn${l.v === currentLeague ? " active" : ""}" data-league="${l.v}">${l.label}</button>`
         ).join("")}
       </div>
       <div class="ld-filter-row">
         <span class="ld-filter-label">시즌</span>
         ${years.map(y =>
           `<button class="ld-year-btn${y === currentYear ? " active" : ""}" data-year="${y}">${y === "all" ? "전체" : y}</button>`
         ).join("")}
       </div>`;

    wrap.addEventListener("click", e => {
      const yBtn = e.target.closest(".ld-year-btn");
      const lBtn = e.target.closest(".ld-league-btn");
      if (yBtn) {
        currentYear = yBtn.dataset.year;
        wrap.querySelectorAll(".ld-year-btn").forEach(b => b.classList.toggle("active", b === yBtn));
        loadAll();
      } else if (lBtn) {
        currentLeague = lBtn.dataset.league;
        wrap.querySelectorAll(".ld-league-btn").forEach(b => b.classList.toggle("active", b === lBtn));
        loadAll();
      }
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
    return fetch(`/api/insights/top-performers?year=${currentYear}&league=${currentLeague}`)
      .then(r => r.json())
      .then(data => {
        window._insTopData = data;
        const hasData = (data.F?.length || data.M?.length || data.D?.length) > 0;
        showBlock("ins-panel-top", hasData);
        if (hasData) renderTopTable(data);
      });
  }

  // 다중 정렬: keys 배열 순서대로 비교
  function sortRows(rows, keys) {
    if (!keys.length) return rows;
    return [...rows].sort((a, b) => {
      for (const { key, dir } of keys) {
        const av = a[key] ?? (typeof a[key] === "string" ? "" : -Infinity);
        const bv = b[key] ?? (typeof b[key] === "string" ? "" : -Infinity);
        let cmp = 0;
        if (typeof av === "string") cmp = av.localeCompare(bv);
        else cmp = bv - av;         // 기본 내림차순 기준
        if (cmp !== 0) return dir * cmp;
      }
      return 0;
    });
  }

  function buildThead(pos) {
    const cols  = SORT_COLS[pos];
    const sorts = sortState[pos];  // [{ key, dir }, ...]
    const ths = cols.map(col => {
      if (!col.key) return `<th>#</th>`;
      const idx = sorts.findIndex(s => s.key === col.key);
      const active = idx !== -1;
      const priority = active && sorts.length > 1 ? `<span class="ins-sort-badge">${idx + 1}</span>` : "";
      const arrow = active ? (sorts[idx].dir === -1 ? "▼" : "▲") : "";
      const hint = !active ? `<span class="ins-sort-hint">↕</span>` : "";
      return `<th class="ins-th-sort${active ? " ins-th-active" : ""}" data-key="${col.key}">
        ${col.label}${priority}${active ? ` <span class="ins-sort-arrow">${arrow}</span>` : hint}
      </th>`;
    });
    return `<thead><tr>${ths.join("")}</tr></thead>`;
  }

  function renderTopTable(data) {
    const body = document.getElementById("ins-top-body");
    if (!body || !data) return;
    const raw = data[currentPos] || [];
    if (!raw.length) { body.innerHTML = '<p class="ins-empty">데이터 없음</p>'; return; }

    const rows = sortRows(raw, sortState[currentPos]);

    let tbody = "";
    if (currentPos === "F") {
      rows.forEach((r, i) => {
        const eff = r.xg_eff != null ? `${r.xg_eff > 1 ? "+" : ""}${(r.xg_eff - 1).toFixed(2)}` : "-";
        const effClass = r.xg_eff > 1 ? "ins-pos" : r.xg_eff < 1 ? "ins-neg" : "";
        tbody += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td>${r.goals}</td>
          <td class="ins-team">${r.pk_goals > 0 ? r.pk_goals : "-"}</td>
          <td><strong>${r.np_goals}</strong></td>
          <td>${r.np_goals_p90}</td>
          <td class="${effClass}">${eff}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    } else if (currentPos === "M") {
      rows.forEach((r, i) => {
        tbody += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td><strong>${r.pass_acc ?? "-"}%</strong></td>
          <td>${r.passes_p90}</td><td>${r.tackles_p90}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    } else if (currentPos === "D") {
      rows.forEach((r, i) => {
        tbody += `<tr>
          <td class="ins-rank">${i + 1}</td><td class="ins-name">${r.name}</td>
          <td class="ins-team">${r.team || "-"}</td>
          <td>${r.games}</td><td><strong>${r.def_score_p90}</strong></td>
          <td>${r.tackles_p90}</td><td>${r.clearances_p90}</td><td>${r.rating ?? "-"}</td>
        </tr>`;
      });
    }

    body.innerHTML = `<table class="ins-table">${buildThead(currentPos)}<tbody>${tbody}</tbody></table>`;

    // 헤더 클릭 → 다중 정렬
    // 첫 클릭: 추가(내림차순), 재클릭: 오름차순, 한번 더: 제거
    body.querySelectorAll(".ins-th-sort").forEach(th => {
      th.addEventListener("click", () => {
        const key  = th.dataset.key;
        const sorts = sortState[currentPos];
        const idx  = sorts.findIndex(s => s.key === key);
        if (idx === -1) {
          // 새로 추가 (내림차순)
          sorts.push({ key, dir: -1 });
        } else if (sorts[idx].dir === -1) {
          // 오름차순으로 변경
          sorts[idx].dir = 1;
        } else {
          // 제거
          sorts.splice(idx, 1);
          // 제거 후 뒤 항목들 재번호는 자동
        }
        renderTopTable(window._insTopData);
      });
    });

    // 행 클릭 → 드로어 열기
    body.querySelectorAll("tbody tr").forEach((tr, i) => {
      const r = rows[i];
      tr.classList.add("ins-row-clickable");
      tr.addEventListener("click", () => openDrawer(r.player_id, currentPos));
    });
  }


  /* ══════════════════════════════════════════════════
     선수 상세 드로어
  ══════════════════════════════════════════════════ */
  let drawerRatingChart = null, drawerStatChart = null;

  function openDrawer(playerId, pos) {
    fetch(`/api/insights/player-detail?playerId=${playerId}&pos=${pos}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) return;
        renderDrawer(data);
        document.getElementById("player-drawer").classList.add("open");
        document.getElementById("player-drawer-overlay").classList.add("open");
      });
  }

  function closeDrawer() {
    document.getElementById("player-drawer").classList.remove("open");
    document.getElementById("player-drawer-overlay").classList.remove("open");
    destroyChart(drawerRatingChart); drawerRatingChart = null;
    destroyChart(drawerStatChart);   drawerStatChart = null;
  }

  function renderDrawer(data) {
    document.getElementById("drawer-name").textContent = data.name;
    document.getElementById("drawer-sub").textContent =
      `${data.team || "-"}  ·  ${{ F:"공격수", M:"미드필더", D:"수비수", G:"골키퍼" }[data.pos] || data.pos}  ·  ${data.matches.length}경기`;

    const matches = [...data.matches].reverse(); // 날짜 오름차순
    const labels  = matches.map(m => m.date ? m.date.slice(5) : "");
    const posAvg  = data.pos_avg;

    // ── 평점 차트
    destroyChart(drawerRatingChart);
    const ctxR = document.getElementById("drawer-chart-rating");
    if (ctxR) {
      const ratings = matches.map(m => m.rating);
      drawerRatingChart = new Chart(ctxR, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "경기 평점", data: ratings,
              borderColor: "rgba(100,200,255,0.9)", backgroundColor: "rgba(100,200,255,0.1)",
              borderWidth: 2, pointRadius: 4,
              pointBackgroundColor: ratings.map(v =>
                v == null ? "transparent" : v >= 7.5 ? "#4ade80" : v >= 6.5 ? "#facc15" : "#f87171"),
              spanGaps: true, tension: 0.3,
            },
            posAvg.rating ? {
              label: `포지션 평균 (${posAvg.rating})`,
              data: matches.map(() => posAvg.rating),
              borderColor: "rgba(255,180,60,0.5)", borderWidth: 1.5,
              borderDash: [5, 4], pointRadius: 0,
            } : null,
          ].filter(Boolean),
        },
        options: {
          ...CHART_DEFAULTS,
          scales: {
            x: { ticks: { color: "#888", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.05)" } },
            y: { min: 5, max: 10, ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
          },
        },
      });
    }

    // ── 포지션별 핵심 스탯 차트
    destroyChart(drawerStatChart);
    const ctxS = document.getElementById("drawer-chart-stat");
    const statTitle = document.getElementById("drawer-stat-title");
    if (ctxS) {
      let statDatasets = [];
      let statLabel = "";

      if (data.pos === "F") {
        statLabel = "⚽ 경기별 득점 / xG";
        statTitle.textContent = statLabel;
        statDatasets = [
          { label: "득점", data: matches.map(m => m.goals), backgroundColor: "rgba(74,222,128,0.75)", type: "bar" },
          { label: "xG",  data: matches.map(m => m.xg),    backgroundColor: "rgba(255,200,60,0.4)", type: "bar" },
        ];
      } else if (data.pos === "M") {
        statLabel = "🎯 경기별 패스 성공률 / 키패스";
        statTitle.textContent = statLabel;
        statDatasets = [
          {
            label: "패스성공률(%)", data: matches.map(m => m.pass_acc),
            borderColor: "rgba(100,180,255,0.9)", backgroundColor: "rgba(100,180,255,0.1)",
            borderWidth: 2, pointRadius: 3, type: "line", yAxisID: "yAcc", spanGaps: true, tension: 0.3,
          },
          {
            label: "키패스", data: matches.map(m => m.key_passes),
            backgroundColor: "rgba(255,160,60,0.65)", type: "bar", yAxisID: "yKP",
          },
        ];
      } else if (data.pos === "D") {
        statLabel = "🛡 경기별 수비 점수";
        statTitle.textContent = statLabel;
        statDatasets = [
          {
            label: "수비점수/90", data: matches.map(m => m.def_score),
            borderColor: "rgba(160,120,255,0.9)", backgroundColor: "rgba(160,120,255,0.15)",
            borderWidth: 2, pointRadius: 3, type: "line", tension: 0.3,
          },
          {
            label: "태클", data: matches.map(m => m.tackles),
            backgroundColor: "rgba(100,160,255,0.6)", type: "bar",
          },
        ];
      }

      const extraScales = data.pos === "M" ? {
        yAcc: { position: "left",  min: 0, max: 100, ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
        yKP:  { position: "right", min: 0, ticks: { color: "#aaa" }, grid: { display: false } },
      } : {};

      drawerStatChart = new Chart(ctxS, {
        data: { labels, datasets: statDatasets },
        options: {
          ...CHART_DEFAULTS,
          scales: data.pos === "M" ? {
            x: { ticks: { color: "#888", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.05)" } },
            ...extraScales,
          } : {
            x: { ticks: { color: "#888", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.05)" } },
            y: { min: 0, ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.07)" } },
          },
        },
      });
    }

    // ── 최근 경기 테이블
    const wrap = document.getElementById("drawer-match-table");
    if (wrap) {
      const recent = data.matches.slice(0, 15);
      let html = `<table class="ins-table" style="font-size:0.8rem">
        <thead><tr><th>날짜</th><th>상대</th><th>결과</th><th>출전</th><th>평점</th>`;
      if (data.pos === "F") html += `<th>골</th><th>xG</th><th>도움</th>`;
      if (data.pos === "M") html += `<th>패스%</th><th>키패스</th><th>태클</th>`;
      if (data.pos === "D") html += `<th>태클</th><th>수비점수</th>`;
      html += `</tr></thead><tbody>`;
      recent.forEach(m => {
        const rCls = m.rating >= 7.5 ? "ins-pos" : m.rating && m.rating < 6.5 ? "ins-neg" : "";
        html += `<tr>
          <td>${m.date ? m.date.slice(5) : "-"}</td>
          <td class="ins-team">${m.opponent}</td>
          <td>${m.score}</td>
          <td>${m.mins}'</td>
          <td class="${rCls}">${m.rating ?? "-"}</td>`;
        if (data.pos === "F") html += `<td>${m.goals}</td><td>${m.xg}</td><td>${m.assists}</td>`;
        if (data.pos === "M") html += `<td>${m.pass_acc != null ? m.pass_acc + "%" : "-"}</td><td>${m.key_passes}</td><td>${m.tackles}</td>`;
        if (data.pos === "D") html += `<td>${m.tackles}</td><td>${m.def_score}</td>`;
        html += `</tr>`;
      });
      html += "</tbody></table>";
      wrap.innerHTML = html;
    }
  }

  /* ── 전체 로드 ── */
  function loadAll() {
    loadTopPerformers();
  }

  function init() {
    initYearFilter();
    initPosTab();
    document.getElementById("drawer-close")?.addEventListener("click", closeDrawer);
    document.getElementById("player-drawer-overlay")?.addEventListener("click", closeDrawer);
    loadAll();
  }

  // 드로어 열기 (외부에서 호출)
  window.openPlayerDrawer = openDrawer;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
