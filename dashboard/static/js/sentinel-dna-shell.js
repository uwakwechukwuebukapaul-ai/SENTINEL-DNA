(function () {
  "use strict";

  function bootShell() {
    var sidebar = document.getElementById("app-sidebar");
    var toggle = document.querySelector("[data-mobile-nav-toggle]");
    var overlay = document.querySelector("[data-nav-overlay]");
    if (!sidebar || !toggle) return;
    var restoreFocus = null;

    function setOpen(open) {
      if (open) restoreFocus = document.activeElement;
      sidebar.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      if (overlay) overlay.hidden = !open;
      if (open) sidebar.querySelector("a")?.focus();
      if (!open && restoreFocus && typeof restoreFocus.focus === "function") {
        restoreFocus.focus();
        restoreFocus = null;
      }
    }

    toggle.addEventListener("click", function () {
      setOpen(!sidebar.classList.contains("is-open"));
    });

    if (overlay) overlay.addEventListener("click", function () { setOpen(false); });
    sidebar.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { setOpen(false); });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && sidebar.classList.contains("is-open")) setOpen(false);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootShell);
  } else {
    bootShell();
  }
})();
