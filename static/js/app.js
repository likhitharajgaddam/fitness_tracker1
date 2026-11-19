// Global Theme Manager (Dark #101322 / Light #FAFAFC)
(function () {
  const THEME_STORAGE_KEY = "fittrack_theme";

  function getTheme() {
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") return attr;
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (_) {}
    return "dark";
  }

  function syncThemeControls(theme) {
    const isLight = theme === "light";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", isLight ? "true" : "false");
      btn.setAttribute(
        "title",
        isLight ? "Switch to Dark Mode" : "Switch to Light Mode"
      );
      const icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-sun-fill", !isLight);
        icon.classList.toggle("bi-moon-stars-fill", isLight);
      }
      const label = btn.querySelector("[data-theme-label]");
      if (label) {
        label.textContent = isLight ? "DARK MODE" : "LIGHT MODE";
      }
    });

    document.querySelectorAll("[data-set-theme]").forEach(function (btn) {
      const target = btn.getAttribute("data-set-theme");
      const active = target === theme;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setTheme(theme) {
    const normalized = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", normalized);
    document.documentElement.setAttribute("data-bs-theme", normalized);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, normalized);
    } catch (_) {}
    syncThemeControls(normalized);
    window.dispatchEvent(
      new CustomEvent("fittrack:themechange", { detail: { theme: normalized } })
    );
  }

  function toggleTheme() {
    setTheme(getTheme() === "dark" ? "light" : "dark");
  }

  window.FitTrackTheme = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggleTheme: toggleTheme,
    syncThemeControls: syncThemeControls,
  };
})();

