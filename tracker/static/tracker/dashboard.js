const api = "/api/v1";
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, {
    credentials: "same-origin",
    ...options,
    headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken, ...(options.headers || {})},
  });
  if (response.status === 204) return {};
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function habitRow(habit) {
  const item = document.createElement("li");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = habit.completed;
  checkbox.setAttribute("aria-label", `Mark ${habit.name} complete`);
  checkbox.addEventListener("change", async () => {
    await request(`/habits/${habit.id}/`, {method: "PATCH", body: JSON.stringify({completed: checkbox.checked})});
    await refresh();
  });
  const label = document.createElement("span");
  label.textContent = `${habit.name} · ${habit.target_per_week} days/week`;
  const remove = document.createElement("button");
  remove.textContent = "Delete";
  remove.addEventListener("click", async () => {
    await request(`/habits/${habit.id}/`, {method: "DELETE"});
    await refresh();
  });
  item.append(checkbox, label, remove);
  return item;
}

async function refresh() {
  const [{habits}, summary] = await Promise.all([request("/habits/"), request("/summary/")]);
  const list = document.getElementById("habit-list");
  list.replaceChildren(...habits.map(habitRow));
  document.getElementById("total").textContent = summary.total;
  document.getElementById("completed").textContent = summary.completed;
  document.getElementById("pending").textContent = summary.pending;
  document.getElementById("rate").textContent = `${summary.completion_rate}%`;
}

document.getElementById("habit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("status");
  try {
    await request("/habits/", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("habit-name").value,
        target_per_week: Number(document.getElementById("habit-target").value),
      }),
    });
    event.target.reset();
    document.getElementById("habit-target").value = 7;
    status.textContent = "Habit added.";
    await refresh();
  } catch (error) {
    status.textContent = error.message;
  }
});

refresh().catch((error) => { document.getElementById("status").textContent = error.message; });
