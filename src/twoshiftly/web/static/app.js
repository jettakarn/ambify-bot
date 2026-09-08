(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileName = document.getElementById("file-name");
  const stepUpload = document.getElementById("step-upload");
  const stepProgress = document.getElementById("step-progress");
  const stepSearch = document.getElementById("step-search");
  const stepPreview = document.getElementById("step-preview");
  const progressText = document.getElementById("progress-text");
  const progressFill = document.getElementById("progress-fill");
  const peopleList = document.getElementById("people-list");
  const rangeText = document.getElementById("range-text");
  const searchInput = document.getElementById("search-input");
  const searchHint = document.getElementById("search-hint");
  const warnings = document.getElementById("warnings");
  const resetBtn = document.getElementById("reset-btn");
  const backSearch = document.getElementById("back-search");
  const previewTitle = document.getElementById("preview-title");
  const previewSub = document.getElementById("preview-sub");
  const shiftList = document.getElementById("shift-list");
  const downloadIcsBtn = document.getElementById("download-ics");
  const copyTextBtn = document.getElementById("copy-text");
  const copyStatus = document.getElementById("copy-status");
  const errorEl = document.getElementById("error");

  let jobId = null;
  let pollTimer = null;
  let employees = [];
  let selected = null;
  let schedule = null;

  function showError(message) {
    errorEl.hidden = !message;
    errorEl.textContent = message || "";
  }

  function showStep(step) {
    stepUpload.hidden = step !== "upload";
    stepProgress.hidden = step !== "progress";
    stepSearch.hidden = step !== "search";
    stepPreview.hidden = step !== "preview";
  }

  function reset() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    jobId = null;
    employees = [];
    selected = null;
    schedule = null;
    fileInput.value = "";
    fileName.hidden = true;
    fileName.textContent = "";
    searchInput.value = "";
    peopleList.innerHTML = "";
    peopleList.hidden = true;
    searchHint.hidden = false;
    searchHint.textContent = "輸入至少一個字開始搜尋";
    warnings.hidden = true;
    warnings.textContent = "";
    shiftList.innerHTML = "";
    copyStatus.hidden = true;
    progressFill.style.width = "0%";
    showError("");
    showStep("upload");
  }

  function goBackSearch() {
    selected = null;
    schedule = null;
    shiftList.innerHTML = "";
    copyStatus.hidden = true;
    showError("");
    showStep("search");
    searchInput.focus();
    runSearch();
  }

  async function uploadFile(file) {
    showError("");
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      showError("請選擇 PDF 檔案。");
      return;
    }

    fileName.hidden = false;
    fileName.textContent = file.name;
    showStep("progress");
    progressText.textContent = "正在上傳…";
    progressFill.style.width = "5%";

    const form = new FormData();
    form.append("file", file);

    let accepted;
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "上傳失敗");
      }
      accepted = await res.json();
    } catch (err) {
      showStep("upload");
      showError(err.message || "上傳失敗");
      return;
    }

    jobId = accepted.job_id;
    progressText.textContent = "開始辨識班表…";
    pollTimer = setInterval(pollJob, 500);
    pollJob();
  }

  async function pollJob() {
    if (!jobId) return;
    try {
      const res = await fetch(`/api/jobs/${jobId}/progress`);
      if (!res.ok) throw new Error("無法取得進度");
      const data = await res.json();

      if (data.total_pages > 0) {
        const pct = Math.max(8, Math.round((data.current_page / data.total_pages) * 100));
        progressFill.style.width = `${pct}%`;
        progressText.textContent = `正在讀取第 ${data.current_page}/${data.total_pages} 頁…`;
      }

      if (data.status === "ready") {
        clearInterval(pollTimer);
        pollTimer = null;
        progressFill.style.width = "100%";
        enterSearch(data);
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        pollTimer = null;
        showStep("upload");
        showError(data.error || "辨識失敗");
      }
    } catch (err) {
      clearInterval(pollTimer);
      pollTimer = null;
      showStep("upload");
      showError(err.message || "進度查詢失敗");
    }
  }

  function enterSearch(data) {
    employees = data.employees || [];
    showStep("search");
    if (data.date_start && data.date_end) {
      rangeText.textContent = `班表日期 ${data.date_start} ～ ${data.date_end}`;
    } else {
      rangeText.textContent = "輸入暱稱或員工代號查詢";
    }

    if (!employees.length) {
      showError("班表內找不到員工。");
    }

    if (data.warnings && data.warnings.length) {
      warnings.hidden = false;
      warnings.textContent = `提醒：${data.warnings.slice(0, 5).join("；")}`;
    } else {
      warnings.hidden = true;
    }

    searchInput.value = "";
    peopleList.hidden = true;
    peopleList.innerHTML = "";
    searchHint.hidden = false;
    searchHint.textContent = "輸入至少一個字開始搜尋";
    searchInput.focus();
  }

  function runSearch() {
    const q = searchInput.value.trim().toLowerCase();
    peopleList.innerHTML = "";

    if (!q) {
      peopleList.hidden = true;
      searchHint.hidden = false;
      searchHint.textContent = "輸入至少一個字開始搜尋";
      return;
    }

    const matches = employees.filter(
      (p) =>
        p.nickname.toLowerCase().includes(q) ||
        String(p.employee_id).toLowerCase().includes(q)
    );

    if (!matches.length) {
      peopleList.hidden = true;
      searchHint.hidden = false;
      searchHint.textContent = "找不到符合的員工";
      return;
    }

    searchHint.hidden = true;
    peopleList.hidden = false;
    for (const person of matches) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.innerHTML = `<span>${escapeHtml(person.nickname)}</span><span class="id">${escapeHtml(person.employee_id)}</span>`;
      btn.addEventListener("click", () => selectPerson(person));
      li.appendChild(btn);
      peopleList.appendChild(li);
    }
  }

  async function selectPerson(person) {
    showError("");
    selected = person;
    copyStatus.hidden = true;
    try {
      const res = await fetch(`/api/jobs/${jobId}/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee: person.nickname,
          employee_id: person.employee_id,
          infer_days_off: true,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "無法取得班表");
      }
      schedule = await res.json();
      renderPreview();
    } catch (err) {
      showError(err.message || "無法取得班表");
    }
  }

  function renderPreview() {
    showStep("preview");
    previewTitle.textContent = schedule.employee_name;
    previewSub.textContent = `員工代號 ${schedule.employee_id || "—"} · ${schedule.year_month}`;

    shiftList.innerHTML = "";
    for (const shift of schedule.shifts) {
      const li = document.createElement("li");
      li.className = shift.is_day_off ? "is-off" : "is-work";
      const date = shift.date;
      const time = shift.is_day_off
        ? "休假 OFF"
        : `${shift.start_time || "—"}–${shift.end_time || "—"}`;
      li.innerHTML = `<span class="shift-date">${escapeHtml(date)}</span><span class="shift-time">${escapeHtml(time)}</span>`;
      shiftList.appendChild(li);
    }
  }

  function schedulePlainText() {
    if (!schedule) return "";
    const lines = [
      `${schedule.employee_name}（${schedule.employee_id || ""}）`,
      `期間 ${schedule.year_month}`,
      "",
    ];
    for (const shift of schedule.shifts) {
      if (shift.is_day_off) {
        lines.push(`${shift.date} 休假 OFF`);
      } else {
        lines.push(
          `${shift.date} ${shift.start_time || ""}-${shift.end_time || ""}`.trim()
        );
      }
    }
    return lines.join("\n");
  }

  async function downloadIcs() {
    if (!selected) return;
    showError("");
    try {
      const res = await fetch(`/api/jobs/${jobId}/ics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee: selected.nickname,
          employee_id: selected.employee_id,
          infer_days_off: true,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "下載失敗");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safe = selected.nickname.toLowerCase().replace(/\s+/g, "-");
      a.href = url;
      a.download = `${safe}-roster.ics`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showError(err.message || "下載失敗");
    }
  }

  async function copyText() {
    const text = schedulePlainText();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copyStatus.hidden = false;
      copyStatus.textContent = "已複製到剪貼簿";
    } catch {
      copyStatus.hidden = false;
      copyStatus.textContent = "複製失敗，請手動選取文字";
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("is-drag");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("is-drag"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("is-drag");
    uploadFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => uploadFile(fileInput.files[0]));
  searchInput.addEventListener("input", runSearch);
  resetBtn.addEventListener("click", reset);
  backSearch.addEventListener("click", goBackSearch);
  downloadIcsBtn.addEventListener("click", downloadIcs);
  copyTextBtn.addEventListener("click", copyText);
})();
