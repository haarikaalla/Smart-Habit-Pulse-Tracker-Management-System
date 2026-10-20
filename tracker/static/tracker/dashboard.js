"use strict";

const api = "/api/v1";
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const state = { habits: [], analytics: null, search: "", category: "" };
const $ = (selector) => document.querySelector(selector);

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken;
  }
  const response = await fetch(`${api}${path}`, { credentials: "same-origin", ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error?.message || "Something went wrong. Please try again.");
    error.code = data.error?.code;
    throw error;
  }
  return data;
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setText(selector, value) {
  $(selector).textContent = value;
}

function renderSummary() {
  const summary = state.analytics.summary;
  setText("#today-rate", `${summary.today_rate}%`);
  setText("#today-completed", summary.today_completed);
  setText("#active-habits", summary.active_habits);
  setText("#weekly-rate", `${summary.weekly_adherence}%`);
  setText("#weekly-count", summary.weekly_check_ins);
  setText("#current-streak", summary.total_current_streak);
  setText("#best-streak", `${summary.best_streak} day${summary.best_streak === 1 ? "" : "s"}`);
  setText("#period-checkins", summary.period_check_ins);
}

function renderTrend() {
  const chart = $("#trend-chart");
  const values = state.analytics.timeline.slice(-7);
  const today = new Date().toISOString().slice(0, 10);
  chart.replaceChildren(...values.map((point) => {
    const column = document.createElement("div");
    column.className = `bar-column${point.date === today ? " today" : ""}`;
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = `${point.rate}%`;
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max(point.rate, 3)}%`;
    bar.title = `${point.completed} of ${point.available} habits completed`;
    const label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = new Intl.DateTimeFormat("en", { weekday: "short", timeZone: "UTC" })
      .format(new Date(`${point.date}T00:00:00Z`)).slice(0, 2);
    column.append(value, bar, label);
    return column;
  }));
}

function renderHeatmap() {
  const heatmap = $("#heatmap");
  const values = state.analytics.timeline.slice(-28);
  const max = Math.max(...values.map((item) => item.completed), 1);
  heatmap.replaceChildren(...values.map((point) => {
    const cell = document.createElement("span");
    cell.className = "heat-day";
    cell.dataset.level = point.completed ? String(Math.max(1, Math.ceil(point.completed / max * 4))) : "0";
    cell.title = `${point.date}: ${point.completed} check-in${point.completed === 1 ? "" : "s"}`;
    return cell;
  }));
  const summary = state.analytics.summary;
  const message = summary.period_check_ins
    ? `${summary.period_check_ins} actions completed in 28 days. Your best streak is ${summary.best_streak} day${summary.best_streak === 1 ? "" : "s"}.`
    : "Your activity pattern will appear here as you record daily check-ins.";
  setText("#insight-copy", message);
}

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function habitCard(habit) {
  const card = makeElement("article", "habit-card");
  card.style.setProperty("--habit-color", habit.color);

  const top = makeElement("div", "habit-card-top");
  const badge = makeElement("span", "category-badge", habit.category_label);
  const edit = makeElement("button", "card-menu", "•••");
  edit.type = "button";
  edit.title = "Edit or archive this habit";
  edit.setAttribute("aria-label", `Edit ${habit.name}`);
  edit.addEventListener("click", () => openEditor(habit));
  top.append(badge, edit);

  const title = makeElement("h3", "", habit.name);
  const description = makeElement("p", "habit-description", habit.description || "A meaningful action in your daily system.");
  const dots = makeElement("div", "weekly-progress");
  for (let index = 0; index < 7; index += 1) {
    dots.append(makeElement("i", `progress-dot${index < habit.week_completed ? " complete" : ""}`));
  }
  const meta = makeElement("div", "progress-meta");
  meta.append(
    makeElement("span", "", `${habit.week_completed} check-in${habit.week_completed === 1 ? "" : "s"} this week`),
    makeElement("span", "", `Goal ${habit.target_per_week}×`),
  );

  const footer = makeElement("div", "habit-card-footer");
  const streak = makeElement("span", "streak");
  streak.append(makeElement("span", "", "♨"), makeElement("b", "", `${habit.current_streak} day streak`));
  const checkIn = makeElement("button", `checkin-button${habit.today_completed ? " completed" : ""}`, habit.today_completed ? "✓ Done today" : "Check in");
  checkIn.type = "button";
  checkIn.setAttribute("aria-pressed", String(habit.today_completed));
  checkIn.addEventListener("click", async () => {
    checkIn.disabled = true;
    try {
      await request(`/habits/${habit.id}/check-in/`, {
        method: "PUT",
        body: JSON.stringify({ completed: !habit.today_completed }),
      });
      showToast(habit.today_completed ? "Today’s check-in removed." : "Check-in recorded. Keep the rhythm going!");
      await refresh();
    } catch (error) {
      showToast(error.message, true);
    } finally {
      checkIn.disabled = false;
    }
  });
  footer.append(streak, checkIn);
  card.append(top, title, description, dots, meta, footer);
  return card;
}

function renderHabits() {
  const query = state.search.toLocaleLowerCase();
  const visible = state.habits.filter((habit) => {
    const matchesText = !query || `${habit.name} ${habit.description}`.toLocaleLowerCase().includes(query);
    const matchesCategory = !state.category || habit.category === state.category;
    return matchesText && matchesCategory;
  });
  $("#habit-list").replaceChildren(...visible.map(habitCard));
  $("#empty-state").hidden = visible.length !== 0;
}

async function refresh() {
  const [{ habits }, analytics] = await Promise.all([
    request("/habits/"),
    request("/analytics/?days=28"),
  ]);
  state.habits = habits;
  state.analytics = analytics;
  renderSummary();
  renderTrend();
  renderHeatmap();
  renderHabits();
}

function resetForm() {
  $("#habit-form").reset();
  $("#habit-id").value = "";
  $("#habit-version").value = "";
  $("#habit-target").value = "5";
  $("#habit-category").value = "other";
  $("#habit-color").value = "#7c5cfc";
  $("#form-error").textContent = "";
  setText("#dialog-title", "Create a new habit");
  setText("#submit-label", "Create habit");
  const archive = $("#archive-habit");
  if (archive) archive.hidden = true;
}

function openCreate() {
  resetForm();
  $("#habit-dialog").showModal();
  $("#habit-name").focus();
}

function openEditor(habit) {
  resetForm();
  $("#habit-id").value = habit.id;
  $("#habit-version").value = habit.version;
  $("#habit-name").value = habit.name;
  $("#habit-description").value = habit.description;
  $("#habit-category").value = habit.category;
  $("#habit-target").value = habit.target_per_week;
  $("#habit-reminder").value = habit.reminder_time || "";
  $("#habit-color").value = habit.color;
  setText("#dialog-title", "Refine your habit");
  setText("#submit-label", "Save changes");

  let archive = $("#archive-habit");
  if (!archive) {
    archive = makeElement("button", "secondary-button", "Archive habit");
    archive.id = "archive-habit";
    archive.type = "button";
    $(".dialog-actions").prepend(archive);
  }
  archive.hidden = false;
  archive.onclick = async () => {
    if (!window.confirm(`Archive “${habit.name}”? Its history will remain in your export.`)) return;
    try {
      await request(`/habits/${habit.id}/`, { method: "DELETE", body: JSON.stringify({}) });
      $("#habit-dialog").close();
      showToast("Habit archived. Its history is preserved.");
      await refresh();
    } catch (error) {
      $("#form-error").textContent = error.message;
    }
  };
  $("#habit-dialog").showModal();
}

$("#habit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("#habit-id").value;
  const payload = {
    name: $("#habit-name").value,
    description: $("#habit-description").value,
    category: $("#habit-category").value,
    target_per_week: Number($("#habit-target").value),
    reminder_time: $("#habit-reminder").value,
    color: $("#habit-color").value,
  };
  if (id) payload.expected_version = Number($("#habit-version").value);
  $("#form-error").textContent = "";
  try {
    await request(id ? `/habits/${id}/` : "/habits/", {
      method: id ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    $("#habit-dialog").close();
    showToast(id ? "Habit updated." : "Habit created. Your next action is ready.");
    await refresh();
  } catch (error) {
    $("#form-error").textContent = error.message;
  }
});

$("#open-create").addEventListener("click", openCreate);
document.querySelectorAll("[data-open-create]").forEach((button) => button.addEventListener("click", openCreate));
$("#close-dialog").addEventListener("click", () => $("#habit-dialog").close());
$("#cancel-dialog").addEventListener("click", () => $("#habit-dialog").close());
$("#search").addEventListener("input", (event) => { state.search = event.target.value; renderHabits(); });
$("#category-filter").addEventListener("change", (event) => { state.category = event.target.value; renderHabits(); });

const now = new Date();
setText("#today-label", now.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }).toUpperCase());
setText("#day-part", now.getHours() < 12 ? "morning" : now.getHours() < 18 ? "afternoon" : "evening");
refresh().catch((error) => {
  showToast(error.message, true);
  $("#empty-state").hidden = false;
});
