(() => {
  const status = document.getElementById("status");
  const content = document.getElementById("content");
  fetch("/api/investigation-decision/analysis")
    .then((response) => response.json())
    .then((data) => {
      status.textContent = "Advisory decision intelligence loaded";
      content.textContent = JSON.stringify(data, null, 2);
    })
    .catch(() => { status.textContent = "Unavailable; human review required."; });
})();