document.addEventListener("DOMContentLoaded", function () {
  const prefersReducedMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 0. Bind Dual-Theme Switchers
  if (window.FitTrackTheme) {
    window.FitTrackTheme.syncThemeControls(window.FitTrackTheme.getTheme());
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.FitTrackTheme.toggleTheme();
      });
    });
    document.querySelectorAll("[data-set-theme]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.FitTrackTheme.setTheme(btn.getAttribute("data-set-theme"));
      });
    });
  }

  // 0b. Guard against browser bfcache serving stale pre-login/pre-workout HTML
  window.addEventListener("pageshow", function (event) {
    if (event.persisted && document.querySelector(".app-shell")) {
      window.location.reload();
    }
  });

  // 0c. Smoothly animate server-calculated Reward Jar liquid fills on initial load
  //     (never zeros out SVG coordinates; settles cleanly to exact persisted DB percent)
  if (!prefersReducedMotion) {
    document.querySelectorAll(".reward-jar-stage .jar-fill-group").forEach(function (group) {
      const pct = parseInt(group.getAttribute("data-fill-percent") || "0", 10);
      if (pct > 0) {
        group.classList.add("jar-fill-rising");
        group.addEventListener(
          "animationend",
          function () {
            group.classList.remove("jar-fill-rising");
          },
          { once: true }
        );
      }
    });
  }

  // 1. Motivational Quote Cycler
  const quoteDataEl = document.getElementById("motivational-quotes-data");
  const nextQuoteBtn = document.getElementById("next-quote-btn");
  const quoteTextEl = document.getElementById("quote-text");
  const quoteAuthorEl = document.getElementById("quote-author");
  const quoteThemeEl = document.getElementById("quote-theme");

  if (quoteDataEl && nextQuoteBtn && quoteTextEl && quoteAuthorEl) {
    try {
      const quotes = JSON.parse(quoteDataEl.textContent || "[]");
      let currentIndex = 0;
      const currentText = quoteTextEl.textContent.trim();
      const foundIndex = quotes.findIndex((item) => item.quote === currentText);
      if (foundIndex >= 0) currentIndex = foundIndex;

      nextQuoteBtn.addEventListener("click", function () {
        if (!quotes.length) return;
        currentIndex = (currentIndex + 1) % quotes.length;
        const item = quotes[currentIndex];
        quoteTextEl.textContent = item.quote;
        quoteAuthorEl.textContent = item.author;
        if (quoteThemeEl) quoteThemeEl.textContent = item.theme;
      });
    } catch (err) {
      console.error("Failed to initialize motivational quotes:", err);
    }
  }

  // 2. Password Visibility Toggles
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetId = btn.getAttribute("data-target");
      const input = targetId
        ? document.getElementById(targetId)
        : btn.closest(".input-group")?.querySelector("input");
      if (!input) return;
      const isPassword = input.getAttribute("type") === "password";
      input.setAttribute("type", isPassword ? "text" : "password");
      const icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-eye", !isPassword);
        icon.classList.toggle("bi-eye-slash", isPassword);
      }
      btn.setAttribute(
        "aria-label",
        isPassword ? "Hide password" : "Show password"
      );
    });
  });

  // 3. Quick-fill chips on Workout Tracker
  const quickFillButtons = document.querySelectorAll("[data-quick-activity]");
  const activityInput = document.getElementById("id_activity_name");
  const durationInput = document.getElementById("id_duration");

  quickFillButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const name = btn.getAttribute("data-quick-activity") || "";
      const duration = btn.getAttribute("data-quick-duration") || "";
      if (activityInput) activityInput.value = name;
      if (durationInput && duration) durationInput.value = duration;
      if (activityInput) activityInput.focus();
    });
  });

  // 4. Reusable Delete Confirmation Modal
  const deleteModalEl = document.getElementById("confirmDeleteModal");
  const deleteModalForm = document.getElementById("confirmDeleteForm");
  const deleteModalLabel = document.getElementById("confirmDeleteItemName");

  if (deleteModalEl && deleteModalForm) {
    deleteModalEl.addEventListener("show.bs.modal", function (event) {
      const trigger = event.relatedTarget;
      if (!trigger) return;
      const actionUrl = trigger.getAttribute("data-delete-url");
      const itemName = trigger.getAttribute("data-delete-name") || "this record";
      if (actionUrl) deleteModalForm.setAttribute("action", actionUrl);
      if (deleteModalLabel) deleteModalLabel.textContent = itemName;
    });
  }

  // 5. Animated KPI Count-up
  const countUpEls = document.querySelectorAll("[data-countup]");
  countUpEls.forEach(function (el) {
    const target = parseInt(el.getAttribute("data-countup") || "0", 10);
    if (isNaN(target) || target <= 0 || prefersReducedMotion) {
      el.textContent = isNaN(target) ? "0" : String(target);
      return;
    }
    const durationMs = 650;
    const startTime = performance.now();
    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = String(Math.round(target * eased));
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = String(target);
      }
    }
    requestAnimationFrame(step);
  });

  // 6. FITBUDDY Floating Companion Minimize / Maximize & Quick Pep Tips
  const fitbuddyDock = document.getElementById("fitbuddyDock");
  const fitbuddyBubble = document.getElementById("fitbuddyBubble");
  const fitbuddyMinBtn = document.getElementById("fitbuddyMinimizeBtn");
  const fitbuddyToggleBtn = document.getElementById("fitbuddyToggleBtn");
  const fitbuddyMsgEl = document.getElementById("fitbuddyMessage");

  if (fitbuddyDock && fitbuddyBubble) {
    const STORAGE_KEY = "fittrack_fitbuddy_minimized";
    try {
      if (localStorage.getItem(STORAGE_KEY) === "1") {
        fitbuddyBubble.classList.add("hidden");
      }
    } catch (_) {
      // Ignore storage access restrictions
    }

    const setMinimized = function (minimized) {
      fitbuddyBubble.classList.toggle("hidden", minimized);
      try {
        localStorage.setItem(STORAGE_KEY, minimized ? "1" : "0");
      } catch (_) {}
    };

    if (fitbuddyMinBtn) {
      fitbuddyMinBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        setMinimized(true);
      });
    }

    const companionTips = [
      "Every move counts! Even 10 mindful minutes nudges your Reward Jar higher.",
      "Consistency beats intensity — one short session today keeps your streak alive.",
      "Pick a Reward Jar on your Goals page to unlock a badge when it fills to 100%!",
      "Not sure what to do? Try spinning 'What Should I Play Today?' on Sports Ideas.",
    ];
    let tipIdx = 0;

    if (fitbuddyToggleBtn) {
      fitbuddyToggleBtn.addEventListener("click", function () {
        const isHidden = fitbuddyBubble.classList.contains("hidden");
        if (isHidden) {
          setMinimized(false);
        } else {
          setMinimized(true);
        }
      });
    }

    if (fitbuddyMsgEl) {
      fitbuddyMsgEl.style.cursor = "pointer";
      fitbuddyMsgEl.title = "Click for another FitBuddy tip";
      fitbuddyMsgEl.addEventListener("click", function () {
        tipIdx = (tipIdx + 1) % companionTips.length;
        fitbuddyMsgEl.textContent = companionTips[tipIdx];
      });
    }
  }

  // 7. Confetti Canvas & Celebration Modal
  function launchConfetti() {
    const canvas = document.getElementById("celebrationConfettiCanvas");
    if (!canvas || prefersReducedMotion) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.classList.remove("d-none");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const colors = ["#d4ff2b", "#de5235", "#34d399", "#fbbf24", "#f5f5ee", "#38bdf8"];
    const pieces = Array.from({ length: 105 }, function () {
      return {
        x: Math.random() * canvas.width,
        y: Math.random() * -canvas.height * 0.4,
        w: 7 + Math.random() * 6,
        h: 7 + Math.random() * 6,
        vx: (Math.random() - 0.5) * 4,
        vy: 3 + Math.random() * 4.5,
        rot: Math.random() * Math.PI * 2,
        vRot: (Math.random() - 0.5) * 0.2,
        color: colors[Math.floor(Math.random() * colors.length)],
      };
    });

    const start = performance.now();
    function frame(now) {
      const elapsed = now - start;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach(function (p) {
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vRot;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      });
      if (elapsed < 2600) {
        requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        canvas.classList.add("d-none");
      }
    }
    requestAnimationFrame(frame);
  }

  function showCelebrationModal(data) {
    if (!data || !data.has_celebration) return;
    const modalEl = document.getElementById("adventureCelebrationModal");
    const bodyEl = document.getElementById("celebrationModalBody");
    const titleEl = document.getElementById("celebrationModalTitle");
    const subEl = document.getElementById("celebrationModalSubtitle");
    if (!modalEl || !bodyEl || typeof bootstrap === "undefined") return;

    bodyEl.innerHTML = "";
    const hasGoals =
      Array.isArray(data.newly_completed_goals) &&
      data.newly_completed_goals.length > 0;
    const hasBadges =
      Array.isArray(data.newly_unlocked) && data.newly_unlocked.length > 0;
    const hasChallenge = Boolean(data.challenge_completed);

    if (hasGoals) {
      if (titleEl) titleEl.textContent = "GOAL JAR FILLED!";
      if (subEl)
        subEl.textContent =
          "Amazing effort — you filled your Reward Jar to 100%!";
    } else if (hasBadges) {
      if (titleEl) titleEl.textContent = "ACHIEVEMENT UNLOCKED!";
      if (subEl)
        subEl.textContent =
          "Your consistency just unlocked a permanent FitTrack badge!";
    } else if (hasChallenge) {
      if (titleEl) titleEl.textContent = "CHALLENGE COMPLETE!";
      if (subEl)
        subEl.textContent =
          "Daily Challenge conquered — bonus XP added to your profile!";
    } else {
      if (titleEl) titleEl.textContent = "WORKOUT LOGGED!";
      if (subEl)
        subEl.textContent =
          "Great job keeping your FitTrack momentum moving forward!";
    }

    if (data.workout) {
      const box = document.createElement("div");
      box.className = "p-3 rounded-4 surface-tint-lavender mb-3";
      const heading = document.createElement("div");
      heading.className = "fw-bold text-ink-bright";
      heading.textContent = `${data.workout.activity_name} · ${data.workout.duration} min`;
      const desc = document.createElement("div");
      desc.className = "small text-ink-muted";
      desc.textContent = "Recorded to your workout history and active goals.";
      box.appendChild(heading);
      box.appendChild(desc);
      bodyEl.appendChild(box);
    }

    if (hasChallenge) {
      const cBox = document.createElement("div");
      cBox.className = "p-3 rounded-4 surface-tint-peach mb-3";
      const cTitle = document.createElement("div");
      cTitle.className = "fw-bold text-ink-bright";
      cTitle.textContent = `${data.challenge_completed.title} (+${data.challenge_completed.xp_reward} XP)`;
      cBox.appendChild(cTitle);
      bodyEl.appendChild(cBox);
    }

    if (hasGoals) {
      data.newly_completed_goals.forEach(function (goal) {
        const gBox = document.createElement("div");
        gBox.className = "p-3 rounded-4 surface-tint-mint mb-2 text-start";
        const gHead = document.createElement("div");
        gHead.className = "fw-bold text-success";
        gHead.textContent = `Reward Jar Filled: ${goal.title}`;
        const gSub = document.createElement("div");
        gSub.className = "small text-ink-bright";
        gSub.textContent = `Badge Unlocked: ${goal.badge_title || goal.reward_badge_title || "Goal Champion"}`;
        gBox.appendChild(gHead);
        gBox.appendChild(gSub);
        bodyEl.appendChild(gBox);
      });
    }

    if (hasBadges) {
      data.newly_unlocked.forEach(function (badge) {
        const bBox = document.createElement("div");
        bBox.className = "p-3 rounded-4 surface-tint-sky mb-2 text-start";
        const bHead = document.createElement("div");
        bHead.className = "fw-bold text-ink-bright";
        bHead.textContent = `${badge.title} (+${badge.reward_xp ?? badge.xp_reward ?? 0} XP)`;
        const bSub = document.createElement("div");
        bSub.className = "small text-ink-muted";
        bSub.textContent = badge.description || "Unlocked in your Trophy Shelf!";
        bBox.appendChild(bHead);
        bBox.appendChild(bSub);
        bodyEl.appendChild(bBox);
      });
    }

    launchConfetti();
    if (window.FitTrackSound) {
      window.FitTrackSound.playFanfare();
      window.FitTrackSound.playCrowdCheer();
    }
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  const pendingCelebrationEl = document.getElementById("pending-celebration-data");
  if (pendingCelebrationEl) {
    try {
      const pending = JSON.parse(pendingCelebrationEl.textContent || "null");
      if (pending && pending.has_celebration) {
        showCelebrationModal(pending);
      }
    } catch (err) {
      console.error("Failed to parse celebration payload:", err);
    }
  }

  // 8. Activity Detail Interactive Workout Timer
  const timerCard = document.getElementById("guidedWorkoutTimerCard");
  if (timerCard) {
    const recMinutes = parseInt(
      timerCard.getAttribute("data-recommended-minutes") || "15",
      10
    );
    const totalTargetSeconds = Math.max(60, recMinutes * 60);
    let remainingSeconds = totalTargetSeconds;
    let elapsedSeconds = 0;
    let timerInterval = null;

    const displayEl = document.getElementById("timerDisplay");
    const ringEl = document.getElementById("timerRingVisual");
    const statusEl = document.getElementById("timerStatusText");
    const startBtn = document.getElementById("timerStartBtn");
    const pauseBtn = document.getElementById("timerPauseBtn");
    const resumeBtn = document.getElementById("timerResumeBtn");
    const resetBtn = document.getElementById("timerResetBtn");
    const timerDurationInput = document.getElementById("timerDurationInput");
    const finishForm = document.getElementById("activityTimerFinishForm");

    function renderTimer() {
      const mins = Math.floor(remainingSeconds / 60);
      const secs = remainingSeconds % 60;
      if (displayEl) {
        displayEl.textContent = `${String(mins).padStart(2, "0")}:${String(
          secs
        ).padStart(2, "0")}`;
      }
      if (ringEl) {
        const pct = Math.min(100, Math.round((elapsedSeconds / totalTargetSeconds) * 100));
        const deg = Math.round((pct / 100) * 360);
        ringEl.style.background = `conic-gradient(var(--accent-primary) ${deg}deg, var(--timer-track-bg) ${deg}deg 360deg)`;
      }
    }

    function tick() {
      elapsedSeconds += 1;
      if (remainingSeconds > 0) {
        remainingSeconds -= 1;
      }
      if (timerDurationInput && elapsedSeconds >= 60) {
        timerDurationInput.value = String(Math.max(1, Math.round(elapsedSeconds / 60)));
      }
      renderTimer();
      if (remainingSeconds === 0 && statusEl) {
        statusEl.textContent = "Finish Line Reached!";
        if (window.FitTrackSound) window.FitTrackSound.playFanfare();
      }
    }

    function setTimerState(mode) {
      if (!startBtn || !pauseBtn || !resumeBtn) return;
      startBtn.classList.toggle("d-none", mode !== "idle");
      pauseBtn.classList.toggle("d-none", mode !== "running");
      resumeBtn.classList.toggle("d-none", mode !== "paused");
      timerCard.classList.toggle("is-timer-running", mode === "running");
      if (statusEl) {
        if (mode === "running") statusEl.textContent = "On Track";
        else if (mode === "paused") statusEl.textContent = "Paused";
        else if (mode === "countdown") statusEl.textContent = "Get Set";
        else statusEl.textContent = "Ready";
      }
    }

    let countdownTimeout = null;
    if (startBtn) {
      startBtn.addEventListener("click", function () {
        if (timerInterval) clearInterval(timerInterval);
        if (countdownTimeout) clearTimeout(countdownTimeout);

        if (prefersReducedMotion || elapsedSeconds > 0) {
          timerInterval = setInterval(tick, 1000);
          setTimerState("running");
          return;
        }

        // Playful 3-2-1-GO race start sequence
        let step = 3;
        setTimerState("countdown");
        startBtn.classList.add("d-none");
        const runCountdown = function () {
          if (step > 0) {
            if (displayEl) displayEl.textContent = `0${step}`;
            if (statusEl) statusEl.textContent = step === 3 ? "READY" : step === 2 ? "SET" : "LAUNCH";
            if (window.FitTrackSound) window.FitTrackSound.playCountdownBeep(false);
            step -= 1;
            countdownTimeout = setTimeout(runCountdown, 520);
          } else {
            if (displayEl) displayEl.textContent = "GO!";
            if (window.FitTrackSound) window.FitTrackSound.playCountdownBeep(true);
            countdownTimeout = setTimeout(function () {
              renderTimer();
              timerInterval = setInterval(tick, 1000);
              setTimerState("running");
            }, 340);
          }
        };
        runCountdown();
      });
    }

    if (pauseBtn) {
      pauseBtn.addEventListener("click", function () {
        if (timerInterval) clearInterval(timerInterval);
        if (countdownTimeout) clearTimeout(countdownTimeout);
        timerInterval = null;
        setTimerState("paused");
      });
    }

    if (resumeBtn) {
      resumeBtn.addEventListener("click", function () {
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(tick, 1000);
        setTimerState("running");
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = null;
        remainingSeconds = totalTargetSeconds;
        elapsedSeconds = 0;
        if (timerDurationInput) timerDurationInput.value = String(recMinutes);
        renderTimer();
        setTimerState("idle");
      });
    }

    if (finishForm) {
      finishForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (timerInterval) clearInterval(timerInterval);
        const submitBtn = document.getElementById("timerFinishBtn");
        if (submitBtn) submitBtn.disabled = true;

        try {
          const formData = new FormData(finishForm);
          const response = await fetch(finishForm.action, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: formData,
          });
          const payload = await response.json();
          if (response.ok && payload.ok) {
            setTimerState("idle");
            if (payload.celebration) {
              showCelebrationModal(payload.celebration);
              const modalEl = document.getElementById("adventureCelebrationModal");
              if (modalEl) {
                modalEl.addEventListener(
                  "hidden.bs.modal",
                  function () {
                    if (payload.redirect_url) {
                      window.location.href = payload.redirect_url;
                    }
                  },
                  { once: true }
                );
              }
            } else if (payload.redirect_url) {
              window.location.href = payload.redirect_url;
            }
          } else {
            finishForm.submit();
          }
        } catch (_) {
          finishForm.submit();
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });
    }

    renderTimer();
  }

  // 9. Sports Discovery ("What Should I Play Today?")
  const pickerDataEl = document.getElementById("sports-picker-data");
  const spinPickerBtn = document.getElementById("spinSportPickerBtn");
  if (pickerDataEl && spinPickerBtn) {
    try {
      const sportsList = JSON.parse(pickerDataEl.textContent || "[]");
      const nameEl = document.getElementById("pickerSportName");
      const metaEl = document.getElementById("pickerSportMeta");
      const durEl = document.getElementById("pickerSportDuration");
      const descEl = document.getElementById("pickerSportDesc");
      const gearEl = document.getElementById("pickerSportGear");
      const detailLink = document.getElementById("pickerDetailLink");
      const logLink = document.getElementById("pickerLogLink");

      let lastIndex = 0;
      let isSpinning = false;
      const cardEl = document.getElementById("pickerSportCard");

      function renderSportPick(pick) {
        if (nameEl) nameEl.textContent = pick.name;
        if (metaEl) metaEl.textContent = `${pick.environment} · ${pick.intensity}`;
        if (durEl) durEl.textContent = `${pick.recommended_duration} min`;
        if (descEl) {
          const words = (pick.description || "").split(/\s+/);
          descEl.textContent =
            words.length > 22 ? words.slice(0, 22).join(" ") + "..." : pick.description;
        }
        if (gearEl) gearEl.textContent = pick.equipment_required || "Comfortable athletic gear";
        if (detailLink) detailLink.setAttribute("href", pick.detail_url);
        if (logLink) logLink.setAttribute("href", pick.log_url);
      }

      spinPickerBtn.addEventListener("click", function () {
        if (!sportsList.length || isSpinning) return;
        let finalIndex = Math.floor(Math.random() * sportsList.length);
        if (sportsList.length > 1 && finalIndex === lastIndex) {
          finalIndex = (finalIndex + 1) % sportsList.length;
        }
        lastIndex = finalIndex;

        if (prefersReducedMotion || sportsList.length < 2) {
          renderSportPick(sportsList[finalIndex]);
          return;
        }

        // Playful kinetic slot-reel spin through sports!
        isSpinning = true;
        spinPickerBtn.disabled = true;
        if (cardEl) cardEl.classList.add("is-reel-spinning");
        let ticks = 0;
        const totalTicks = 11;

        function nextTick() {
          ticks += 1;
          const idx = ticks < totalTicks ? (finalIndex + ticks) % sportsList.length : finalIndex;
          renderSportPick(sportsList[idx]);
          if (window.FitTrackSound) window.FitTrackSound.playSlotTick(ticks);

          if (ticks < totalTicks) {
            setTimeout(nextTick, 45 + ticks * 16);
          } else {
            isSpinning = false;
            spinPickerBtn.disabled = false;
            if (cardEl) {
              cardEl.classList.remove("is-reel-spinning");
              cardEl.classList.add("is-reel-landed");
              setTimeout(() => cardEl.classList.remove("is-reel-landed"), 480);
            }
            if (window.FitTrackSound) window.FitTrackSound.playStagePass(3);
          }
        }
        nextTick();
      });
    } catch (err) {
      console.error("Failed to initialize sports picker:", err);
    }
  }

  // 10. 7-Step Interactive FitBuddy Onboarding Tour
  const tourOverlay = document.getElementById("fittrackTourOverlay");
  if (tourOverlay) {
    const steps = [
      {
        title: "Welcome to FitTrack Adventure!",
        body: "Hi! I'm your FitBuddy companion. Every workout you log fills real Reward Jars, advances your streak, and unlocks badges.",
        target: "fitness-world",
      },
      {
        title: "My Fitness World & Reward Jar",
        body: "Watch your active Reward Jar fill up live from 0% to 100% as you complete minutes or weekly workouts.",
        target: "fitness-world",
      },
      {
        title: "Guided Fitness Activities",
        body: "Explore 10 custom-illustrated exercises and launch the interactive Workout Timer directly on any activity detail page.",
        target: "nav-activities",
      },
      {
        title: "Sports Ideas & Daily Spinner",
        body: "Not sure what to play? Visit Sports Ideas and spin 'What Should I Play Today?' for an instant sport adventure.",
        target: "nav-sports",
      },
      {
        title: "Workout Tracker & Streaks",
        body: "Log custom sessions or use quick-fill chips in the Workout Tracker. Daily logs keep your streak flame burning!",
        target: "nav-workouts",
      },
      {
        title: "Custom Reward Jars & Goals",
        body: "Choose between a Popcorn Bucket, Juice Glass, Water Bottle, Flower Pot, Treasure Chest, or Fish Tank for each goal.",
        target: "nav-goals",
      },
      {
        title: "Rewards & Fitness Journey",
        body: "Collect 8 permanent achievement badges on Rewards & Badges, and trace your milestones on Fitness Journey. You're all set!",
        target: "nav-rewards",
      },
    ];

    let stepIndex = 0;
    const counterEl = document.getElementById("tourStepCounter");
    const titleEl = document.getElementById("tourStepTitle");
    const bodyEl = document.getElementById("tourStepBody");
    const skipBtn = document.getElementById("tourSkipBtn");
    const backBtn = document.getElementById("tourBackBtn");
    const nextBtn = document.getElementById("tourNextBtn");

    function clearHighlight() {
      document
        .querySelectorAll(".tour-highlight")
        .forEach((el) => el.classList.remove("tour-highlight"));
    }

    function renderTourStep() {
      const current = steps[stepIndex];
      if (counterEl)
        counterEl.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
      if (titleEl) titleEl.textContent = current.title;
      if (bodyEl) bodyEl.textContent = current.body;
      if (backBtn) backBtn.classList.toggle("d-none", stepIndex === 0);
      if (nextBtn)
        nextBtn.textContent =
          stepIndex === steps.length - 1 ? "Finish Tour" : "Next";

      clearHighlight();
      if (current.target) {
        const targetEl = document.querySelector(
          `[data-tour-id="${current.target}"]`
        );
        if (targetEl) {
          targetEl.classList.add("tour-highlight");
        }
      }
    }

    async function finishTour() {
      clearHighlight();
      tourOverlay.classList.add("d-none");
      const completeUrl = tourOverlay.getAttribute("data-complete-url");
      const csrfToken = tourOverlay.getAttribute("data-csrf");
      if (completeUrl && csrfToken) {
        try {
          const fd = new FormData();
          fd.append("csrfmiddlewaretoken", csrfToken);
          await fetch(completeUrl, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: fd,
          });
        } catch (_) {}
      }
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (stepIndex < steps.length - 1) {
          stepIndex += 1;
          renderTourStep();
        } else {
          finishTour();
        }
      });
    }

    if (backBtn) {
      backBtn.addEventListener("click", function () {
        if (stepIndex > 0) {
          stepIndex -= 1;
          renderTourStep();
        }
      });
    }

    if (skipBtn) {
      skipBtn.addEventListener("click", finishTour);
    }

    renderTourStep();
  }

  // 11. Theme-Aware Chart.js Palette & Live Theme Sync
  function getChartPalette() {
    const isLight =
      window.FitTrackTheme && window.FitTrackTheme.getTheme() === "light";
    if (isLight) {
      return {
        primaryBar: "#15803d",
        secondaryBar: "#c23b1f",
        emptyBar: "#e2e8f0",
        lineStroke: "#047857",
        lineFill: "rgba(4, 120, 87, 0.14)",
        linePoint: "#15803d",
        freqBar: "#c23b1f",
        doughnutPalette: [
          "#15803d",
          "#c23b1f",
          "#0369a1",
          "#7c3aed",
          "#b45309",
          "#0f766e",
        ],
        doughnutBorder: "#ffffff",
        gridColor: "rgba(23, 25, 35, 0.1)",
        tickColor: "#4b5563",
        xTickColor: "#171923",
        legendColor: "#171923",
        tooltipBg: "#171923",
        tooltipBorder: "#334155",
        tooltipTitle: "#f8fafc",
        tooltipBody: "#e2e8f0",
      };
    }
    return {
      primaryBar: "#d4ff2b",
      secondaryBar: "#e04f33",
      emptyBar: "#28324c",
      lineStroke: "#34d399",
      lineFill: "rgba(52, 211, 153, 0.16)",
      linePoint: "#d4ff2b",
      freqBar: "#e04f33",
      doughnutPalette: [
        "#d4ff2b",
        "#e04f33",
        "#34d399",
        "#38bdf8",
        "#fbbf24",
        "#a78bfa",
      ],
      doughnutBorder: "#1b2235",
      gridColor: "rgba(203, 213, 225, 0.12)",
      tickColor: "#cbd5e1",
      xTickColor: "#f8fafc",
      legendColor: "#e2e8f0",
      tooltipBg: "#101322",
      tooltipBorder: "#46557b",
      tooltipTitle: "#f8fafc",
      tooltipBody: "#d4ff2b",
    };
  }

  const themedChartUpdaters = [];

  function applyCommonTooltip(p) {
    return {
      backgroundColor: p.tooltipBg,
      borderColor: p.tooltipBorder,
      borderWidth: 1,
      titleColor: p.tooltipTitle,
      bodyColor: p.tooltipBody,
      padding: 10,
      cornerRadius: 10,
    };
  }

  // 11a. Dashboard Weekly Activity Chart
  const weeklyChartCanvas = document.getElementById("dashboardWeeklyChart");
  if (weeklyChartCanvas && typeof Chart !== "undefined") {
    const labelsEl = document.getElementById("dashboard-weekly-labels");
    const valuesEl = document.getElementById("dashboard-weekly-values");
    if (labelsEl && valuesEl) {
      const labels = JSON.parse(labelsEl.textContent || "[]");
      const values = JSON.parse(valuesEl.textContent || "[]");
      const p = getChartPalette();
      const buildColors = (pal) =>
        values.map((v, idx) =>
          v > 0 ? (idx % 2 === 0 ? pal.primaryBar : pal.secondaryBar) : pal.emptyBar
        );

      const dashChart = new Chart(weeklyChartCanvas, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Workout Minutes",
              data: values,
              backgroundColor: buildColors(p),
              borderRadius: 8,
              maxBarThickness: 36,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...applyCommonTooltip(p),
              callbacks: {
                label: (ctx) => `${ctx.parsed.y} minutes`,
              },
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0, color: p.tickColor },
              grid: { color: p.gridColor },
            },
            x: {
              ticks: { color: p.xTickColor, font: { weight: "600" } },
              grid: { display: false },
            },
          },
        },
      });

      themedChartUpdaters.push(function (pal) {
        dashChart.data.datasets[0].backgroundColor = buildColors(pal);
        dashChart.options.plugins.tooltip = {
          ...dashChart.options.plugins.tooltip,
          ...applyCommonTooltip(pal),
        };
        dashChart.options.scales.y.ticks.color = pal.tickColor;
        dashChart.options.scales.y.grid.color = pal.gridColor;
        dashChart.options.scales.x.ticks.color = pal.xTickColor;
        dashChart.update();
      });
    }
  }

  // 12. Chart.js: Analytics / My Fitness Journey Charts
  if (
    typeof Chart !== "undefined" &&
    document.getElementById("analyticsWeeklyChart")
  ) {
    const readJson = (id) => {
      const el = document.getElementById(id);
      return el ? JSON.parse(el.textContent || "[]") : [];
    };

    const weeklyLabels = readJson("analytics-weekly-labels");
    const weeklyDuration = readJson("analytics-weekly-duration");
    const weeklyFrequency = readJson("analytics-weekly-frequency");
    const monthLabels = readJson("analytics-month-labels");
    const monthValues = readJson("analytics-month-values");
    const distLabels = readJson("analytics-dist-labels");
    const distValues = readJson("analytics-dist-values");
    const p = getChartPalette();

    const weeklyChart = new Chart(document.getElementById("analyticsWeeklyChart"), {
      type: "bar",
      data: {
        labels: weeklyLabels,
        datasets: [
          {
            label: "Minutes",
            data: weeklyDuration,
            backgroundColor: p.primaryBar,
            borderRadius: 8,
            maxBarThickness: 34,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: applyCommonTooltip(p) },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: p.tickColor },
            grid: { color: p.gridColor },
          },
          x: {
            ticks: { color: p.xTickColor },
            grid: { display: false },
          },
        },
      },
    });

    const monthlyChart = new Chart(document.getElementById("analyticsMonthlyChart"), {
      type: "line",
      data: {
        labels: monthLabels,
        datasets: [
          {
            label: "Monthly Minutes",
            data: monthValues,
            borderColor: p.lineStroke,
            backgroundColor: p.lineFill,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: p.linePoint,
            pointRadius: 5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: applyCommonTooltip(p) },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: p.tickColor },
            grid: { color: p.gridColor },
          },
          x: {
            ticks: { color: p.xTickColor },
            grid: { display: false },
          },
        },
      },
    });

    let distChart = null;
    const distCanvas = document.getElementById("analyticsDistributionChart");
    if (distCanvas && distLabels.length > 0) {
      distChart = new Chart(distCanvas, {
        type: "doughnut",
        data: {
          labels: distLabels,
          datasets: [
            {
              data: distValues,
              backgroundColor: p.doughnutPalette,
              borderWidth: 2,
              borderColor: p.doughnutBorder,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            tooltip: applyCommonTooltip(p),
            legend: {
              position: "bottom",
              labels: { color: p.legendColor, boxWidth: 12, padding: 14 },
            },
          },
          cutout: "62%",
        },
      });
    }

    const freqChart = new Chart(document.getElementById("analyticsFrequencyChart"), {
      type: "bar",
      data: {
        labels: weeklyLabels,
        datasets: [
          {
            label: "Workouts",
            data: weeklyFrequency,
            backgroundColor: p.freqBar,
            borderRadius: 8,
            maxBarThickness: 34,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: applyCommonTooltip(p) },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1, precision: 0, color: p.tickColor },
            grid: { color: p.gridColor },
          },
          x: {
            ticks: { color: p.xTickColor },
            grid: { display: false },
          },
        },
      },
    });

    themedChartUpdaters.push(function (pal) {
      [weeklyChart, monthlyChart, freqChart].forEach(function (chart) {
        chart.options.plugins.tooltip = applyCommonTooltip(pal);
        chart.options.scales.y.ticks.color = pal.tickColor;
        chart.options.scales.y.grid.color = pal.gridColor;
        chart.options.scales.x.ticks.color = pal.xTickColor;
      });
      weeklyChart.data.datasets[0].backgroundColor = pal.primaryBar;
      monthlyChart.data.datasets[0].borderColor = pal.lineStroke;
      monthlyChart.data.datasets[0].backgroundColor = pal.lineFill;
      monthlyChart.data.datasets[0].pointBackgroundColor = pal.linePoint;
      freqChart.data.datasets[0].backgroundColor = pal.freqBar;
      weeklyChart.update();
      monthlyChart.update();
      freqChart.update();

      if (distChart) {
        distChart.data.datasets[0].backgroundColor = pal.doughnutPalette;
        distChart.data.datasets[0].borderColor = pal.doughnutBorder;
        distChart.options.plugins.tooltip = applyCommonTooltip(pal);
        distChart.options.plugins.legend.labels.color = pal.legendColor;
        distChart.update();
      }
    });
  }

  window.addEventListener("fittrack:themechange", function () {
    const pal = getChartPalette();
    themedChartUpdaters.forEach(function (fn) {
      fn(pal);
    });
  });
});
