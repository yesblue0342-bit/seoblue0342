(() => {
  "use strict";
  const storageKey = "seoblue-theme";

  function currentTheme() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  }

  function syncControls(theme) {
    document.querySelectorAll("[data-theme-toggle]").forEach(button => {
      const dark = theme === "dark";
      button.textContent = dark ? "Light mode" : "Dark mode";
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", dark ? "라이트 모드로 전환" : "다크 모드로 전환");
    });
  }

  function syncFrames(theme) {
    document.querySelectorAll("iframe").forEach(frame => {
      try {
        if (frame.contentDocument) frame.contentDocument.documentElement.dataset.theme = theme;
      } catch (_) {}
    });
  }

  function applyTheme(theme, persist = false) {
    const selected = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = selected;
    if (persist) {
      try { localStorage.setItem(storageKey, selected); } catch (_) {}
    }
    syncControls(selected);
    syncFrames(selected);
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(button => {
    button.addEventListener("click", () => applyTheme(currentTheme() === "dark" ? "light" : "dark", true));
  });
  document.querySelectorAll("iframe").forEach(frame => {
    frame.addEventListener("load", () => syncFrames(currentTheme()));
  });
  window.addEventListener("storage", event => {
    if (event.key === storageKey) applyTheme(event.newValue);
  });
  applyTheme(currentTheme());
})();
