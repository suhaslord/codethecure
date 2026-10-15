import { browserAPI, imageSource } from "./browser-client.mjs";
const $ = (selector) => document.querySelector(selector);
const percent = (value, digits = 1) =>
  value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
const signed = (value, digits = 1) =>
  `${value < 0 ? "−" : "+"}${Math.abs(value).toFixed(digits)}`;
const names = ["Malignant", "Normal / benign"];
const stressNames = {
  gain_down: "Reduced gain",
  gain_up: "Increased gain",
  speckle: "Speckle noise",
  shadow: "Shadow attenuation",
};
const stressColors = {
  gain_down: "#a04435",
  gain_up: "#b17c32",
  speckle: "#4d6a9a",
  shadow: "#256c57",
};
const state = {
  samples: [],
  report: null,
  selected: 0,
  result: null,
  queue: new Map(),
  request: 0,
  busy: false,
  batch: false,
  storageKey: "",
  dirty: false,
};
const settings = () => ({
  gain: Number($("#gain").value),
  speckle: Number($("#speckle").value),
  shadow: Number($("#shadow").value),
});
const queueKey = (result) =>
  JSON.stringify([
    result.sample.id,
    result.settings.gain,
    result.settings.speckle,
    result.settings.shadow,
  ]);
const settingsLabel = (s) =>
  `Gain ${signed(s.gain, 0)} dB · Speckle ${s.speckle.toFixed(2)} σ · Shadow ${percent(s.shadow, 0)}`;
const escapeHTML = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );

async function api(path, payload, signal) {
  if (window.GAINGUARD_STATIC) return browserAPI(path, payload);
  const response = await fetch(
    path,
    payload === undefined
      ? { signal }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal,
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.error || `Request failed (${response.status}).`);
  return result;
}

function download(value, filename) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function experimentExport(result) {
  const { original_image, transformed_image, ...data } = result;
  return {
    ...data,
    model_sha256: state.report.model.sha256,
    dataset: state.report.dataset,
    review_policy: state.report.review_policy,
    research_only: true,
  };
}

function saveQueue() {
  try {
    // Store only metadata; pixels and inference results are reconstructed on inspection.
    sessionStorage.setItem(
      state.storageKey,
      JSON.stringify(
        [...state.queue.values()].map((entry) => ({
          data: experimentExport(entry.data),
          reviewed: entry.reviewed,
        })),
      ),
    );
  } catch {
    $("#batch-status").textContent =
      "Browser storage is unavailable. The queue remains available until this page reloads; export it to keep a copy.";
  }
  $("#queue-count").textContent = state.queue.size;
}

function remember(result) {
  if (!result.flagged) return;
  const key = queueKey(result);
  state.queue.set(key, {
    data: result,
    reviewed: state.queue.get(key)?.reviewed || false,
  });
  saveQueue();
}

function renderSamples() {
  const query = $("#sample-search").value.trim().toLowerCase();
  const filter = $("#sample-filter").value;
  const samples = state.samples.filter(
    (sample) =>
      sample.name.toLowerCase().includes(query) &&
      (filter === "all" ||
        (filter === "malignant" && sample.label === 0) ||
        (filter === "benign" && sample.label === 1) ||
        (filter === "error" && !sample.correct)),
  );
  $("#sample-list").innerHTML = samples.length
    ? samples
        .map(
          (sample) =>
            `<button class="sample-button" data-sample="${sample.id}" aria-pressed="${sample.id === state.selected}" aria-label="${sample.name}, dataset label ${names[sample.label]}${sample.correct ? "" : ", clean-model error"}"><img src="${imageSource(sample.id)}" alt="" loading="lazy"><span><strong>${sample.name}</strong><small>${names[sample.label]}</small></span>${sample.correct ? "" : '<i class="sample-indicator" title="Clean-model error"></i>'}</button>`,
        )
        .join("")
    : '<p class="no-samples">No matching images. Try a different ID or filter.</p>';
}

function updateControlLabels() {
  const s = settings();
  $("#gain-value").textContent = `${signed(s.gain, 0)} dB`;
  $("#speckle-value").textContent = `${s.speckle.toFixed(2)} σ`;
  $("#shadow-value").textContent = percent(s.shadow, 0);
  $("#batch-settings").textContent = settingsLabel(s);
}

