function getCsrfToken() {
  const cookie = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='));
  return cookie ? cookie.split('=')[1] : '';
}


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("eventForm");

    // Validación de formulario de evento
    if (form) {
        const titleField = form.querySelector("[name='title']");
        const dateField = form.querySelector("[name='date']");
        const submitButton = form.querySelector("[type='submit']");

        const validateForm = () => {
            const title = titleField.value.trim();
            const date = dateField.value;

            let isValid = true;

            if (!title) {
                showError(titleField, "Por favor ingrese un título.");
                isValid = false;
            } else {
                clearError(titleField);
            }

            if (!date) {
                showError(dateField, "Por favor ingrese una fecha.");
                isValid = false;
            } else {
                clearError(dateField);
            }

            submitButton.disabled = !isValid;
            return isValid;
        };

        const showError = (field, message) => {
            let error = field.nextElementSibling;
            if (!error || !error.classList.contains("error-message")) {
                error = document.createElement("div");
                error.classList.add("error-message");
                field.parentNode.appendChild(error);
            }
            error.textContent = message;
            field.classList.add("is-invalid");

            // Mostrar SweetAlert cuando hay error
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: message,
            });
        };

        const clearError = (field) => {
            let error = field.nextElementSibling;
            if (error && error.classList.contains("error-message")) {
                error.remove();
            }
            field.classList.remove("is-invalid");
        };

        form.addEventListener("submit", (e) => {
            if (!validateForm()) {
                e.preventDefault();
            }
        });

        titleField.addEventListener("input", validateForm);
        dateField.addEventListener("input", validateForm);

        validateForm();
    }

    

    // Mostrar alerta de éxito tras enviar el formulario de calificación
    const ratingForms = document.querySelectorAll("#rating-form");
    ratingForms.forEach(form => {
        form.addEventListener("submit", (event) => {
            // Verifica si el usuario es su primera calificación
            const isFirstRating = form.dataset.firstRating === "true";

            // Si es la primera calificación, mostrar la alerta
            if (isFirstRating) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Gracias por tu calificación!',
                    showConfirmButton: false, // No se muestra el botón de confirmación
                    timer: 1000 // La alerta se cerrará automáticamente después de 3 segundos
                }).then(() => {
                    // Después de que la alerta se cierre, enviar el formulario
                    form.submit();
                });
            } else {
                // Si no es la primera calificación, simplemente envía el formulario sin alerta
                form.submit();
            }

            // Prevenir el envío del formulario hasta que se cierre la alerta
            event.preventDefault();
        });
    });

    // Confirmación con SweetAlert al eliminar calificación
    const deleteButtons = document.querySelectorAll(".delete-rating-btn");

    deleteButtons.forEach(button => {
        button.addEventListener("click", (e) => {
            e.preventDefault();
            const url = button.dataset.url;

            Swal.fire({
                title: '¿Estás seguro?',
                text: "Esta acción eliminará la calificación.",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Redirige a la URL de eliminación
                    window.location.href = url;
                }
            });
        });
    });
});




document.addEventListener('click', e => {
    if (e.target.closest('.delete-rating-btn')) {
      e.preventDefault();
      const btn = e.target.closest('.delete-rating-btn');
      Swal.fire({
        title: '¿Eliminar calificación?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, borrar',
      }).then(result => {
        if (result.isConfirmed) {
          fetch(btn.dataset.url, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() } })
            .then(() => location.reload());
        }
      });
    }
  });

/* ⭐ STAR RATING COMPONENT – una sola implementación global */
document.querySelectorAll('.star-rating').forEach(wrapper => {
  const radios  = wrapper.querySelectorAll('input[type="radio"]');
  const labels  = wrapper.querySelectorAll('label.star');
  let current   = +wrapper.dataset.ratingCurrent || 0;

  const paint = val => {
    labels.forEach((lab, idx) => {
      const icon = lab.firstElementChild;
      const on   = idx < val;
      icon.classList.toggle('bi-star-fill', on);
      icon.classList.toggle('bi-star',      !on);
      icon.classList.toggle('text-gold',    on);
    });
  };

  paint(current);

  labels.forEach((lab, idx) => {
    const val = idx + 1;

    lab.addEventListener('mouseenter', () => paint(val));
    lab.addEventListener('mouseleave', () => paint(current));
    lab.addEventListener('click', () => {
      current = val;
      wrapper.dataset.ratingCurrent = val;
      radios[idx].checked = true;
      paint(current);
    });
  });
});

/* ───────── SweetAlert2 para eliminar calificación ───────── */
document.querySelectorAll('.rating-delete-form').forEach(form => {
    form.addEventListener('submit', e => {
      e.preventDefault();                                // cancela envío
      Swal.fire({
        title: '¿Eliminar calificación?',
        text: 'Esta acción no se puede deshacer',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, borrar',
        cancelButtonText: 'Cancelar'
      }).then(result => {
        if (result.isConfirmed) {
          form.submit();                                 // ahora sí POST
        }
      });
    });
  });

  /* ───────── SweetAlert2: eliminar COMENTARIO ───────── */
document.querySelectorAll('.comment-delete-form').forEach(form => {
    form.addEventListener('submit', e => {
      e.preventDefault();
      Swal.fire({
        title: '¿Eliminar comentario?',
        text: 'Esta acción no se puede deshacer',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, borrar',
        cancelButtonText: 'Cancelar'
      }).then(r => { if (r.isConfirmed) form.submit(); });
    });
  });


  document.addEventListener("DOMContentLoaded", function () {
  const favButtons = document.querySelectorAll(".btn-fav-toggle");

  favButtons.forEach(btn => {
    btn.addEventListener("click", async function () {
      const icon = this.querySelector("i");
      const eventId = this.dataset.eventId;

      if (!eventId || !icon) return;

      // Prevención de doble clic rápido
      btn.disabled = true;

      try {
        const res = await fetch(`/favorites/toggle/${eventId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
          }
        });
        const data = await res.json();

        const isFav = data.favorito;

        icon.classList.remove("bi-star", "bi-star-fill", "text-warning", "fav-glow");
        icon.classList.add(isFav ? "bi-star-fill" : "bi-star");
        if (isFav) {
          icon.classList.add("text-warning", "fav-glow");
          showToast("Agregado a favoritos ✨", "success");
        } else {
          showToast("Eliminado de favoritos 💔", "info");
        }
      } catch (error) {
        console.error("Error al marcar favorito", error);
        showToast("Ocurrió un error", "error");
      } finally {
        btn.disabled = false;
      }
    });
  });

  // Toast personalizado sin librerías externas
  function showToast(msg, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast-msg toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 10); // animación de entrada
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300); // limpieza tras salida
    }, 2200);
  }
});