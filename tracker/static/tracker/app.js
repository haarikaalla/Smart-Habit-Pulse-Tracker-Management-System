let currentFilter = "all";
const fallbackQuotes = [
    {
        text: "Small steps every day build strong habits over time.",
        author: "Smart Habit Pulse Tracker"
    },
    {
        text: "Consistency matters more than intensity.",
        author: "Daily Reminder"
    },
    {
        text: "A routine becomes powerful when you repeat it with purpose.",
        author: "Habit Note"
    },
    {
        text: "Progress grows when you show up again tomorrow.",
        author: "Focus Log"
    },
    {
        text: "Discipline is often just a decision repeated quietly.",
        author: "Tracker Console"
    }
];
const introStorageKey = "smart_habit_pulse_tracker_intro_seen";
const introLines = [
    "[OK] Loading interface modules...",
    "[OK] Syncing habit tracker workspace...",
    "[OK] Preparing daily progress dashboard...",
    "[OK] Restoring quote generator cache...",
    "[OK] Launch complete. Opening system."
];
const introStartDelay = 700;
const introStepDelay = 560;
const introEndDelay = 950;
const metricBarWidth = 20;
let quoteTypingAnimationId = 0;
const dashboardBarState = {
    completedFilled: 0,
    pendingFilled: 0,
    introFilled: 0,
    completedAnimationId: 0,
    pendingAnimationId: 0,
    introAnimationId: 0
};

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function renderBar(value, total, width = 20) {
    if (!total) {
        return `[${".".repeat(width)}]`;
    }

    const filled = Math.max(0, Math.min(width, Math.round((value / total) * width)));
    return `[${"|".repeat(filled)}${".".repeat(width - filled)}]`;
}

function padCount(value) {
    return String(value).padStart(2, "0");
}

function updateTerminalCaret() {
    const input = document.getElementById("habitInput");
    const mirror = document.getElementById("inputMirror");
    const caret = document.getElementById("terminalCaret");

    if (!input || !mirror || !caret) {
        return;
    }

    const caretIndex = typeof input.selectionStart === "number" ? input.selectionStart : input.value.length;
    const contentBeforeCaret = input.value.slice(0, caretIndex).replace(/ /g, "\u00a0");

    mirror.textContent = contentBeforeCaret;

    const mirrorWidth = mirror.getBoundingClientRect().width;
    const inputWidth = input.getBoundingClientRect().width;
    const caretWidth = caret.getBoundingClientRect().width || 10;
    const nextLeft = Math.min(Math.max(0, mirrorWidth - input.scrollLeft), Math.max(0, inputWidth - caretWidth));

    caret.style.left = `${nextLeft}px`;
}

function easeOutCubic(progress) {
    return 1 - Math.pow(1 - progress, 3);
}

function animateBarFill(selector, fromFilled, toFilled, toneClass, animationKey) {
    const element = $(selector);
    const duration = 680;
    const start = window.performance.now();
    dashboardBarState[animationKey] += 1;
    const animationId = dashboardBarState[animationKey];

    function tick(now) {
        if (dashboardBarState[animationKey] !== animationId) {
            return;
        }

        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutCubic(progress);
        const currentFilled = Math.round(fromFilled + (toFilled - fromFilled) * easedProgress);

        element
            .toggleClass("is-animating", progress < 1)
            .toggleClass("is-amber", toneClass === "amber")
            .text(`[${"|".repeat(currentFilled)}${".".repeat(metricBarWidth - currentFilled)}]`);

        if (progress < 1) {
            window.requestAnimationFrame(tick);
        } else {
            element.removeClass("is-animating");
        }
    }

    window.requestAnimationFrame(tick);
}

function animateDashboardBars(completed, pending, total) {
    const nextCompletedFilled = total ? Math.round((completed / total) * metricBarWidth) : 0;
    const nextPendingFilled = total ? Math.round((pending / total) * metricBarWidth) : 0;

    animateBarFill(
        "#completedBar",
        dashboardBarState.completedFilled,
        nextCompletedFilled,
        "green",
        "completedAnimationId"
    );
    animateBarFill(
        "#pendingBar",
        dashboardBarState.pendingFilled,
        nextPendingFilled,
        "amber",
        "pendingAnimationId"
    );

    dashboardBarState.completedFilled = nextCompletedFilled;
    dashboardBarState.pendingFilled = nextPendingFilled;
}

function showMessage(tone, text) {
    const prefixMap = {
        success: "[OK]",
        warning: "[WARN]",
        error: "[ERR]",
        info: "[SYS]"
    };

    $("#messageBox")
        .attr("data-tone", tone)
        .html(`
            <span class="message-prefix">${prefixMap[tone] || "[SYS]"}</span>
            <span class="message-text">${escapeHtml(text)}</span>
        `);
}