function markDirty() {
  updateControlLabels();
  state.dirty = true;
  $(".controls").classList.add("dirty");
  $("#experiment-status").textContent =
    "Settings changed. Run the stress test to update results.";
  $("#stressed-state").textContent = "Previous run · settings changed";
  $("#export-experiment").disabled = true;
}

function route() {
  const hash = location.hash.slice(1) || "lab";
  const view = ["lab", "benchmark", "queue", "methods"].includes(hash)
    ? hash
    : "methods";
  document.querySelectorAll(".view").forEach((node) => {
    node.hidden = node.id !== `view-${view}`;
  });
  document.querySelectorAll("[data-route]").forEach((node) => {
    if (node.dataset.route === view) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  });
  if (view === "queue") {
    renderQueue();
    updateControlLabels();
  }
  document.title = `GainGuard — ${{ lab: "Experiment lab", benchmark: "Benchmark", queue: "Review queue", methods: "Methods" }[view]}`;
  if (
    ![
      "data-method",
      "model-method",
      "stress-method",
      "review-method",
      "limits-method",
    ].includes(hash)
  )
    window.scrollTo(0, 0);
  else
    requestAnimationFrame(() =>
      document.getElementById(hash)?.scrollIntoView(),
    );
}

function chartFrame(width, height, inner, label, description = "") {
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHTML(label)}"><title>${escapeHTML(label)}</title>${description ? `<desc>${escapeHTML(description)}</desc>` : ""}${inner}</svg>`;
}

function renderSweep(result) {
  const width = 480,
    height = 170,
    left = 37,
    right = 14,
    top = 15,
    bottom = 25;
  const x = (v) => left + v * (width - left - right);
  const y = (v) => top + (1 - v) * (height - top - bottom);
  const ticks = [0, 0.5, 1];
  let inner = ticks
    .map(
      (tick) =>
        `<line x1="${left}" y1="${y(tick)}" x2="${width - right}" y2="${y(tick)}" stroke="${tick === 0.5 ? "#b8c4b7" : "#e2e7de"}" ${tick === 0.5 ? 'stroke-dasharray="4 4"' : ""}/><text class="chart-number" x="${left - 8}" y="${y(tick) + 3}" text-anchor="end">${percent(tick, 0)}</text>`,
    )
    .join("");
  const points = result.sweep
    .map((p) => `${x(p.strength)},${y(p.malignant_probability)}`)
    .join(" ");
  inner += `<polyline points="${points}" fill="none" stroke="#256c57" stroke-width="2.5" stroke-linejoin="round"/>`;
  inner += result.sweep
    .map(
      (p) =>
        `<circle cx="${x(p.strength)}" cy="${y(p.malignant_probability)}" r="${p.strength === 1 ? 4 : 2.5}" fill="#256c57"><title>${percent(p.strength, 0)} stress: ${percent(p.malignant_probability)} malignant-class probability${p.flagged ? "; flagged for review" : ""}</title></circle>`,
    )
    .join("");
  inner += `<text class="chart-number" x="${x(0)}" y="${height - 6}" text-anchor="middle">0%</text><text class="chart-number" x="${x(0.5)}" y="${height - 6}" text-anchor="middle">50%</text><text class="chart-number" x="${x(1)}" y="${height - 6}" text-anchor="middle">100%</text>`;
  $("#sweep-chart").innerHTML = chartFrame(
    width,
    height,
    inner,
    "Malignant-class probability as stress increases",
    result.sweep
      .map(
        (p) =>
          `${percent(p.strength, 0)} stress: ${percent(p.malignant_probability)}`,
      )
      .join("; "),
  );
}

