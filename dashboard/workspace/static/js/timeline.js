/** Render existing timeline events; intelligence remains backend-owned. */
export function renderTimeline(events, target) {
  const element = typeof target === "string" ? document.querySelector(target) : target;
  if (!element) return;
  element.replaceChildren(...(events || []).map((event) => {
    const item = document.createElement("li");
    item.textContent = `${event.timestamp || ""} — ${event.description || event.event_type || "Event"}`;
    return item;
  }));
}
