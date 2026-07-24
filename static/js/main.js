// ============================================
// static/js/main.js  —  Frontend JavaScript v4
// ============================================
// Motion split:
//   CSS      → entrance, hover, press, focus, skeletons, page transitions
//   GSAP     → number count-ups, chart draw-in on scroll
//   Three.js → homepage hero gradient mesh (lazy, homepage only)
// ============================================

document.addEventListener('DOMContentLoaded', function () {

  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Dark Mode Toggle ────────────────────────────────────────────
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');
  const root = document.documentElement;

  function updateThemeIcon() {
    const current = root.getAttribute('data-theme');
    if (themeIcon) {
      themeIcon.className = current === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
  }
  updateThemeIcon();

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function () {
      const current = root.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      localStorage.setItem('talentai_theme', next);
      updateThemeIcon();
    });
  }

  // ── Auto-dismiss flash alerts after 4 seconds ──────────────────────
  setTimeout(function () {
    document.querySelectorAll('.alert').forEach(function (alert) {
      var bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 4000);

  // ── Skills input: auto lowercase + preview tags ────────────────────
  const skillsInput = document.querySelector('input[name="required_skills"]');
  if (skillsInput) {
    skillsInput.addEventListener('blur', function () {
      this.value = this.value.toLowerCase();
    });

    skillsInput.addEventListener('input', function () {
      const preview = document.getElementById('skillsPreview');
      if (!preview) return;
      const skills = this.value.split(',').map(s => s.trim()).filter(Boolean);
      preview.innerHTML = skills.map(s =>
        `<span class="badge bg-primary me-1 mb-1">${s}</span>`
      ).join('');
    });
  }

  // ── Score bars fill on load ───────────────────────────────────────
  document.querySelectorAll('.progress-bar').forEach(function (bar) {
    const target = bar.style.width;
    if (REDUCED) return;
    bar.style.width = '0%';
    setTimeout(function () {
      bar.style.transition = 'width 600ms cubic-bezier(0.2, 0, 0, 1)';
      bar.style.width = target;
    }, 120);
  });

  // ── Confirm before status change ──────────────────────────────────
  document.querySelectorAll('select[name="status"]').forEach(function (sel) {
    sel.addEventListener('change', function () {
      const val = this.value;
      if (val === 'rejected' || val === 'hired') {
        if (!confirm(`Set status to "${val}"?`)) {
          this.value = this.dataset.prev || 'applied';
          return;
        }
      }
      this.dataset.prev = val;
    });
    sel.dataset.prev = sel.value;
  });

  // ── Tooltip init ──────────────────────────────────────────────────
  var tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // ── Job Search & Filter (Candidate Dashboard) ──────────────────────
  const jobSearchInput   = document.getElementById('jobSearchInput');
  const jobLocationFilter = document.getElementById('jobLocationFilter');
  const jobSkillFilter   = document.getElementById('jobSkillFilter');
  const jobCards         = document.querySelectorAll('.job-card-wrapper');
  const noJobsMsg        = document.getElementById('noJobsFound');

  function filterJobs() {
    if (!jobCards.length) return;

    const searchTerm = (jobSearchInput?.value || '').toLowerCase().trim();
    const locationVal = (jobLocationFilter?.value || '').toLowerCase();
    const skillVal     = (jobSkillFilter?.value || '').toLowerCase();

    let visibleCount = 0;

    jobCards.forEach(function (card) {
      const title    = (card.dataset.title || '').toLowerCase();
      const location = (card.dataset.location || '').toLowerCase();
      const skills   = (card.dataset.skills || '').toLowerCase();

      const matchesSearch   = !searchTerm || title.includes(searchTerm) || skills.includes(searchTerm);
      const matchesLocation = !locationVal || location.includes(locationVal);
      const matchesSkill    = !skillVal || skills.includes(skillVal);

      if (matchesSearch && matchesLocation && matchesSkill) {
        card.style.display = '';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    if (noJobsMsg) {
      noJobsMsg.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  if (jobSearchInput)    jobSearchInput.addEventListener('input', filterJobs);
  if (jobLocationFilter) jobLocationFilter.addEventListener('change', filterJobs);
  if (jobSkillFilter)    jobSkillFilter.addEventListener('change', filterJobs);

  // ── Clear Filters Button ───────────────────────────────────────────
  const clearFiltersBtn = document.getElementById('clearFiltersBtn');
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', function () {
      if (jobSearchInput) jobSearchInput.value = '';
      if (jobLocationFilter) jobLocationFilter.value = '';
      if (jobSkillFilter) jobSkillFilter.value = '';
      filterJobs();
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // MOTION
  // ══════════════════════════════════════════════════════════════════

  const CDN = {
    gsap:          'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js',
    scrollTrigger: 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js',
    three:         'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js',
    hero3d:        '/static/js/hero-3d.js'
  };

  const loaded = {};
  function loadScript(src) {
    if (loaded[src]) return loaded[src];
    loaded[src] = new Promise(function (resolve, reject) {
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
    return loaded[src];
  }

  // ── Chart skeletons ────────────────────────────────────────────────
  // Plotly renders after its own script runs. Until then the container
  // is empty, so show a skeleton rather than blank space.
  document.querySelectorAll('[id^="chart"]').forEach(function (host) {
    if (host.querySelector('.js-plotly-plot')) return;
    const sk = document.createElement('div');
    sk.className = 'skeleton skeleton-chart';
    sk.dataset.chartSkeleton = '1';
    host.appendChild(sk);
  });

  function clearSkeletons() {
    document.querySelectorAll('[data-chart-skeleton]').forEach(function (sk) {
      sk.remove();
    });
  }

  // ── Number count-ups + chart draw-in (GSAP) ────────────────────────
  const numberEls = Array.prototype.filter.call(
    document.querySelectorAll('.stat-number, .stat-number-sm, .display-6'),
    function (el) { return /^[\d.,]+%?$/.test(el.textContent.trim()); }
  );

  const hasPlots  = document.querySelectorAll('.js-plotly-plot').length > 0;
  const needsGSAP = numberEls.length > 0 || hasPlots;

  if (REDUCED || !needsGSAP) {
    clearSkeletons();
  } else {
    loadScript(CDN.gsap)
      .then(function () { return loadScript(CDN.scrollTrigger); })
      .then(function () {
        gsap.registerPlugin(ScrollTrigger);

        // Count-ups — numbers roll to their real value
        numberEls.forEach(function (el) {
          const raw      = el.textContent.trim();
          const suffix   = raw.endsWith('%') ? '%' : '';
          const decimals = (raw.split('.')[1] || '').replace('%', '').length;
          const target   = parseFloat(raw.replace(/[^\d.]/g, ''));
          if (isNaN(target)) return;

          const counter = { v: 0 };
          gsap.to(counter, {
            v: target,
            duration: 0.6,
            ease: 'power2.out',
            scrollTrigger: { trigger: el, start: 'top 92%', once: true },
            onUpdate: function () {
              el.textContent = counter.v.toFixed(decimals) + suffix;
            },
            onComplete: function () {
              el.textContent = raw;   // restore the exact original string
            }
          });
        });

        // Charts draw in when they reach the viewport
        document.querySelectorAll('.js-plotly-plot').forEach(function (plot) {
          gsap.fromTo(plot,
            { opacity: 0, y: 20 },
            {
              opacity: 1, y: 0,
              duration: 0.6,
              ease: 'power2.out',
              scrollTrigger: { trigger: plot, start: 'top 88%', once: true }
            }
          );
        });

        clearSkeletons();
      })
      .catch(clearSkeletons);   // GSAP blocked or offline — show content anyway
  }

  // ── Homepage hero gradient mesh (lazy, homepage only) ──────────────
  const hero = document.querySelector('.hero-section');
  if (hero && !REDUCED && window.innerWidth > 768) {
    const idle = window.requestIdleCallback || function (fn) { setTimeout(fn, 400); };
    idle(function () {
      loadScript(CDN.three)
        .then(function () { return loadScript(CDN.hero3d); })
        .catch(function () { /* hero stays flat — nothing breaks */ });
    });
  }

});