function typeQuoteText(fullText) {
    const quoteText = document.getElementById("quoteText");
    const quoteTextValue = document.getElementById("quoteTextValue");
    const quoteAuthor = document.getElementById("quoteAuthor");

    if (!quoteText || !quoteTextValue || !quoteAuthor) {
        return;
    }

    quoteTypingAnimationId += 1;
    const animationId = quoteTypingAnimationId;
    const characters = Array.from(fullText);
    const duration = Math.max(1300, Math.min(3200, characters.length * 42));
    const start = window.performance.now();

    quoteText.classList.add("is-typing");
    quoteAuthor.classList.add("is-hidden");
    quoteTextValue.textContent = "";

    function tick(now) {
        if (animationId !== quoteTypingAnimationId) {
            return;
        }

        const progress = Math.min((now - start) / duration, 1);
        const visibleCount = Math.max(1, Math.floor(progress * characters.length));
        quoteTextValue.textContent = characters.slice(0, visibleCount).join("");

        if (progress < 1) {
            window.requestAnimationFrame(tick);
        } else {
            quoteTextValue.textContent = fullText;
            quoteText.classList.remove("is-typing");
            window.setTimeout(function () {
                if (animationId === quoteTypingAnimationId) {
                    quoteAuthor.classList.remove("is-hidden");
                }
            }, 40);
        }
    }

    window.requestAnimationFrame(tick);
}

function renderQuote(quote) {
    typeQuoteText(`"${quote.text}"`);
    $("#quoteAuthor").text(`- ${quote.author}`);
}

function renderIntroProgress(step, total) {
    const nextIntroFilled = total ? Math.round((step / total) * metricBarWidth) : 0;

    animateBarFill(
        "#introProgress",
        dashboardBarState.introFilled,
        nextIntroFilled,
        "amber",
        "introAnimationId"
    );

    dashboardBarState.introFilled = nextIntroFilled;
}

function appendIntroLine(text) {
    $("#introLog").append(`<p class="intro-line"><strong>$</strong> ${escapeHtml(text)}</p>`);
}

function finishIntro() {
    $("body").removeClass("intro-active");
    document.documentElement.classList.remove("intro-pending");

    window.setTimeout(function () {
        $("#introScreen").attr("aria-hidden", "true");
    }, 350);
}

function startIntroSequence() {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let hasSeenIntro = false;

    try {
        hasSeenIntro = window.localStorage.getItem(introStorageKey) === "true";
    } catch (error) {
        hasSeenIntro = false;
    }

    if (reduceMotion || hasSeenIntro) {
        finishIntro();
        return;
    }

    $("body").addClass("intro-active");
    $("#introScreen").attr("aria-hidden", "false");
    $("#introLog").empty();
    renderIntroProgress(0, introLines.length);

    const timers = [];

    introLines.forEach(function (line, index) {
        const timer = window.setTimeout(function () {
            appendIntroLine(line);
            renderIntroProgress(index + 1, introLines.length);
        }, introStartDelay + index * introStepDelay);

        timers.push(timer);
    });

    const completeTimer = window.setTimeout(function () {
        try {
            window.localStorage.setItem(introStorageKey, "true");
        } catch (error) {
        }

        finishIntro();
    }, introStartDelay + introLines.length * introStepDelay + introEndDelay);

    timers.push(completeTimer);

    $("#skipIntroBtn").off("click").on("click", function () {
        timers.forEach(function (timer) {
            window.clearTimeout(timer);
        });

        try {
            window.localStorage.setItem(introStorageKey, "true");
        } catch (error) {
        }

        finishIntro();
    });
}

function setQuoteLoading(isLoading) {
    const button = $("#newQuoteBtn");
    button.prop("disabled", isLoading);
    button.text(isLoading ? "[ LOADING ]" : "[ NEW QUOTE ]");
}

function loadRandomQuote() {
    setQuoteLoading(true);

    $.ajax({
        url: "https://dummyjson.com/quotes/random",
        method: "GET",
        timeout: 5000,
        success: function (data) {
            if (data && data.quote && data.author) {
                renderQuote({
                    text: data.quote,
                    author: data.author
                });
                return;
            }

            const quote = fallbackQuotes[Math.floor(Math.random() * fallbackQuotes.length)];
            renderQuote(quote);
        },
        error: function () {
            const quote = fallbackQuotes[Math.floor(Math.random() * fallbackQuotes.length)];
            renderQuote(quote);
        },
        complete: function () {
            setQuoteLoading(false);
        }
    });
}

function updateFilterState() {
    $(".filterBtn").each(function () {
        const isActive = $(this).data("filter") === currentFilter;
        $(this).toggleClass("active", isActive);
        $(this).attr("aria-pressed", String(isActive));
    });

    $("#activeFilter").text(`[ FILTER ${currentFilter.toUpperCase()} ]`);
}

function updateSyncClock() {
    const now = new Date();
    const timeStamp = now.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });

    $("#lastSync").text(`[ SYNC ${timeStamp} ]`);
}

