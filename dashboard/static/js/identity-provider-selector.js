const icons = { entra: "◆", okta: "O", google: "G" };

export function initIdentityProviderSelectors() {
  document.querySelectorAll("[data-idp-selector]").forEach(async (root) => {
    try {
      const response = await fetch("/auth/enterprise/providers", { credentials: "same-origin" });
      if (!response.ok) return;
      const payload = await response.json();
      const providers = Array.isArray(payload.providers) ? payload.providers : [];
      providers.forEach((provider) => {
        const button = document.createElement("a");
        button.className = "sentinel-idp-button";
        button.href = provider.start_url;
        const icon = document.createElement("span");
        icon.className = "idp-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = icons[provider.id] || "•";
        const name = document.createElement("span");
        name.textContent = provider.name;
        button.append(icon, name);
        root.append(button);
      });
      if (providers.length === 0) root.closest(".auth-enterprise")?.remove();
    } catch (_) {
      root.closest(".auth-enterprise")?.remove();
    }
  });
}
