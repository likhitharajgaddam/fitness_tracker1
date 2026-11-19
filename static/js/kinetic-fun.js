/**
 * FitTrack Site-Wide Kinetic Fun & Micro-Interaction Engine
 * Brings the whole website alive: starry track ambient backdrop, 3D card tilt + glare,
 * particle bursts on actions, staggered scroll entrances, and playful FitBuddy reactions.
 */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const prefersReducedMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // 1. Ambient Night-Sky Starfield & Rising Kinetic Embers Canvas (for non-WebGL pages)
    const ambientCanvas = document.getElementById("kineticAmbientCanvas");
    if (ambientCanvas && !prefersReducedMotion) {
      const ctx = ambientCanvas.getContext("2d");
      if (ctx) {
        let w = 0;
        let h = 0;
        const stars = Array.from({ length: 54 }, () => ({
          x: Math.random(),
          y: Math.random(),
          r: 0.7 + Math.random() * 1.4,
          twinkle: Math.random() * Math.PI * 2,
          speed: 0.4 + Math.random() * 1.2,
          tint: Math.random() > 0.8 ? "#d4ff2b" : "#f5f5ee",
        }));
        const embers = Array.from({ length: 16 }, () => ({
          x: Math.random(),
          y: Math.random(),
          vy: 0.00025 + Math.random() * 0.00055,
          vx: (Math.random() - 0.5) * 0.0002,
          size: 1.5 + Math.random() * 2.2,
          alpha: 0.14 + Math.random() * 0.25,
          color: Math.random() > 0.35 ? "#d4ff2b" : "#de5235",
        }));

        function resizeAmbient() {
          w = ambientCanvas.width = window.innerWidth;
          h = ambientCanvas.height = window.innerHeight;
        }
        resizeAmbient();
        window.addEventListener("resize", resizeAmbient);

        let lastTime = performance.now();
        function drawAmbient(now) {
          const dt = Math.min((now - lastTime) / 1000, 0.05);
          lastTime = now;
          const isLight = document.documentElement.getAttribute("data-theme") === "light";
          ctx.clearRect(0, 0, w, h);

          // Twinkling stars (Dark) / delicate athletic dust motes (Light)
          for (let i = 0; i < stars.length; i++) {
            const s = stars[i];
            s.twinkle += dt * s.speed;
            const op = isLight
              ? 0.08 + 0.14 * (0.5 + 0.5 * Math.sin(s.twinkle))
              : 0.15 + 0.36 * (0.5 + 0.5 * Math.sin(s.twinkle));
            ctx.globalAlpha = op;
            ctx.fillStyle = isLight
              ? s.tint === "#d4ff2b"
                ? "#15803d"
                : "#64748b"
              : s.tint;
            ctx.beginPath();
            ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
            ctx.fill();
          }

          // Rising kinetic embers
          for (let i = 0; i < embers.length; i++) {
            const e = embers[i];
            e.y -= e.vy * (dt * 60);
            e.x += e.vx * (dt * 60);
            if (e.y < -0.05) {
              e.y = 1.05;
              e.x = Math.random();
            }
            ctx.globalAlpha = isLight ? e.alpha * 0.55 : e.alpha;
            ctx.fillStyle = isLight
              ? e.color === "#d4ff2b"
                ? "#15803d"
                : "#c23b1f"
              : e.color;
            ctx.beginPath();
            ctx.arc(e.x * w, e.y * h, e.size, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.globalAlpha = 1;
          requestAnimationFrame(drawAmbient);
        }
        requestAnimationFrame(drawAmbient);
      }
    }

    // 2. Crisp Particle Spark Burst on Primary Buttons & Interactive Actions
    function spawnSparkBurst(clientX, clientY, count = 14) {
      if (prefersReducedMotion) return;
      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      const palette = isLight
        ? ["#15803d", "#c23b1f", "#0369a1", "#10b981", "#d97706"]
        : ["#d4ff2b", "#f8fafc", "#e04f33", "#34d399", "#fbbf24"];
      const layer = document.createElement("div");
      layer.className = "kinetic-spark-layer";
      layer.style.left = clientX + "px";
      layer.style.top = clientY + "px";
      document.body.appendChild(layer);

      for (let i = 0; i < count; i++) {
        const spark = document.createElement("span");
        spark.className = "kinetic-spark";
        const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.4;
        const dist = 24 + Math.random() * 44;
        const dx = Math.cos(angle) * dist;
        const dy = Math.sin(angle) * dist - 10;
        spark.style.setProperty("--dx", dx.toFixed(1) + "px");
        spark.style.setProperty("--dy", dy.toFixed(1) + "px");
        spark.style.backgroundColor =
          palette[Math.floor(Math.random() * palette.length)];
        layer.appendChild(spark);
      }

      setTimeout(() => layer.remove(), 620);
    }

    window.FitTrackFX = {
      spawnSparkBurst,
    };

    document.addEventListener("click", function (e) {
      const btn = e.target.closest(
        ".btn-lime, .btn-emerald, .btn-purple, .quick-chip, .filter-tab, #spinSportPickerBtn, #fitbuddyToggleBtn"
      );
      if (!btn) return;
      if (window.FitTrackSound) window.FitTrackSound.playClick();
      if (e.clientX || e.clientY) {
        spawnSparkBurst(e.clientX, e.clientY, btn.classList.contains("btn-lime") || btn.classList.contains("btn-emerald") ? 16 : 9);
      }
    });

    // 3. Interactive 3D Perspective Tilt + Directional Lime Glare on Cards & Race Bibs
    if (!prefersReducedMotion) {
      const tiltEls = document.querySelectorAll(
        ".surface-card-hover, .race-bib-card, [data-tilt-card]"
      );
      tiltEls.forEach(function (card) {
        card.addEventListener("pointermove", function (e) {
          const rect = card.getBoundingClientRect();
          if (!rect.width || !rect.height) return;
          const px = (e.clientX - rect.left) / rect.width;
          const py = (e.clientY - rect.top) / rect.height;
          const rotY = (px - 0.5) * 9;
          const rotX = (0.5 - py) * 8;
          card.style.setProperty("--tilt-rx", rotX.toFixed(2) + "deg");
          card.style.setProperty("--tilt-ry", rotY.toFixed(2) + "deg");
          card.style.setProperty("--glare-x", (px * 100).toFixed(1) + "%");
          card.style.setProperty("--glare-y", (py * 100).toFixed(1) + "%");
          card.classList.add("is-tilting");
        });
        card.addEventListener("pointerleave", function () {
          card.classList.remove("is-tilting");
          card.style.setProperty("--tilt-rx", "0deg");
          card.style.setProperty("--tilt-ry", "0deg");
        });
      });
    }

    // 4. Staggered Scroll-Choreographed Kinetic Entrance (Zero-Latency DOM Safe)
    const revealEls = document.querySelectorAll(
      ".surface-card, .surface-tint-lavender, .surface-tint-mint, .surface-tint-peach, .surface-tint-sky, .journey-node"
    );
    if (!prefersReducedMotion && "IntersectionObserver" in window && revealEls.length) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("kinetic-entered");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.06, rootMargin: "0px 0px -24px 0px" }
      );

      revealEls.forEach((el, idx) => {
        // Elements already visible above the fold enter immediately with subtle stagger
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.92) {
          el.style.setProperty("--stagger-delay", `${Math.min(idx % 6, 5) * 45}ms`);
          el.classList.add("kinetic-ready", "kinetic-entered");
        } else {
          el.style.setProperty("--stagger-delay", `${(idx % 4) * 55}ms`);
          el.classList.add("kinetic-ready");
          observer.observe(el);
        }
      });
    }

    // 5. Playful Reward Jar Hover Surge (speeds up bubbles / popcorn / fish playfully)
    document.querySelectorAll(".reward-jar-stage").forEach(function (jar) {
      jar.addEventListener("mouseenter", function () {
        jar.classList.add("jar-excited");
        if (window.FitTrackSound) window.FitTrackSound.playHoverTick();
      });
      jar.addEventListener("mouseleave", function () {
        jar.classList.remove("jar-excited");
      });
    });

    // 6. Playful FitBuddy Click Bounce & Cheer Burst
    const fitbuddyToggle = document.getElementById("fitbuddyToggleBtn");
    if (fitbuddyToggle) {
      fitbuddyToggle.addEventListener("click", function () {
        fitbuddyToggle.classList.remove("fitbuddy-hop");
        void fitbuddyToggle.offsetWidth;
        fitbuddyToggle.classList.add("fitbuddy-hop");
      });
    }
  });
})();
