(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { csrf: null, emailChallenge: null, phoneChallenge: null };

  async function csrf() {
    if (state.csrf) return state.csrf;
    const response = await fetch("/api/auth/csrf", { credentials: "same-origin" });
    if (!response.ok) throw new Error("csrf_unavailable");
    state.csrf = (await response.json()).csrf_token;
    return state.csrf;
  }

  async function request(path, options = {}) {
    const headers = { "X-CSRF-Token": await csrf(), ...(options.headers || {}) };
    const response = await fetch(path, { credentials: "same-origin", ...options, headers });
    let body = {};
    try { body = await response.json(); } catch (_) { /* keep safe generic response */ }
    return { response, body };
  }

  function statusFor(element, message, tone = "") {
    if (!element) return;
    element.textContent = message;
    element.classList.toggle("is-success", tone === "success");
    element.classList.toggle("is-progress", tone === "progress");
  }

  function busy(button, busyState, label) {
    if (!button) return;
    if (busyState) {
      button.dataset.originalLabel = button.textContent;
      button.disabled = true;
      button.classList.add("auth-loading");
      button.setAttribute("aria-busy", "true");
    } else {
      button.disabled = false;
      button.classList.remove("auth-loading");
      button.removeAttribute("aria-busy");
      if (label) button.textContent = label;
    }
  }

  function cooldown(button, seconds, label = "Send code") {
    if (!button) return;
    let remaining = seconds;
    button.disabled = true;
    button.textContent = `${label} in ${remaining}s`;
    const timer = window.setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) { window.clearInterval(timer); button.disabled = false; button.textContent = label; return; }
      button.textContent = `${label} in ${remaining}s`;
    }, 1000);
  }

  function enablePasswordToggles() {
    $$('[data-password-toggle]').forEach((button) => {
      button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.passwordToggle);
        if (!input) return;
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.textContent = showing ? "Show" : "Hide";
        button.setAttribute("aria-label", `${showing ? "Show" : "Hide"} password`);
      });
    });
  }

  function showSignedOut() {
    const marker = $("[data-signed-out]");
    if (marker && new URLSearchParams(window.location.search).get("signed_out") === "true") {
      marker.hidden = false;
    }
    const registered = $("[data-registered]");
    if (registered && new URLSearchParams(window.location.search).get("registered") === "true") {
      registered.hidden = false;
    }
  }

  function initLogin() {
    const form = $("[data-auth-form='login']");
    if (!form) return;
    const passwordMode = $("[data-login-mode='password']");
    const emailMode = $("[data-login-mode='email']");
    const passwordPanel = $("[data-login-panel='password']");
    const emailPanel = $("[data-login-panel='email']");
    const email = $("#login-email");
    const password = $("#login-password");
    const remember = $("#login-remember");
    const status = $("[data-auth-status]");

    function selectMode(mode) {
      const emailSelected = mode === "email";
      passwordPanel.hidden = emailSelected;
      emailPanel.hidden = !emailSelected;
      passwordMode.classList.toggle("is-selected", !emailSelected);
      emailMode.classList.toggle("is-selected", emailSelected);
      passwordMode.setAttribute("aria-selected", String(!emailSelected));
      emailMode.setAttribute("aria-selected", String(emailSelected));
      $("#login-username").required = !emailSelected;
      password.required = !emailSelected;
      email.required = emailSelected;
      $("#login-code").required = emailSelected;
      (emailSelected ? email : password).focus();
      statusFor(status, "");
    }
    passwordMode?.addEventListener("click", () => selectMode("password"));
    emailMode?.addEventListener("click", () => selectMode("email"));

    $("[data-login-send-code]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      if (!email.value.trim()) { statusFor(status, "Enter your account email first."); email.focus(); return; }
      busy(button, true);
      try {
        const { response } = await request("/api/auth/email/send-code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: email.value.trim() }) });
        statusFor(status, response.ok ? "If the account is eligible, a verification code has been sent." : "Email verification is temporarily unavailable.", response.ok ? "progress" : "");
        if (response.ok) $("#login-code")?.focus();
      } catch (_) { statusFor(status, "Email verification is temporarily unavailable."); }
      busy(button, false, "Send code");
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const isEmail = !emailPanel.hidden;
      const button = $("[type='submit']", form);
      busy(button, true);
      try {
        const payload = isEmail
          ? { challenge_id: state.emailChallenge || undefined, code: $("#login-code").value.trim(), remember_me: remember.checked }
          : { username: $("#login-username").value.trim(), password: password.value, remember_me: remember.checked };
        const endpoint = isEmail ? "/api/auth/email/verify-code" : "/api/auth/login";
        const { response } = await request(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (response.ok) { statusFor(status, "Identity verified. Opening your workspace…", "success"); window.location.assign("/"); }
        else statusFor(status, isEmail ? "Verification failed or expired. Request a new code and try again." : "Sign-in failed. Check your credentials and try again.");
      } catch (_) { statusFor(status, "Sign-in is temporarily unavailable. Try again shortly."); }
      busy(button, false, isEmail ? "Verify and sign in" : "Sign in");
    });
  }

  function initSignup() {
    const form = $("[data-auth-form='signup']");
    if (!form) return;
    const status = $("[data-auth-status]");
    const country = $("#signup-country");
    const password = $("#signup-password");
    const confirm = $("#confirm");
    const strengthLabel = $("[data-strength-label]");
    const strengthBars = $$('[data-strength-bar]');
    const setStatus = (message, tone = "") => statusFor(status, message, tone);

    const picker = $("[data-country-picker]");
    const trigger = $(".country-trigger", picker);
    const menu = $(".country-menu", picker);
    const search = $("#signup-country-search");
    const options = $("[data-country-options]", picker);
    const label = $("[data-country-label]", picker);
    let countries = [];
    let highlighted = -1;
    const flagFor = (region) => [...String(region || "")].map((letter) => String.fromCodePoint(letter.charCodeAt(0) + 127397)).join("");
    const displayName = (region) => {
      try { return new Intl.DisplayNames([navigator.language || "en"], { type: "region" }).of(region) || region; }
      catch (_) { return region; }
    };
    function renderCountries() {
      const query = (search?.value || "").trim().toLowerCase();
      const visible = countries.filter((item) => `${displayName(item.region)} ${item.calling_code} ${item.region}`.toLowerCase().includes(query));
      options.replaceChildren();
      highlighted = visible.length ? 0 : -1;
      visible.forEach((item, index) => {
        const option = document.createElement("button");
        option.type = "button"; option.className = "country-option"; option.setAttribute("role", "option");
        option.dataset.region = item.region; option.setAttribute("aria-selected", String(index === highlighted));
        const flag = document.createElement("span"); flag.className = "country-flag"; flag.setAttribute("aria-hidden", "true"); flag.textContent = flagFor(item.region);
        const text = document.createElement("span"); text.textContent = `${displayName(item.region)} ${item.calling_code}`;
        option.append(flag, text); option.addEventListener("click", () => chooseCountry(item)); options.append(option);
      });
      if (!visible.length) { const empty = document.createElement("div"); empty.className = "country-empty"; empty.textContent = "No matching country."; options.append(empty); }
      return visible;
    }
    function chooseCountry(item) {
      country.value = item.region;
      label.textContent = `${flagFor(item.region)} ${displayName(item.region)} (${item.calling_code})`;
      menu.hidden = true; trigger.setAttribute("aria-expanded", "false"); trigger.focus();
    }
    function openCountries() { menu.hidden = false; trigger.setAttribute("aria-expanded", "true"); renderCountries(); search.focus(); }
    trigger.addEventListener("click", () => menu.hidden ? openCountries() : (menu.hidden = true, trigger.setAttribute("aria-expanded", "false")));
    search.addEventListener("input", renderCountries);
    search.addEventListener("keydown", (event) => {
      const visible = [...options.querySelectorAll(".country-option")];
      if (!visible.length) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); highlighted = (highlighted + (event.key === "ArrowDown" ? 1 : visible.length - 1)) % visible.length; visible.forEach((item, index) => item.setAttribute("aria-selected", String(index === highlighted))); visible[highlighted].scrollIntoView({ block: "nearest" }); }
      if (event.key === "Enter" && highlighted >= 0) { event.preventDefault(); visible[highlighted].click(); }
      if (event.key === "Escape") { menu.hidden = true; trigger.setAttribute("aria-expanded", "false"); trigger.focus(); }
    });
    document.addEventListener("click", (event) => { if (picker && !picker.contains(event.target) && !menu.hidden) { menu.hidden = true; trigger.setAttribute("aria-expanded", "false"); } });

    fetch("/api/auth/countries", { credentials: "same-origin" }).then((response) => {
      if (!response.ok) throw new Error("countries_unavailable");
      return response.json();
    }).then((data) => {
      countries = data.countries || [];
      country.replaceChildren(new Option("Select country", ""));
      countries.forEach((item) => country.add(new Option(`${displayName(item.region)} (${item.calling_code})`, item.region)));
      label.textContent = "Select country";
    }).catch(() => { country.replaceChildren(new Option("Country list unavailable", "")); setStatus("Country selection is temporarily unavailable."); });

    function updateStrength() {
      const value = password.value;
      let score = 0;
      if (value.length >= 10) score++;
      if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
      if (/\d/.test(value)) score++;
      if (/[^A-Za-z0-9]/.test(value)) score++;
      strengthBars.forEach((bar, index) => bar.classList.toggle("is-on", index < score));
      if (strengthLabel) strengthLabel.textContent = score < 2 ? "Use 10+ characters with mixed case, numbers, and symbols." : score < 4 ? "Good start — add another character type." : "Password meets the local strength guidance.";
    }
    password.addEventListener("input", updateStrength);

    $("[data-signup-email-send]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      let sent = false;
      busy(button, true);
      try {
        const { response, body } = await request("/api/auth/email/send-registration-code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: $("#signup-email").value.trim() }) });
        if (response.ok) { state.emailChallenge = body.challenge_id || "pending"; setStatus("If eligible, an email verification code has been sent.", "progress"); $("#signup-email-code")?.focus(); sent = true; }
        else setStatus("Email verification is temporarily unavailable.");
      } catch (_) { setStatus("Email verification is temporarily unavailable."); }
      busy(button, false, "Send code");
      if (sent) cooldown(button, 60);
    });
    $("[data-signup-email-verify]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget; busy(button, true);
      try {
        const { response } = await request("/api/auth/email/verify-registration-code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ challenge_id: state.emailChallenge, code: $("#signup-email-code").value.trim() }) });
        setStatus(response.ok ? "Email verified." : "Email verification failed or expired.", response.ok ? "success" : "");
      } catch (_) { setStatus("Email verification is temporarily unavailable."); }
      busy(button, false, "Verify");
    });
    $("[data-signup-phone-send]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget; let sent = false; busy(button, true);
      try {
        const { response, body } = await request("/api/auth/phone/send-code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ country: country.value, phone: $("#signup-phone").value.trim() }) });
        if (response.ok) { state.phoneChallenge = body.challenge_id; setStatus("Phone code sent.", "progress"); $("#signup-phone-code")?.focus(); sent = true; }
        else setStatus("Unable to send a phone code.");
      } catch (_) { setStatus("Phone verification is temporarily unavailable."); }
      busy(button, false, "Send code");
      if (sent) cooldown(button, 60);
    });
    $("[data-signup-phone-verify]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget; busy(button, true);
      try {
        const { response } = await request("/api/auth/phone/verify-code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ challenge_id: state.phoneChallenge, code: $("#signup-phone-code").value.trim() }) });
        setStatus(response.ok ? "Phone verified." : "Phone verification failed or expired.", response.ok ? "success" : "");
      } catch (_) { setStatus("Phone verification is temporarily unavailable."); }
      busy(button, false, "Verify");
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (password.value !== confirm.value) { setStatus("Passwords do not match."); confirm.focus(); return; }
      const button = $("[type='submit']", form); busy(button, true);
      try {
        const payload = { username: $("#signup-username").value.trim(), email: $("#signup-email").value.trim(), password: password.value, date_of_birth: $("#signup-dob").value, country: country.value, phone: $("#signup-phone").value.trim(), phone_challenge_id: state.phoneChallenge, email_challenge_id: state.emailChallenge || "pending" };
        const { response } = await request("/api/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (response.ok) { setStatus("Account created. Continue to sign in.", "success"); window.location.assign("/login?registered=true"); }
        else setStatus("Unable to create the account. Check the information and verification status.");
      } catch (_) { setStatus("Account creation is temporarily unavailable. Try again shortly."); }
      busy(button, false, "Create analyst account");
    });
  }

  function initRecovery() {
    const form = $("[data-auth-form='recovery']");
    if (!form) return;
    const status = $("[data-auth-status]");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = $("[type='submit']", form); busy(button, true);
      try {
        const { response, body } = await request("/api/auth/password-reset/request", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: $("#recovery-email").value.trim() }) });
        statusFor(status, body.message || "If the account is eligible, recovery instructions have been sent.", response.ok ? "progress" : "");
        if (response.ok) $("#recovery-code")?.focus();
      } catch (_) { statusFor(status, "Recovery is temporarily unavailable. Try again shortly."); }
      busy(button, false, "Send recovery code");
    });
    $("[data-recovery-confirm]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget; busy(button, true);
      try {
        const { response } = await request("/api/auth/password-reset/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: $("#recovery-code").value.trim(), password: $("#recovery-password").value }) });
        statusFor(status, response.ok ? "Password updated. Sign in again." : "Recovery failed. Check the code and password policy.", response.ok ? "success" : "");
      } catch (_) { statusFor(status, "Recovery is temporarily unavailable. Try again shortly."); }
      busy(button, false, "Set new password");
    });
  }

  enablePasswordToggles();
  showSignedOut();
  initLogin();
  initSignup();
  initRecovery();
})();
