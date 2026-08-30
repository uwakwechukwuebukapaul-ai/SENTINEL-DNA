(function () {
  "use strict";

  function bootPalette() {
    var backdrop = document.getElementById("command-palette-backdrop");
    var dialog = document.getElementById("command-palette");
    var input = document.getElementById("command-palette-input");
    var list = document.getElementById("command-palette-list");
    var closeButton = document.querySelector("[data-command-close]");
    if (!backdrop || !dialog || !input || !list) return;

    var allCommands = Array.prototype.slice.call(list.querySelectorAll(".palette-command"));
    var openButtons = Array.prototype.slice.call(document.querySelectorAll("[data-command-open]"));
    var activeIndex = 0;
    var restoreFocus = null;

    function visibleCommands() {
      return allCommands.filter(function (command) { return !command.hidden; });
    }

    function highlight(index) {
      var commands = visibleCommands();
      if (!commands.length) return;
      activeIndex = (index + commands.length) % commands.length;
      commands.forEach(function (command, position) {
        var active = position === activeIndex;
        command.classList.toggle("is-highlighted", active);
        command.setAttribute("aria-selected", String(active));
      });
      commands[activeIndex].scrollIntoView({ block: "nearest" });
    }

    function filter() {
      var query = input.value.trim().toLowerCase();
      allCommands.forEach(function (command) {
        var haystack = (command.textContent + " " + (command.dataset.keywords || "")).toLowerCase();
        command.hidden = Boolean(query && haystack.indexOf(query) === -1);
      });
      activeIndex = 0;
      highlight(0);
    }

    function open() {
      restoreFocus = document.activeElement;
      backdrop.hidden = false;
      document.body.style.overflow = "hidden";
      openButtons.forEach(function (button) { button.setAttribute("aria-expanded", "true"); });
      input.value = "";
      filter();
      window.requestAnimationFrame(function () { input.focus(); });
    }

    function close() {
      backdrop.hidden = true;
      document.body.style.overflow = "";
      openButtons.forEach(function (button) { button.setAttribute("aria-expanded", "false"); });
      if (restoreFocus && typeof restoreFocus.focus === "function") restoreFocus.focus();
    }

    document.querySelectorAll("[data-command-open]").forEach(function (button) {
      button.addEventListener("click", open);
    });
    if (closeButton) closeButton.addEventListener("click", close);

    document.addEventListener("keydown", function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (backdrop.hidden) open(); else close();
        return;
      }
      if (backdrop.hidden) return;
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        highlight(activeIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        highlight(activeIndex - 1);
      } else if (event.key === "Enter") {
        var commands = visibleCommands();
        if (commands[activeIndex]) commands[activeIndex].click();
      } else if (event.key === "Tab") {
        var focusable = [input].concat(visibleCommands());
        if (closeButton) focusable.push(closeButton);
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    });

    input.addEventListener("input", filter);
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) close();
    });
    allCommands.forEach(function (command) {
      command.addEventListener("mousemove", function () {
        highlight(visibleCommands().indexOf(command));
      });
    });
    highlight(0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootPalette);
  } else {
    bootPalette();
  }
})();