function renderResult(result) {
  const sample = result.sample;
  $("#sample-name").textContent = sample.name;
  $("#sample-ground-truth").textContent = `Dataset label: ${sample.label_name}`;
  $("#original-image").src = result.original_image;
  $("#transformed-image").src = result.transformed_image;
  $("#original-prediction").textContent = names[sample.prediction];
  $("#changed-prediction").textContent = names[result.prediction];
  $("#original-image").hidden = false;
  $("#transformed-image").hidden = false;
  $("#original-bar").style.transform = `scaleX(${sample.confidence})`;
  $("#changed-bar").style.transform = `scaleX(${result.confidence})`;
  $("#original-bar").classList.toggle("error-bar", !sample.correct);
  $("#changed-bar").classList.toggle("error-bar", !result.correct);
  $("#original-confidence").innerHTML =
    `<strong>${percent(sample.confidence)}</strong><span>confidence · ${sample.correct ? "matches" : "differs from"} dataset label</span>`;
  $("#changed-confidence").innerHTML =
    `<strong>${percent(result.confidence)}</strong><span>confidence · ${result.correct ? "matches" : "differs from"} dataset label</span>`;
  $("#stressed-state").textContent =
    `${signed(result.settings.gain, 0)} dB · σ ${result.settings.speckle.toFixed(2)} · ${percent(result.settings.shadow, 0)}`;
  const flag = $("#review-result");
  flag.classList.toggle("stable", !result.flagged);
  flag.innerHTML = `<div class="review-title"><svg viewBox="0 0 20 20" aria-hidden="true">${result.flagged ? '<path d="M4 17V3m0 1h11l-2 4 2 4H4"/>' : '<circle cx="10" cy="10" r="7"/><path d="m6.5 10 2.5 2.5 4.5-5"/>'}</svg>${result.flagged ? "Flagged for human review" : "No review trigger detected"}</div><p>${result.flagged ? "This result crossed the fixed research review policy." : "The selected change did not cross the fixed policy. A stable prediction can still be wrong."}</p>${result.flagged ? `<ul class="review-reasons">${result.reasons.map((reason) => `<li>${escapeHTML(reason)}</li>`).join("")}</ul>` : ""}<div class="result-stats"><div><strong>${signed(result.probability_shift * 100)}<span class="stat-unit">pp</span></strong><span>Malignant-class probability shift</span></div><div><strong>${result.entropy.toFixed(2)}<span class="stat-unit">bits</span></strong><span>Predictive entropy · 0–1</span></div></div><button class="text-button" id="open-review-policy">View review policy <svg class="outbound-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M5 5h10v10"/></svg></button>`;
  $("#open-review-policy").addEventListener("click", () => {
    location.hash = "review-method";
  });
  renderSweep(result);
  $("#model-fingerprint").textContent =
    `MODEL ${state.report.model.sha256.slice(0, 12)} · SEED ${result.settings.seed}`;
}

async function runExperiment(index = state.selected) {
  const request = ++state.request;
  state.selected = index;
  const config = settings();
  state.busy = true;
  state.dirty = false;
  $(".controls").classList.remove("dirty");
  $("#run-experiment").disabled = true;
  $("#export-experiment").disabled = true;
  $("#experiment-error").hidden = true;
  $("#experiment-status").textContent = "Running model on 9 stress levels…";
  $("#result-area").setAttribute("aria-busy", "true");
  renderSamples();
  try {
    const result = await api("/api/experiment", {
      sample_id: index,
      ...config,
    });
    if (request !== state.request) return;
    state.result = result;
    renderResult(result);
    remember(result);
    const changedDuringRun =
      JSON.stringify(settings()) !== JSON.stringify(config);
    if (changedDuringRun) markDirty();
    else {
      $("#experiment-status").textContent =
        "Complete · 9 real model passes · fixed noise seed";
      $("#export-experiment").disabled = false;
    }
  } catch (error) {
    if (request !== state.request) return;
    $("#experiment-error").textContent =
      `Could not run the experiment: ${error.message} Check that the Python server is running, then retry.`;
    $("#experiment-error").hidden = false;
    $("#experiment-status").textContent =
      "Experiment failed. Previous results have not been updated.";
    $("#stressed-state").textContent = "Previous result · request failed";
  } finally {
    if (request === state.request) {
      state.busy = false;
      $("#run-experiment").disabled = false;
      $("#result-area").removeAttribute("aria-busy");
    }
  }
}

function conditionLabel(condition) {
  const { stress, severity } = condition;
  return {
    gain_down: `Gain −${severity * 3} dB`,
    gain_up: `Gain +${severity * 3} dB`,
    speckle: `Speckle σ ${(severity * 0.15).toFixed(2)}`,
    shadow: `Shadow ${severity * 25}%`,
  }[stress];
}

