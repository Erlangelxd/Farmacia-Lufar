(() => {
  "use strict";

  const body = document.body;
  const toggles = document.querySelectorAll("[data-sidebar-toggle]");
  const overlay = document.querySelector("[data-sidebar-overlay]");
  const mobileQuery = window.matchMedia("(max-width: 900px)");
  const desktopQuery = window.matchMedia("(min-width: 901px)");

  const setSidebarOpen = (isOpen) => {
    body.classList.toggle("nav-open", isOpen);
    toggles.forEach((toggle) => {
      toggle.setAttribute("aria-expanded", String(isOpen));
    });
  };

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      setSidebarOpen(!body.classList.contains("nav-open"));
    });
  });

  overlay?.addEventListener("click", () => setSidebarOpen(false));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && body.classList.contains("nav-open")) {
      setSidebarOpen(false);
    }
  });

  desktopQuery.addEventListener("change", (event) => {
    if (event.matches) {
      setSidebarOpen(false);
    }
  });

  document.querySelectorAll(".sidebar a").forEach((link) => {
    link.addEventListener("click", () => {
      if (mobileQuery.matches) {
        setSidebarOpen(false);
      }
    });
  });

  document.querySelectorAll("[data-dismiss]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("[data-dismissible]")?.remove();
    });
  });

  window.setTimeout(() => {
    document
      .querySelectorAll(
        ".alert--success[data-dismissible], .alert--info[data-dismissible]"
      )
      .forEach((alert) => {
        alert.classList.add("is-hidden");
        window.setTimeout(() => alert.remove(), 220);
      });
  }, 6000);
})();
