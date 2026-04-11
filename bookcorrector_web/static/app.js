const form = document.getElementById("analyze-form");
const fileInput = document.getElementById("file-input");
const textInput = document.getElementById("text-input");
const clearButton = document.getElementById("clear-button");
const resultsShell = document.getElementById("results-shell");
const statsGrid = document.getElementById("stats-grid");
const statusPanel = document.getElementById("status-panel");
const originalView = document.getElementById("original-view");
const correctedView = document.getElementById("corrected-view");
const suggestionsList = document.getElementById("suggestions-list");
const selectionCounter = document.getElementById("selection-counter");
const selectSafeButton = document.getElementById("select-safe-button");
const unselectAllButton = document.getElementById("unselect-all-button");
const exportDocxButton = document.getElementById("export-docx-button");
const suggestionTemplate = document.getElementById("suggestion-template");
const dropzone = document.getElementById("dropzone");

let analysisState = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoadingState(true, "Analyse en cours…");

  const formData = new FormData();
  if (fileInput.files[0]) {
    formData.append("file", fileInput.files[0]);
  }
  if (textInput.value.trim()) {
    formData.append("text", textInput.value.trim());
  }

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Analyse impossible.");
    }
    analysisState = {
      ...payload,
      selectedIds: new Set(payload.selected_ids || []),
    };
    renderAnalysis();
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    setLoadingState(false);
  }
});

clearButton.addEventListener("click", () => {
  fileInput.value = "";
  textInput.value = "";
  analysisState = null;
  resultsShell.hidden = true;
  statusPanel.textContent = "";
});

selectSafeButton.addEventListener("click", () => {
  if (!analysisState) {
    return;
  }
  analysisState.selectedIds = new Set(
    analysisState.issues.filter((issue) => issue.default_selected).map((issue) => issue.id),
  );
  renderAnalysis();
});

unselectAllButton.addEventListener("click", () => {
  if (!analysisState) {
    return;
  }
  analysisState.selectedIds = new Set();
  renderAnalysis();
});

exportDocxButton.addEventListener("click", async () => {
  if (!analysisState) {
    return;
  }

  setLoadingState(true, "Génération du document Word…");
  try {
    const response = await fetch("/api/export-docx", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: analysisState.filename,
        original_text: analysisState.original_text,
        issues: analysisState.issues,
        selected_ids: Array.from(analysisState.selectedIds),
      }),
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.error || "Export impossible.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = analysisState.filename.replace(/\.[^.]+$/, "") + "_corrige.docx";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showStatus("Export Word terminé.");
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    setLoadingState(false);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) {
    const filename = fileInput.files[0].name;
    dropzone.querySelector(".dropzone-title").textContent = filename;
  }
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, () => {
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (!file) {
    return;
  }
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInput.files = dataTransfer.files;
  dropzone.querySelector(".dropzone-title").textContent = file.name;
});

function renderAnalysis() {
  if (!analysisState) {
    return;
  }

  const rendered = computeRenderedState();
  resultsShell.hidden = false;
  renderStats(analysisState.stats);
  renderViews(rendered);
  renderSuggestions();

  const warnings = (analysisState.warnings || []).filter(Boolean);
  const summary = [
    `Document: ${analysisState.filename}`,
    `${analysisState.issues.length} suggestion(s) détectée(s).`,
    warnings.length ? `Notes techniques: ${warnings.join(" | ")}` : "Aucun avertissement technique.",
  ].join("\n");
  showStatus(summary, false);
}

function computeRenderedState() {
  const sortedIssues = [...analysisState.issues].sort((a, b) => a.start - b.start || a.end - b.end);
  const selectedIds = analysisState.selectedIds;
  const originalHtml = renderOriginalText(analysisState.original_text, sortedIssues);
  const appliedIssues = selectNonOverlappingIssues(sortedIssues.filter((issue) => selectedIds.has(issue.id)));
  const correctedSegments = buildCorrectedSegments(analysisState.original_text, appliedIssues);
  const correctedHtml = correctedSegments
    .map((segment) => segment.changed ? `<span class="changed-segment">${escapeHtml(segment.text)}</span>` : escapeHtml(segment.text))
    .join("");

  return {
    originalHtml,
    correctedHtml,
    correctedSegments,
    appliedIssues,
  };
}