function renderThresholdStudy() {
  const study = state.report.threshold_study;
  if (!study) {
    $(".threshold-study").hidden = true;
    return;
  }
  const conditionSelect = $("#threshold-condition");
  conditionSelect.innerHTML = study.curves.validation
    .map((entry) => {
      const [stress, level] = entry.condition.split(":");
      const name =
        stress === "clean"
          ? "Clean reference"
          : conditionLabel({ stress, severity: Number(level) });
      return `<option value="${entry.condition}">${name}</option>`;
    })
    .join("");
  conditionSelect.value = "gain_down:2";
  $("#selected-policy-summary").innerHTML = Object.entries(study.selected)
    .map(([name, p]) =>
      p
        ? `<div><h3>${name === "combined" ? "Validation-selected combined rule" : "Validation-selected confidence-only rule"}</h3><p>Confidence &lt;<strong>${percent(p.confidence_below, 0)}</strong>${p.probability_shift_above == null ? "" : `, or flip, or probability shift &gt;${(p.probability_shift_above * 100).toFixed(0)} pp`}</p><p>Validation: ${percent(p.validation.error_capture)} errors detected / ${percent(p.validation.review_rate)} review<br>Frozen test: ${percent(p.test.error_capture)} errors detected / ${percent(p.test.review_rate)} review</p></div>`
        : `<p>${name}: no candidate satisfies the validation budget.</p>`,
    )
    .join("");
  const update = () => {
    const split = $("#threshold-split").value,
      rule = $("#threshold-rule").value;
    const entry = study.curves[split].find(
      (row) => row.condition === conditionSelect.value,
    );
    const points = entry.points,
      selected = study.selected[rule];
    const w = 900,
      h = 300,
      left = 48,
      right = 25,
      top = 30,
      bottom = 45;
    const x = (v) => left + ((v - 0.5) / 0.5) * (w - left - right);
    const y = (v) => top + (1 - v) * (h - top - bottom);
    let inner = [0, 0.25, 0.5, 0.75, 1]
      .map(
        (v) =>
          `<line x1="${left}" y1="${y(v)}" x2="${w - right}" y2="${y(v)}" stroke="#dce3dc"/><text class="chart-number" x="${left - 8}" y="${y(v) + 4}" text-anchor="end">${percent(v, 0)}</text>`,
      )
      .join("");
    inner += [0.5, 0.6, 0.7, 0.8, 0.9, 1]
      .map(
        (v) =>
          `<text class="chart-number" x="${x(v)}" y="${h - 21}" text-anchor="middle">${percent(v, 0)}</text>`,
      )
      .join("");
    for (const [metric, color] of [
      ["error_capture", "#256c57"],
      ["review_rate", "#b17c32"],
    ]) {
      const valid = points.filter((p) => p[rule][metric] != null);
      inner += `<polyline points="${valid.map((p) => `${x(p.confidence_threshold)},${y(p[rule][metric])}`).join(" ")}" fill="none" stroke="${color}" stroke-width="3"/>`;
    }
    if (selected)
      inner += `<line x1="${x(selected.confidence_below)}" y1="${top}" x2="${x(selected.confidence_below)}" y2="${h - bottom}" stroke="#5c6c64" stroke-dasharray="5 5"/><text class="chart-text" x="${x(selected.confidence_below) - 5}" y="${top - 10}" text-anchor="end">Selected ${percent(selected.confidence_below, 0)}</text>`;
    inner += `<text class="chart-text" x="${w / 2}" y="${h - 2}" text-anchor="middle">Confidence threshold (flag below this value)</text>`;
    $("#threshold-chart").innerHTML = chartFrame(
      w,
      h,
      inner,
      `${split} error detection and workload across confidence thresholds`,
      "Both rates range from zero to one hundred percent. The vertical line is frozen from validation selection.",
    );
    const threshold = Number($("#threshold-explore").value) / 100;
    const stats = points.find(
      (p) => Math.abs(p.confidence_threshold - threshold) < 1e-8,
    )[rule];
    $("#threshold-explore-value").textContent = percent(threshold, 0);
    $("#threshold-readout").textContent =
      `${split === "test" ? "Descriptive test view" : "Validation view"} at ${percent(threshold, 0)}: ${stats.errors_caught}/${stats.total_errors} errors flagged (${percent(stats.error_capture)}); ${stats.flagged}/${stats.n} images to review (${percent(stats.review_rate)}); unflagged accuracy ${percent(stats.retained_accuracy)} (n=${stats.retained}).`;
  };
  ["threshold-split", "threshold-condition", "threshold-rule"].forEach((id) =>
    $(`#${id}`).addEventListener("change", update),
  );
  $("#threshold-explore").addEventListener("input", update);
  update();
}

