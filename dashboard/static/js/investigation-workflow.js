(() => {
  "use strict";

  const normalize = (value) => String(value || "").trim().toLowerCase();

  function bindFilters() {
    document.querySelectorAll("[data-filter-target]").forEach((input) => {
      const target = input.dataset.filterTarget;
      const items = Array.from(document.querySelectorAll(`[data-filter-item="${target}"]`));
      input.addEventListener("input", () => {
        const query = normalize(input.value);
        items.forEach((item) => {
          const matches = !query || normalize(item.dataset.filterText).includes(query);
          item.hidden = !matches;
        });
      });
    });
  }

  function bindReferenceNavigation() {
    document.querySelectorAll("a[href^='#evidence-']").forEach((link) => {
      link.addEventListener("click", () => {
        const target = document.querySelector(link.getAttribute("href"));
        if (target) {
          target.querySelector("details")?.setAttribute("open", "");
        }
      });
    });
  }

  function bindDisclosureState() {
    document.querySelectorAll("details").forEach((disclosure) => {
      disclosure.addEventListener("toggle", () => {
        const summary = disclosure.querySelector("summary");
        if (summary) summary.setAttribute("aria-expanded", String(disclosure.open));
      });
      const summary = disclosure.querySelector("summary");
      if (summary) summary.setAttribute("aria-expanded", String(disclosure.open));
    });
  }

  function bindKeyboardNavigation() {
    document.addEventListener("keydown", (event) => {
      if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
      const active = document.activeElement;
      if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) return;
      const filter = document.querySelector(".command-filter");
      if (!filter) return;
      event.preventDefault();
      filter.focus();
    });
  }

  function boot() {
    bindFilters();
    bindReferenceNavigation();
    bindDisclosureState();
    bindKeyboardNavigation();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
