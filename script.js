document.getElementById("year").textContent = new Date().getFullYear();

document.querySelectorAll("[data-load-embed]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const box = btn.closest(".case-embed");
    const frame = document.createElement("iframe");
    frame.src = box.dataset.embed;
    frame.title = box.dataset.title;
    frame.allowFullscreen = true;
    box.appendChild(frame);
    box.classList.add("is-loaded");
  });
});