function renderBenchmark() {
  const r = state.report;
  const summary = [
    [
      "Clean accuracy",
      percent(r.clean.accuracy),
      `95% image-level CI ${percent(r.clean.accuracy_ci[0])}–${percent(r.clean.accuracy_ci[1])}`,
    ],
    [
      "Malignant AUROC",
      r.clean.auc.toFixed(3),
      `Balanced accuracy ${percent(r.clean.balanced_accuracy)}`,
    ],
    [
      "Clean calibration error",
      percent(r.clean.ece),
      `Raw ${percent(r.clean_raw.ece)} → calibrated ${percent(r.clean.ece)}`,
    ],
    [
      "Held-out test images",
      String(r.clean.n),
      "42 malignant · 114 normal / benign",
    ],
  ];
  $("#benchmark-summary").innerHTML = summary
    .map(
      ([label, value, description]) =>
        `<div class="summary-item"><span>${label}</span><strong>${value}</strong><p>${description}</p></div>`,
    )
    .join("");
  const w = 540,
    h = 290,
    left = 44,
    right = 18,
    top = 18,
    bottom = 45;
  const x = (v) => left + (v / 3) * (w - left - right);
  const y = (v) => top + (1 - v) * (h - top - bottom);
  let inner = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (tick) =>
        `<line x1="${left}" y1="${y(tick)}" x2="${w - right}" y2="${y(tick)}" stroke="#dce3dc"/><text class="chart-number" x="${left - 8}" y="${y(tick) + 4}" text-anchor="end">${percent(tick, 0)}</text>`,
    )
    .join("");
  inner += [0, 1, 2, 3]
    .map(
      (tick) =>
        `<text class="chart-text" x="${x(tick)}" y="${h - 22}" text-anchor="middle">${tick ? `Level ${tick}` : "Clean"}</text>`,
    )
    .join("");
  for (const key of Object.keys(stressNames)) {
    const points = [
      r.clean.accuracy,
      ...r.conditions
        .filter((c) => c.stress === key)
        .map((c) => c.metrics.accuracy),
    ];
    inner += `<polyline points="${points.map((v, i) => `${x(i)},${y(v)}`).join(" ")}" fill="none" stroke="${stressColors[key]}" stroke-width="2.5" stroke-linejoin="round"/>`;
    inner += points
      .map(
        (v, i) =>
          `<circle cx="${x(i)}" cy="${y(v)}" r="3.5" fill="${stressColors[key]}"><title>${stressNames[key]}, ${i ? `level ${i}` : "clean"}: ${percent(v)} accuracy</title></circle>`,
      )
      .join("");
  }
  $("#benchmark-chart").innerHTML = chartFrame(
    w,
    h,
    inner,
    "Classifier accuracy by stress severity",
    "See the condition table below for exact measurements.",
  );
  $("#benchmark-legend").innerHTML = Object.keys(stressNames)
    .map(
      (key) =>
        `<span><i style="--series:${stressColors[key]}"></i>${stressNames[key]}</span>`,
    )
    .join("");
  let calibration = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (tick) =>
        `<line x1="${left}" y1="${y(tick)}" x2="${w - right}" y2="${y(tick)}" stroke="#dce3dc"/><text class="chart-number" x="${left - 8}" y="${y(tick) + 4}" text-anchor="end">${percent(tick, 0)}</text>`,
    )
    .join("");
  const cx = (v) => left + v * (w - left - right);
  calibration += `<line x1="${cx(0)}" y1="${y(0)}" x2="${cx(1)}" y2="${y(1)}" stroke="#98a795" stroke-dasharray="5 5"/>`;
  [0, 0.25, 0.5, 0.75, 1].forEach((v) => {
    calibration += `<text class="chart-number" x="${cx(v)}" y="${h - 22}" text-anchor="middle">${percent(v, 0)}</text>`;
  });
  for (const [metric, color] of [
    [r.clean_raw, "#b2bdb8"],
    [r.clean, "#256c57"],
  ]) {
    calibration += metric.bins
      .filter((bin) => bin.n)
      .map(
        (bin) =>
          `<circle cx="${cx(bin.confidence)}" cy="${y(bin.accuracy)}" r="${Math.max(3, Math.sqrt(bin.n) * 0.8)}" fill="${color}" stroke="${color === "#256c57" ? "#f6f8f5" : color}" stroke-width="1.5"><title>${color === "#256c57" ? "Calibrated" : "Raw"}: ${bin.n} images, confidence ${percent(bin.confidence)}, accuracy ${percent(bin.accuracy)}</title></circle>`,
      )
      .join("");
  }
  calibration += `<text class="chart-text" x="${w / 2}" y="${h - 3}" text-anchor="middle">Mean confidence →</text><text class="chart-text" x="${left}" y="10">Observed accuracy</text>`;
  $("#calibration-chart").innerHTML = chartFrame(
    w,
    h,
    calibration,
    "Reliability diagram: mean confidence versus observed accuracy",
    "The diagonal is perfect agreement. Circle size reflects bin sample count.",
  );
  const clean = `<tr><td>Clean reference</td><td>${percent(r.clean.accuracy)} <small>[${percent(r.clean.accuracy_ci[0], 0)}–${percent(r.clean.accuracy_ci[1], 0)}]</small></td><td>${r.clean.confident_errors} / ${r.clean.errors} errors</td><td>${r.clean_review.flagged} / 156</td><td>${r.clean_review.errors_caught} / ${r.clean_review.total_errors}</td><td>${percent(r.clean_review.retained_accuracy)} <small>n=${r.clean_review.retained}</small></td></tr>`;
  $("#benchmark-rows").innerHTML =
    clean +
    r.conditions
      .map(
        (c) =>
          `<tr class="${c.stress === "gain_down" && c.severity === 2 ? "worst-row" : ""}"><td>${conditionLabel(c)}</td><td>${percent(c.metrics.accuracy)} <small>[${percent(c.metrics.accuracy_ci[0], 0)}–${percent(c.metrics.accuracy_ci[1], 0)}]</small></td><td>${c.metrics.confident_errors} / ${c.metrics.errors} errors</td><td>${c.review.flagged} / 156</td><td>${c.review.errors_caught} / ${c.review.total_errors}</td><td>${percent(c.review.retained_accuracy)} <small>n=${c.review.retained}</small></td></tr>`,
      )
      .join("");
  const example = r.conditions.find(
    (c) => c.stress === "gain_down" && c.severity === 2,
  );
  $("#benchmark-finding").innerHTML =
    `<h2>The model gets more wrong.<br>It does not always get less certain.</h2><p>At −6 dB simulated gain, <strong>${example.metrics.confident_errors} predictions are wrong at ≥80% confidence.</strong> The fixed rule captures ${example.review.errors_caught} of ${example.review.total_errors} errors, compared with ${example.review.confidence_only_errors_caught} using confidence alone. But it sends <strong>${example.review.flagged} of 156 images to review.</strong> That workload is part of the result.</p>`;
  $("#model-method-details").innerHTML =
    `<div class="method-model">${r.model.parameters.toLocaleString()} parameters · selected epoch ${r.model.selected_epoch} / ${r.model.epochs}<br>Temperature ${r.model.temperature.toFixed(3)} · seed ${r.seed}<br>Checkpoint SHA-256: ${r.model.sha256}</div>`;
  $("#limitations-list").innerHTML = r.limitations
    .map((limit) => `<li>${escapeHTML(limit)}</li>`)
    .join("");
}