function renderStats(stats) {
  statsGrid.innerHTML = "";
  const entries = [
    ["Total", stats.total],
    ["Orthographe", stats.orthographe],
    ["Grammaire", stats.grammaire],
    ["Typographie", stats.typographie],
    ["Style", stats.style],
    ["Registre", stats.registre],
  ];

  entries.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `<div class="stat-value">${value}</div><div class="stat-label">${label}</div>`;
    statsGrid.appendChild(card);
  });
}

function renderViews(rendered) {
  originalView.innerHTML = rendered.originalHtml || "<em>Aucun texte.</em>";
  correctedView.innerHTML = rendered.correctedHtml || "<em>Aucune correction appliquée.</em>";
  selectionCounter.textContent = `${analysisState.selectedIds.size} sélection${analysisState.selectedIds.size > 1 ? "s" : ""}`;
}

function renderSuggestions() {
  suggestionsList.innerHTML = "";

  analysisState.issues.forEach((issue) => {
    const fragment = suggestionTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".suggestion-card");
    const toggle = fragment.querySelector(".suggestion-toggle");

    toggle.checked = analysisState.selectedIds.has(issue.id);
    toggle.disabled = !issue.replacement;
    toggle.addEventListener("change", () => {
      if (toggle.checked) {
        analysisState.selectedIds.add(issue.id);
      } else {
        analysisState.selectedIds.delete(issue.id);
      }
      renderAnalysis();
    });

    fragment.querySelector(".suggestion-category").textContent = issue.category;
    fragment.querySelector(".suggestion-severity").textContent = issue.severity;
    fragment.querySelector(".suggestion-confidence").textContent = `${Math.round((issue.confidence || 0) * 100)}%`;
    fragment.querySelector(".suggestion-message").textContent = issue.message;
    fragment.querySelector(".suggestion-excerpt").textContent = issue.excerpt;
    fragment.querySelector(".suggestion-replacement").textContent = issue.replacement
      ? `Correction proposée: ${issue.replacement}`
      : `Suggestion: ${issue.suggestion || "Aucune correction automatique."}`;

    if (!issue.replacement) {
      card.classList.add("no-auto-fix");
    }

    suggestionsList.appendChild(fragment);
  });
}

function renderOriginalText(text, issues) {
  if (!text) {
    return "";
  }

  let cursor = 0;
  const segments = [];
  issues.forEach((issue) => {
    if (issue.start < cursor) {
      return;
    }
    if (cursor < issue.start) {
      segments.push(escapeHtml(text.slice(cursor, issue.start)));
    }
    const klass = `issue-mark issue-${issue.category}`;
    const tooltip = `${issue.message} ${issue.replacement ? `=> ${issue.replacement}` : issue.suggestion || ""}`.trim();
    segments.push(`<span class="${klass}" title="${escapeHtml(tooltip)}">${escapeHtml(text.slice(issue.start, issue.end))}</span>`);
    cursor = issue.end;
  });
  if (cursor < text.length) {
    segments.push(escapeHtml(text.slice(cursor)));
  }
  return segments.join("");
}

function selectNonOverlappingIssues(issues) {
  const accepted = [];
  issues.forEach((issue) => {
    if (!issue.replacement) {
      return;
    }
    const overlaps = accepted.some((current) => !(issue.end <= current.start || issue.start >= current.end));
    if (!overlaps) {
      accepted.push(issue);
    }
  });
  return accepted;
}

function buildCorrectedSegments(text, issues) {
  const segments = [];
  let cursor = 0;

  issues.forEach((issue) => {
    if (cursor < issue.start) {
      segments.push({ text: text.slice(cursor, issue.start), changed: false });
    }
    segments.push({
      text: issue.replacement || text.slice(issue.start, issue.end),
      changed: Boolean(issue.replacement),
      issueId: issue.id,
      category: issue.category,
    });
    cursor = issue.end;
  });

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), changed: false });
  }

  return segments;
}

function showStatus(message, isError = false) {
  statusPanel.textContent = message;
  statusPanel.style.color = isError ? "#991b1b" : "";
}

function setLoadingState(isLoading, message = "") {
  form.querySelectorAll("button, input, textarea").forEach((element) => {
    element.disabled = isLoading;
  });
  selectSafeButton.disabled = isLoading;
  unselectAllButton.disabled = isLoading;
  exportDocxButton.disabled = isLoading;
  if (message) {
    showStatus(message, false);
  }
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
