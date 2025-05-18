document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggleView");
  const table = document.querySelector(".table-wrapper-fav");
  const cards = document.getElementById("cardView");

  // Recuperar preferencia de vista
  const savedView = localStorage.getItem("favoritos_view");
  if (savedView === "cards") {
    table.classList.add("d-none");
    cards.classList.remove("d-none");
    toggleBtn.textContent = "Ver como tabla";
  }

  toggleBtn.addEventListener("click", () => {
    const isTableHidden = table.classList.toggle("d-none");
    cards.classList.toggle("d-none");

    const newView = isTableHidden ? "cards" : "table";
    toggleBtn.textContent = isTableHidden ? "Ver como tabla" : "Ver como tarjetas";
    localStorage.setItem("favoritos_view", newView);
  });

  // Acción: Toggle favorito
  document.querySelectorAll(".btn-fav-toggle").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const eventId = btn.dataset.eventId;
      const icon = btn.querySelector("i");
      const rowOrCard = btn.closest("tr") || btn.closest(".col");

      if (!eventId || !icon || !rowOrCard) return;

      try {
        const res = await fetch(`/favorites/toggle/${eventId}/`, {
          method: "POST",
          headers: { "X-CSRFToken": getCsrfToken() }
        });

        const data = await res.json();

        if (!data.favorito) {
          // Eliminar visual
          rowOrCard.classList.add("fade-out-remove");
          setTimeout(() => rowOrCard.remove(), 400);
          showToast("Eliminado de favoritos 💔", "info");
        }
      } catch (err) {
        console.error("Error al eliminar favorito:", err);
        showToast("Ocurrió un error", "error");
      }
    });
  });

  function showToast(msg, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast-msg toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 10);
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 2200);
  }

  function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }
});