function renderQueue() {
  const filter = $("#queue-filter").value;
  const entries = [...state.queue.entries()].filter(
    ([, e]) =>
      filter === "all" || (filter === "reviewed" ? e.reviewed : !e.reviewed),
  );
  const reviewed = [...state.queue.values()].filter(
    (entry) => entry.reviewed,
  ).length;
  $("#queue-count").textContent = state.queue.size;
  $("#queue-heading").textContent =
    `Flagged experiments${state.queue.size ? ` (${state.queue.size})` : ""}`;
  $("#queue-summary").textContent = state.queue.size
    ? `${state.queue.size} flagged experiments · ${reviewed} marked reviewed · Stored in this browser tab for this model. Different settings can create multiple entries for the same image.`
    : "";
  $("#export-queue").disabled = !state.queue.size;
  $("#clear-queue").disabled = !state.queue.size || state.batch;
  $("#queue-list").innerHTML = entries.length
    ? entries
        .map(([key, entry]) => {
          const r = entry.data;
          return `<article class="queue-row ${entry.reviewed ? "reviewed-row" : ""}" data-key="${escapeHTML(key)}"><img src="${imageSource(r.sample.id)}" alt="${r.sample.name} ultrasound"><div><h3>${r.sample.name}</h3><p>${settingsLabel(r.settings)}<br>${percent(r.confidence)} confidence · ${r.correct ? "matches" : "differs from"} dataset label</p></div><ul class="review-reasons">${r.reasons.map((reason) => `<li>${escapeHTML(reason)}</li>`).join("")}</ul><label><input type="checkbox" data-review="${escapeHTML(key)}" ${entry.reviewed ? "checked" : ""}>Marked reviewed</label><button class="button button-outline" data-inspect="${escapeHTML(key)}">Inspect pair <svg class="outbound-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M5 5h10v10"/></svg></button></article>`;
        })
        .join("")
    : `<div class="queue-empty"><h3>${state.queue.size ? "No experiments in this filter." : "No flagged experiments yet."}</h3><p>${state.queue.size ? "Choose another filter to view the rest of the queue." : "Run an experiment in the lab or audit the full test split above. Cases appear here only when they cross the fixed review rule."}</p></div>`;
}

