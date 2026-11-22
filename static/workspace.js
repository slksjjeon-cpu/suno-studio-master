/* Alternate workspace. Move the real controls, preserving listeners and audio state. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const homes = [];
  const folds = [];
  let modern = false;
  let page = "import";
  let previousVersion = "v25";
  const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const save = (key, value) => { try { localStorage.setItem(key, value); } catch {} };

  function move(node, target) {
    if (!node || !target) return;
    const marker = document.createComment("workspace original position");
    node.before(marker);
    homes.push({ node, marker });
    target.append(node);
  }

  function fold(node, title) {
    if (!node) return;
    const details = document.createElement("details");
    details.className = "ws-fold";
    const summary = document.createElement("summary");
    summary.textContent = title;
    details.append(summary);
    node.before(details);
    move(node, details);
    folds.push(details);
  }

  function selectPage(next, focus = false) {
    page = next;
    document.querySelectorAll("[data-ws-page]").forEach(el => {
      el.hidden = el.dataset.wsPage !== next;
    });
    document.querySelectorAll("[data-ws-nav]").forEach(btn => {
      const active = btn.dataset.wsNav === next;
      btn.classList.toggle("is-selected", active);
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    const titles = { import: ["YOUR NEXT RECORD", "좋은 사운드의 시작.", "링크 하나, 또는 오디오 파일 하나. 나머지는 스튜디오에서."], edit: ["SHAPE YOUR SOUND", "듣고, 다듬고, 비교하세요.", "원본과 실시간 청음을 비교하며 나만의 사운드를 만드세요."], export: ["THE FINAL TAKE", "이제, 완성할 시간.", "전체 곡을 렌더링하고 결과를 비교한 뒤 다운로드하세요."], copyright: ["REFERENCE CHECK", "저작권을 미리 살펴보세요.", "음원 인식과 카탈로그 검색을 통해 참고할 정보를 확인해요."], hum: ["HUM STUDIO", "목소리로 더하는 새로운 색.", "불러온 곡에 허밍을 섞어 새로운 버전을 만드세요."] };
    const title = titles[next];
    $("ws-eyebrow").textContent = title[0];
    $("ws-title").textContent = title[1];
    $("ws-subtitle").textContent = title[2];
    if (next === "hum") window.switchStudioMode?.("hum");
    else window.switchStudioMode?.("suno");
    window.dispatchEvent(new Event("resize"));
    if (focus) $("ws-title").focus({ preventScroll: true });
  }

  function setDesign(next) {
    if (next === modern) return;
    modern = next;
    if (modern) {
      document.body.classList.remove("copyright-page-open");
      previousVersion = document.body.dataset.studioVersion || "v25";
      window.v3Studio?.audioElement?.pause();
      if (window.v3Studio) { window.v3Studio.isPlaying = false; window.v3Studio.updatePlayBtnUi(); }
      window.switchStudioVersion?.("v25", false);
      move($("panel-step-1"), $("ws-import-slot"));
      move($("panel-step-2"), $("ws-listen-slot"));
      move($("panel-step-3"), $("ws-adjust-slot"));
      move($("panel-step-4"), $("ws-results-slot"));
      move($("ws-render-action-group") || $("draft-name-input").parentElement, $("ws-render-slot"));
      move($("view-hum-studio"), $("ws-hum-slot"));
      move($("btn-load-demo"), $("ws-demo-slot"));
      // Reuse the export hub and tools once, together on the output page.
      move($("btn-export-speed-audio").parentElement.parentElement, $("ws-quick-export"));
      move($("btn-open-mv-modal"), $("ws-tools-slot"));
      move($("btn-open-copyright-check"), $("ws-tools-slot"));
      move($("youtube-copyright-modal"), $("ws-copyright-slot"));
      fold($("diag-container"), "분석 리포트 · 템포 / 음압 / 사운드 특성");
      fold($("suno-v6-prompt-card"), "Suno 프롬프트 · 스타일과 가사 보기");
      document.body.classList.add("workspace-modern");
      $("ws-shell").hidden = false;
      selectPage(page);
      if (page === "copyright") window.showCopyrightPage();
    } else {
      for (const { node, marker } of homes.reverse()) { marker.replaceWith(node); }
      homes.length = 0;
      folds.forEach(el => el.remove());
      folds.length = 0;
      document.body.classList.remove("workspace-modern");
      $("ws-shell").hidden = true;
      window.switchStudioMode?.("suno");
      window.switchStudioVersion?.(previousVersion, false);
      if (page === "copyright") window.showCopyrightPage();
    }
    $("ws-design-toggle").textContent = modern ? "기존 디자인 보기 ↗" : "새 디자인 보기 ↗";
    $("ws-design-toggle").setAttribute("aria-pressed", String(modern));
    $("ws-design-caption").textContent = modern ? "STUDIO / WORKSPACE" : "STUDIO / CLASSIC";
    save("studio_workspace_design", modern ? "modern" : "classic");
    window.dispatchEvent(new Event("resize"));
  }

  document.addEventListener("DOMContentLoaded", () => {
    const bar = document.createElement("div");
    bar.id = "ws-design-bar";
    bar.innerHTML = `<span id="ws-design-caption">STUDIO / CLASSIC</span><div><span class="ws-design-hint">같은 곡, 같은 설정. 다른 작업 공간.</span><button type="button" id="ws-theme-toggle" aria-label="다크 모드로 전환" aria-pressed="false">☾ 다크 모드</button><button type="button" id="ws-design-toggle" aria-pressed="false">새 디자인 보기 ↗</button></div>`;
    document.body.prepend(bar);
    const shell = document.createElement("div");
    shell.id = "ws-shell";
    shell.hidden = true;
    shell.innerHTML = `
      <aside class="ws-sidebar">
        <a class="ws-brand" href="#" aria-label="스튜디오 홈">
          <span class="ws-brand-mark">♫</span>
          <span>music<br><b>studio.</b></span>
          <span class="ws-version-badge" id="ws-brand-ver" style="font-size:10px; font-weight:800; font-family:monospace; color:#22d3ee; background:rgba(6,182,212,0.15); border:1px solid rgba(6,182,212,0.3); padding:1px 6px; border-radius:6px; margin-left:auto;">v3.6.0</span>
        </a>
        <div class="ws-sidebar-label">MY WORKSPACE</div>
        <nav aria-label="작업 단계">
          <button type="button" data-ws-nav="import"><span>01</span> 음원 불러오기 <i>↗</i></button>
          <button type="button" data-ws-nav="edit"><span>02</span> 사운드 편집 <i>↗</i></button>
          <button type="button" data-ws-nav="export"><span>03</span> 완성 · 내보내기 <i>↗</i></button>
        </nav>
        <div class="ws-sidebar-label ws-tools-label">EXTRA ROOM</div>
        <button type="button" data-ws-nav="copyright"><span>✓</span> 저작권 참고 진단 <i>↗</i></button>
        <button type="button" data-ws-nav="hum"><span>♫</span> Hum Studio <i>↗</i></button>
        <div class="ws-sidebar-bottom">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;">
            <span style="display:flex; align-items:center; gap:6px;"><span class="ws-live-dot"></span> LOCAL WORKSPACE</span>
            <span id="ws-sidebar-ver" style="font-size:10px; font-family:monospace; font-weight:700; color:#22d3ee;">v3.6.0</span>
          </div>
          <p>당신의 음악에 집중하는 공간.</p>
          <div id="ws-sidebar-updated" style="margin-top:6px; font-size:10.5px; color:#94a3b8; font-family:monospace; display:flex; align-items:center; gap:4px;">
            <i class="fa-regular fa-clock" style="color:#06b6d4; font-size:9.5px;"></i>
            <span>업데이트: 2026.11.23 00:15</span>
          </div>
        </div>
      </aside>
      <div class="ws-main">
        <div class="ws-session">
          <span>WORKSPACE <b>/</b> <span id="ws-track-name">새로운 세션</span></span>
          <div class="ws-session-meta" style="display:inline-flex; align-items:center; gap:8px;">
            <span class="ws-version-pill" id="ws-session-ver" style="font-size:11px; font-family:monospace; font-weight:700; color:#38bdf8; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); padding:2px 8px; border-radius:8px; display:inline-flex; align-items:center; gap:5px;" title="최종 업데이트 날짜와 시간">
              <i class="fa-solid fa-code-branch" style="font-size:10px;"></i>
              <span id="ws-ver-num">v3.6.0</span>
              <span id="ws-ver-date" style="color:#94a3b8; font-weight:500;">· 2026.11.23 00:15</span>
            </span>
            <span id="ws-queue">대기열 0</span>
          </div>
        </div>
        <header class="ws-heading"><p id="ws-eyebrow"></p><h1 id="ws-title" tabindex="-1"></h1><p id="ws-subtitle"></p></header>
        <section data-ws-page="import" aria-label="음원 불러오기">
          <div class="ws-import-grid"><div id="ws-import-slot"></div>
            <aside class="ws-record-card"><div class="ws-record-top"><span>나만의 음악 작업실</span><span>♪</span></div><div class="ws-record" aria-hidden="true"><div class="ws-record-label"><span>♫</span></div></div><div class="ws-record-bottom"><span>음악을 더 나답게,<br><b>쉽고 편하게 완성해요.</b></span></div></aside>
          </div>
          <div class="ws-bottom-row"><div><span class="ws-tiny-label">JUST EXPLORING?</span><p>파일이 없어도 가볍게 시작하세요.</p></div><div id="ws-demo-slot"></div><button type="button" class="ws-link" data-ws-go="edit">편집 화면 살펴보기 →</button></div>
          <div class="ws-process"><div><span>01 / IMPORT</span><h3>음원을 가져오세요</h3><p>Suno · YouTube 링크 또는 로컬 파일</p></div><div><span>02 / REFINE</span><h3>사운드를 다듬으세요</h3><p>구간 청음 · 속도와 음정 · EQ</p></div><div><span>03 / RELEASE</span><h3>당신의 버전으로 완성</h3><p>완곡 렌더링 · 비교 · 다운로드</p></div></div>
        </section>
        <section data-ws-page="edit" hidden aria-label="사운드 편집">
          <div class="ws-edit-toolbar"><span>실시간 청음과 최종 렌더링 결과는 다를 수 있습니다.</span><button type="button" class="ws-primary" data-ws-go="export">완성 · 내보내기로 →</button></div>
          <div class="ws-edit-grid"><div id="ws-listen-slot"></div><div id="ws-adjust-slot"></div></div>
        </section>
        <section data-ws-page="export" hidden aria-label="완성 및 내보내기">
          <div class="ws-export-grid"><div><section class="ws-white-card"><span class="ws-tiny-label">RENDER YOUR MASTER</span><h2>마스터 만들기</h2><p>편집 화면의 EQ · 음압 · 속도 설정을 적용합니다.</p><div id="ws-render-slot"></div></section>
            <details class="ws-fold ws-export-options"><summary>속도·음정만 적용해 빠르게 저장</summary><p>전체 마스터링 체인이 아닌 속도·음정 변환 파일입니다.</p><div id="ws-quick-export"></div></details>
            <section class="ws-white-card ws-extra"><span class="ws-tiny-label">ONE MORE THING</span><h2>음악, 그다음</h2><div id="ws-tools-slot"></div><p>저작권 검사는 비공식 참고 진단입니다.</p></section></div><div id="ws-results-slot"></div></div>
        </section>
        <section data-ws-page="hum" hidden aria-label="허밍 믹서"><div id="ws-hum-slot"></div></section>
        <section data-ws-page="copyright" hidden aria-label="저작권 참고 진단"><div id="ws-copyright-slot"></div></section>
        <footer class="ws-footer">
          <span>MUSIC STUDIO <b id="ws-footer-ver">v3.6.0</b> — MADE FOR YOUR SOUND.</span>
          <span id="ws-footer-updated">최종 업데이트: 2026.11.23 00:15 KST / 로컬 작업 공간</span>
        </footer>
      </div>`;
    bar.after(shell);
    const setTheme = theme => {
      const dark = theme === "dark";
      document.body.dataset.workspaceTheme = dark ? "dark" : "light";
      const button = $("ws-theme-toggle");
      button.textContent = dark ? "☀ 라이트 모드" : "☾ 다크 모드";
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", dark ? "라이트 모드로 전환" : "다크 모드로 전환");
      save("studio_workspace_theme_v3", dark ? "dark" : "light");
      save("studio_workspace_color_mode", dark ? "dark" : "light");
    };
    // User explicit requirement: 다크모드 (기본값) & 브라운 테마 완전 금지
    document.documentElement.setAttribute("data-theme", "1");
    document.body.setAttribute("data-theme", "1");
    try { localStorage.setItem("antigravity_studio_ui_theme", "1"); } catch(e){}
    const storedTheme = read("studio_workspace_theme_v3");
    const activeTheme = storedTheme === "light" ? "light" : "dark";
    setTheme(activeTheme);
    $("ws-theme-toggle").addEventListener("click", () => setTheme(document.body.dataset.workspaceTheme === "dark" ? "light" : "dark"));
    $("ws-design-toggle").addEventListener("click", () => setDesign(!modern));
    shell.querySelector(".ws-brand").addEventListener("click", e => { e.preventDefault(); selectPage("import", true); });
    shell.querySelectorAll("[data-ws-nav], [data-ws-go]").forEach(btn => btn.addEventListener("click", () => {
      const target = btn.dataset.wsNav || btn.dataset.wsGo;
      if (target === "copyright") window.openCopyrightModal();
      else selectPage(target, true);
    }));
    let returnPage = "import";
    window.showCopyrightPage = () => {
      if (page !== "copyright") returnPage = page;
      const mv = $("modal-mv-studio");
      if (mv && !mv.classList.contains("hidden")) window.closeMvStudioModal?.();
      $("youtube-copyright-modal").classList.remove("hidden");
      document.body.style.overflow = "";
      if (modern) selectPage("copyright", true);
      else document.body.classList.add("copyright-page-open");
      window.scrollTo({ top: 0, behavior: "auto" });
    };
    window.leaveCopyrightPage = () => {
      document.body.classList.remove("copyright-page-open");
      if (modern) selectPage(returnPage === "copyright" ? "import" : returnPage, true);
      else {
        $("youtube-copyright-modal").classList.add("hidden");
        page = returnPage === "copyright" ? "import" : returnPage;
      }
    };
    // Keep primary import action and raw MP4 downloader
    $("btn-fetch-suno").onclick = () => window.handleSunoUrlImport();
    $("btn-fetch-suno").querySelector("span").textContent = "음원 불러오기";
    if ($("btn-download-yt-raw")) {
      $("btn-download-yt-raw").onclick = () => window.downloadRawMp4Dedicated?.();
    }
    $("suno-auto-master-toggle").checked = false;
    $("suno-auto-master-toggle").nextElementSibling.textContent = "분석 후 자동 마스터링 (선택)";
    $("suno-url-input").placeholder = "Suno / YouTube 링크 붙여넣기";
    const importLabel = $("suno-url-input").parentElement.parentElement.previousElementSibling.firstElementChild;
    importLabel.textContent = "링크로 음원 불러오기";
    $("btn-export-speed-audio").querySelector("span").textContent = "속도·음정 적용 WAV 저장";
    $("btn-export-speed-audio").title = "속도·음정 변환 WAV 저장 (전체 마스터링은 마스터 만들기에서 실행)";
    // Canvas may have been hidden when analysis finished; redraw at its real size.
    new ResizeObserver(entries => {
      if (entries[0].contentRect.width > 0 && typeof state !== "undefined" && state.audio?.waveform_peaks) {
        drawWaveform(state.audio.waveform_peaks);
        updateSelectionOverlay();
      }
    }).observe($("waveform-container"));
    $("btn-enqueue-full-master").addEventListener("click", () => { if (modern) selectPage("export"); });
    $("btn-goto-step-3").addEventListener("click", () => { if (modern) $("ws-adjust-slot").scrollIntoView({ behavior: "smooth", block: "start" }); });
    // No new polling loop: reflect existing analysis and queue UI updates.
    new MutationObserver(() => {
      const name = $("loaded-track-title").textContent.trim();
      $("ws-track-name").textContent = name && name !== "-" ? name : "새로운 세션";
      $("ws-track-name").title = name;
    }).observe($("loaded-track-title"), { childList: true, subtree: true, characterData: true });
    new MutationObserver(() => { $("ws-queue").textContent = $("queue-badge").textContent; }).observe($("queue-badge"), { childList: true, subtree: true, characterData: true });
    new MutationObserver(() => {
      if (modern && /분석 완료/.test($("analysis-status-pill").textContent) && page === "import") selectPage("edit");
      if (modern && /마스터링 대기열 등록 완료/.test($("analysis-status-pill").textContent)) selectPage("export");
    }).observe($("analysis-status-pill"), { childList: true, subtree: true });
    setDesign(read("studio_workspace_design") !== "classic");
  });
})();