function loadDashboard() {
    $.get("/api/dashboard/", function (data) {
        const total = data.total || 0;
        const completed = data.completed || 0;
        const pending = data.pending || 0;
        const completionRate = total ? Math.round((completed / total) * 100) : 0;

        $("#totalCount").text(padCount(total));
        $("#completedCount").text(padCount(completed));
        $("#pendingCount").text(padCount(pending));
        animateDashboardBars(completed, pending, total);
        $("#completionRate").text(`${String(completionRate).padStart(2, "0")}%`);

        let statusText = "[ IDLE ]";
        if (total > 0) {
            statusText = completionRate === 100 ? "[ OPTIMAL ]" : "[ TRACKING ]";
        }

        $("#systemStatus").text(statusText);
        $("#completionSummary").text(
            total === 0
                ? "No habits tracked yet."
                : `${completed} completed and ${pending} pending out of ${total} habits.`
        );
        updateSyncClock();
    }).fail(function () {
        showMessage("error", "Unable to load dashboard status.");
    });
}

function buildHabitRow(habit) {
    const checked = habit.completed ? "checked" : "";
    const statusClass = habit.completed ? "is-done" : "is-pending";
    const statusLabel = habit.completed ? "[DONE]" : "[TODO]";

    return `
        <article class="habit-row ${habit.completed ? "is-complete" : ""}" role="listitem">
            <div class="habit-main">
                <label class="habit-toggle" for="habit-${habit.id}">
                    <input
                        type="checkbox"
                        id="habit-${habit.id}"
                        class="completeCheckbox"
                        data-id="${habit.id}"
                        ${checked}
                        aria-label="Toggle habit completion"
                    >
                    <span class="checkbox-ui" aria-hidden="true">${habit.completed ? "[x]" : "[ ]"}</span>
                    <span class="habit-status ${statusClass}">${statusLabel}</span>
                    <span class="habit-name">${escapeHtml(habit.name)}</span>
                </label>
                <p class="habit-meta">-- created ${escapeHtml(habit.created_at)}</p>
            </div>
            <button class="terminal-button danger deleteBtn" type="button" data-id="${habit.id}">
                [ PURGE ]
            </button>
        </article>
    `;
}

function loadHabits() {
    $.get("/api/habits/", function (data) {
        $("#habitList").empty();
        let visibleCount = 0;

        data.forEach(function (habit) {
            if (currentFilter === "completed" && !habit.completed) {
                return;
            }

            if (currentFilter === "pending" && habit.completed) {
                return;
            }

            visibleCount += 1;
            $("#habitList").append(buildHabitRow(habit));
        });

        $("#listMeta").text(`[ ${padCount(visibleCount)} ITEMS ]`);

        if (visibleCount === 0) {
            $("#habitList").html(`
                <div class="empty-state">
                    <strong>[ EMPTY LOG ]</strong><br>
                    No habits match the current filter. Add a new routine or switch views.
                </div>
            `);
        }
    }).fail(function () {
        showMessage("error", "Unable to load the habit log.");
    });
}

function submitHabit() {
    const habitName = $("#habitInput").val().trim();

    if (!habitName) {
        showMessage("warning", "Enter a habit before running the command.");
        return;
    }

    $.ajax({
        url: "/add/",
        type: "POST",
        data: JSON.stringify({ name: habitName }),
        contentType: "application/json",
        success: function (response) {
            if (response.status === "success") {
                $("#habitInput").val("");
                updateTerminalCaret();
                showMessage("success", "Habit added.");
                loadHabits();
                loadDashboard();
                return;
            }

            showMessage("warning", response.error || "Unable to add habit.");
        },
        error: function () {
            showMessage("error", "The add command failed.");
        }
    });
}

$(document).ready(function () {
    startIntroSequence();
    updateFilterState();
    loadRandomQuote();
    loadHabits();
    loadDashboard();
    updateTerminalCaret();

    $("#addBtn").on("click", submitHabit);
    $("#newQuoteBtn").on("click", loadRandomQuote);

    $("#habitInput").on("keydown", function (event) {
        if (event.key === "Enter") {
            submitHabit();
        }

        window.requestAnimationFrame(updateTerminalCaret);
    });

    $("#habitInput").on("input click focus blur keyup select", function () {
        window.requestAnimationFrame(updateTerminalCaret);
    });

    $(window).on("resize", updateTerminalCaret);

    $(".filterBtn").on("click", function () {
        currentFilter = $(this).data("filter");
        updateFilterState();
        loadHabits();
        showMessage("info", `Filter switched to ${currentFilter}.`);
    });

    $(document).on("change", ".completeCheckbox", function () {
        const id = $(this).data("id");
        const completed = $(this).is(":checked");

        $.ajax({
            url: `/api/habits/${id}/`,
            type: "PUT",
            data: JSON.stringify({ completed: completed }),
            contentType: "application/json",
            success: function () {
                showMessage("success", completed ? "Habit marked complete." : "Habit marked pending.");
                loadHabits();
                loadDashboard();
            },
            error: function () {
                showMessage("error", "Unable to update habit status.");
            }
        });
    });

    $(document).on("click", ".deleteBtn", function () {
        const id = $(this).data("id");

        $.ajax({
            url: `/api/habits/${id}/`,
            type: "DELETE",
            success: function () {
                showMessage("warning", "Habit removed.");
                loadHabits();
                loadDashboard();
            },
            error: function () {
                showMessage("error", "Unable to purge habit.");
            }
        });
    });
});