async function runBatch() {
  if (state.batch) return;
  state.batch = true;
  $("#run-batch").disabled = true;
  $("#clear-queue").disabled = true;
  $("#batch-progress").hidden = false;
  $("#batch-progress").value = 0;
  const config = settings();
  let next = 0,
    completed = 0,
    flagged = 0,
    errors = 0,
    caught = 0,
    failed = 0;
  const worker = async () => {
    while (next < state.samples.length) {
      const id = next++;
      try {
        const result = await api("/api/experiment", {
          sample_id: id,
          ...config,
          sweep: false,
        });
        if (result.flagged) {
          remember(result);
          flagged++;
        }
        if (!result.correct) {
          errors++;
          if (result.flagged) caught++;
        }
      } catch {
        failed++;
      }
      completed++;
      $("#batch-progress").value = completed;
      $("#batch-status").textContent =
        `Auditing ${completed} / ${state.samples.length} · ${flagged} flagged${failed ? ` · ${failed} requests failed` : ""}`;
    }
  };
  await Promise.all([worker(), worker(), worker()]);
  $("#batch-status").textContent =
    `${failed ? "Audit incomplete" : "Audit complete"} · ${settingsLabel(config)}. ${flagged} / ${completed - failed} images flagged; ${caught} / ${errors} observed errors captured.${failed ? ` ${failed} requests failed; retry the audit with the server running.` : ""} Counts describe this run; the queue can contain earlier settings.`;
  $("#run-batch").disabled = false;
  state.batch = false;
  renderQueue();
}

async function loadFailure() {
  $("#load-case").disabled = true;
  $("#load-case").textContent = "Finding an observed failure…";
  try {
    // Search actual outputs; no prewritten or fabricated confidence values.
    for (const sample of state.samples.filter(
      (s) => s.correct && s.label === 1,
    )) {
      const result = await api("/api/experiment", {
        sample_id: sample.id,
        gain: -6,
        speckle: 0,
        shadow: 0,
      });
      if (!result.correct && result.confidence >= 0.8) {
        $("#gain").value = -6;
        $("#speckle").value = 0;
        $("#shadow").value = 0;
        updateControlLabels();
        await runExperiment(sample.id);
        return;
      }
    }
    $("#experiment-status").textContent =
      "No confidently wrong gain-shift example found for this checkpoint. Explore the benchmark instead.";
  } catch (error) {
    $("#experiment-error").textContent =
      `Could not load an example: ${error.message}. Retry with the Python server running.`;
    $("#experiment-error").hidden = false;
  } finally {
    $("#load-case").disabled = false;
    $("#load-case").innerHTML =
      '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 4 7 6-7 6V4Z"/></svg>Load failure example';
  }
}

