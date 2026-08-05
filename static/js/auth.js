// Shared behaviour for the login and forgot-password pages:
// password show/hide, inline validation, and a loading state on submit.

(function () {
  "use strict";

  // Password show / hide
  var toggle = document.getElementById("togglePw");
  var password = document.getElementById("password");
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

  // Validate on submit, then show the loading state and let the form post.
  var form = document.getElementById("loginForm") || document.getElementById("resetForm");
  if (!form) return;

  var btn = document.getElementById("submitBtn");
  var emailField = document.getElementById("emailField");
  var pwField = document.getElementById("pwField");
  var email = document.getElementById("email");

  form.addEventListener("submit", function (e) {
    var ok = true;

    if (emailField) emailField.classList.remove("invalid");
    if (pwField) pwField.classList.remove("invalid");

    if (email && !isValidEmail(email.value.trim())) {
      if (emailField) emailField.classList.add("invalid");
      ok = false;
    }
    if (password && password.value.length < 1) {
      if (pwField) pwField.classList.add("invalid");
      ok = false;
    }

    if (!ok) {
      e.preventDefault();
      return;
    }

    // Valid — show loading and allow the real POST to proceed.
    if (btn) {
      btn.classList.add("loading");
      btn.disabled = true;
    }
  });
})();
