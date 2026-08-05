// Shared behaviour for the login, forgot-password, and register pages:
// password show/hide, inline validation, a password strength meter,
// and a loading state on submit.

(function () {
  "use strict";

  var password = document.getElementById("password");

  // Password show / hide
  var toggle = document.getElementById("togglePw");
  if (toggle && password) {
    toggle.addEventListener("click", function () {
      var show = password.type === "password";
      password.type = show ? "text" : "password";
      toggle.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
      toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  }

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  // Password strength meter (register page only)
  var meter = document.getElementById("pwMeter");
  var hint = document.getElementById("pwHint");
  if (meter && password) {
    password.addEventListener("input", function () {
      var v = password.value;
      var score = 0;
      if (v.length >= 8) score++;
      if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
      if (/\d/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;

      meter.className = "pw-meter" + (v ? " s" + score : "");
      if (hint) {
        if (!v) hint.textContent = "Use 8+ characters with a mix of letters, numbers & symbols.";
        else if (score <= 1) hint.textContent = "Weak password.";
        else if (score === 2) hint.textContent = "Fair — add numbers or symbols.";
        else if (score === 3) hint.textContent = "Good password.";
        else hint.textContent = "Strong password.";
      }
    });
  }

  // Pick whichever form is on this page
  var form = document.getElementById("loginForm")
          || document.getElementById("resetForm")
          || document.getElementById("registerForm");
  if (!form) return;

  var isRegister = form.id === "registerForm";
  var btn = document.getElementById("submitBtn");
  var nameField = document.getElementById("nameField");
  var emailField = document.getElementById("emailField");
  var pwField = document.getElementById("pwField");
  var name = document.getElementById("name");
  var email = document.getElementById("email");

  form.addEventListener("submit", function (e) {
    var ok = true;

    if (nameField) nameField.classList.remove("invalid");
    if (emailField) emailField.classList.remove("invalid");
    if (pwField) pwField.classList.remove("invalid");

    if (name && name.value.trim().length < 1) {
      nameField.classList.add("invalid");
      ok = false;
    }
    if (email && !isValidEmail(email.value.trim())) {
      if (emailField) emailField.classList.add("invalid");
      ok = false;
    }
    if (password) {
      // Register needs 8+, login just needs non-empty.
      var minLen = isRegister ? 8 : 1;
      if (password.value.length < minLen) {
        if (pwField) pwField.classList.add("invalid");
        ok = false;
      }
    }

    if (!ok) {
      e.preventDefault();
      return;
    }

    if (btn) {
      btn.classList.add("loading");
      btn.disabled = true;
    }
  });
})();