function bindEvents() {
  $(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    const main =
      document.querySelector(".view:not([hidden]) main") ||
      document.querySelector("main.view:not([hidden])");
    main?.focus();
    main?.scrollIntoView();
  });
  window.addEventListener("hashchange", route);
  $("#sample-search").addEventListener("input", renderSamples);
  $("#sample-filter").addEventListener("change", renderSamples);
  $("#sample-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-sample]");
    if (button) runExperiment(Number(button.dataset.sample));
  });
  ["gain", "speckle", "shadow"].forEach((id) =>
    $(`#${id}`).addEventListener("input", markDirty),
  );
  $("#experiment-form").addEventListener("submit", (event) => {
    event.preventDefault();
    runExperiment();
  });
  $("#reset-controls").addEventListener("click", () => {
    $("#gain").value = 0;
    $("#speckle").value = 0;
    $("#shadow").value = 0;
    updateControlLabels();
    runExperiment();
  });
  $("#load-case").addEventListener("click", loadFailure);
  $("#export-experiment").addEventListener("click", () => {
    if (state.result && !state.busy && !state.dirty)
      download(
        experimentExport(state.result),
        `gainguard-${state.result.sample.name}.json`,
      );
  });
  $("#export-report").addEventListener("click", () =>
    download(state.report, "gainguard-benchmark.json"),
  );
  $("#queue-filter").addEventListener("change", renderQueue);
  $("#run-batch").addEventListener("click", runBatch);
  $("#clear-queue").addEventListener("click", () => {
    state.queue.clear();
    saveQueue();
    renderQueue();
  });
  $("#export-queue").addEventListener("click", () =>
    download(
      {
        model_sha256: state.report.model.sha256,
        research_only: true,
        entries: [...state.queue.values()].map((e) => ({
          ...experimentExport(e.data),
          reviewed: e.reviewed,
        })),
      },
      "gainguard-review-queue.json",
    ),
  );
  $("#queue-list").addEventListener("change", (event) => {
    const key = event.target.dataset.review;
    if (key && state.queue.has(key)) {
      state.queue.get(key).reviewed = event.target.checked;
      saveQueue();
      renderQueue();
    }
  });
  $("#queue-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-inspect]");
    if (!button) return;
    const entry = state.queue.get(button.dataset.inspect);
    if (!entry) return;
    const s = entry.data.settings;
    $("#gain").value = s.gain;
    $("#speckle").value = s.speckle;
    $("#shadow").value = s.shadow;
    updateControlLabels();
    location.hash = "lab";
    runExperiment(entry.data.sample.id);
  });
}

async function boot() {
  try {
    [state.report, state.samples] = await Promise.all([
      api("/api/report"),
      api("/api/samples"),
    ]);
    state.storageKey = `gainguard-queue-${state.report.model.sha256}`;
    try {
      const saved = JSON.parse(
        sessionStorage.getItem(state.storageKey) || "[]",
      );
      if (Array.isArray(saved))
        saved.forEach((entry) => {
          if (
            entry?.data?.sample &&
            Array.isArray(entry.data.reasons) &&
            entry.data.settings
          )
            state.queue.set(queueKey(entry.data), entry);
        });
    } catch {
      /* Session history is optional; inference remains available. */
    }
    renderSamples();
    renderBenchmark();
    renderThresholdStudy();
    renderQueue();
    updateControlLabels();
    bindEvents();
    route();
    $("#app").hidden = false;
    $("#loading").hidden = true;
    // Start with a real correctly classified reference, without selecting on stress outcomes.
    state.selected =
      state.samples.find((sample) => sample.label === 1 && sample.correct)
        ?.id || 0;
    await runExperiment();
  } catch (error) {
    $("#loading").hidden = true;
    $("#boot-error").hidden = false;
    $("#boot-error").textContent =
      `The research service could not load: ${error.message}. ${window.GAINGUARD_STATIC ? "Reload to retry, or follow the Python instructions linked in the footer." : "Start python server.py, then reload."}`;
  }
}

boot();
