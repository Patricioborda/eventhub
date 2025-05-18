document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggleView");
  const table = document.querySelector(".table-wrapper-fav");
  const cards = document.getElementById("cardView");

  if (!toggleBtn || !table || !cards) return;

  // Cargar vista previa del localStorage
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

  // Confirmar y eliminar con animación
  document.querySelectorAll(".btn-remove-card").forEach(btn => {
    btn.addEventListener("click", () => {
      const item = btn.closest("tr") || btn.closest(".col");
      if (!item) return;

      Swal.fire({
        title: "¿Eliminar de favoritos?",
        text: "Esta acción es solo visual por ahora.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, eliminar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#d33"
      }).then(result => {
        if (result.isConfirmed) {
          item.classList.add("fade-out-remove");
          setTimeout(() => item.remove(), 400);
          showToast("Eliminado de favoritos 💔", "info");
        }
      });
    });
  });

  // Toast personalizado
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
});