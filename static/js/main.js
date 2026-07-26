// ============================================
// static/js/main.js  —  Frontend JavaScript v2
// ============================================

document.addEventListener('DOMContentLoaded', function () {

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

  // ── Score bar animation on page load ──────────────────────────────
  document.querySelectorAll('.progress-bar').forEach(function (bar) {
    const target = bar.style.width;
    bar.style.width = '0%';
    setTimeout(function () {
      bar.style.transition = 'width 0.8s ease-in-out';
      bar.style.width = target;
    }, 300);
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

});
