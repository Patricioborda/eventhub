// Validación de EventForm y toggle de favoritos en el listado general

document.addEventListener('DOMContentLoaded', () => {
  // 1️⃣ Validación del formulario de evento
  const form = document.getElementById('eventForm');
  if (form) {
    const titleF = form.querySelector('[name="title"]');
    const dateF  = form.querySelector('[name="date"]');
    const subBtn = form.querySelector('[type="submit"]');

    const validate = () => {
      let ok = true;
      if (!titleF.value.trim()) {
        showError(titleF, 'Por favor ingrese un título.');
        ok = false;
      } else {
        clearError(titleF);
      }
      if (!dateF.value) {
        showError(dateF, 'Por favor ingrese una fecha.');
        ok = false;
      } else {
        clearError(dateF);
      }
      subBtn.disabled = !ok;
      return ok;
    };

    const showError = (fld, msg) => {
      let err = fld.nextElementSibling;
      if (!err || !err.classList.contains('error-message')) {
        err = document.createElement('div');
        err.className = 'error-message';
        fld.after(err);
      }
      fld.classList.add('is-invalid');
      err.textContent = msg;
      // SweetAlert2
      Swal.fire({ icon: 'error', title: 'Oops...', text: msg });
    };

    const clearError = fld => {
      const nxt = fld.nextElementSibling;
      if (nxt?.classList.contains('error-message')) nxt.remove();
      fld.classList.remove('is-invalid');
    };

    form.addEventListener('submit', e => { if (!validate()) e.preventDefault(); });
    titleF.addEventListener('input', validate);
    dateF .addEventListener('input', validate);
    validate();
  }

  // 2️⃣ Toggle favoritos en el listado de eventos
  document.addEventListener('click', async e => {
    const btn = e.target.closest('.btn-fav-toggle');
    if (!btn) return;
    e.preventDefault();

    const icon = btn.querySelector('i');
    const id   = btn.dataset.eventId;
    if (!id || !icon) return;

    btn.disabled = true;
    try {
      const res = await fetch(`/favorites/toggle/${id}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': window.getCsrfToken() },
        credentials: 'same-origin'
      });
      const js = await res.json();
      const fav = js.favorito;

      // cambio de icono y glow
      icon.classList.remove('bi-star','bi-star-fill','text-warning','fav-glow');
      if (fav) {
        icon.classList.add('bi-star-fill','text-warning','fav-glow');
        toast('Agregado a favoritos ✨','success');
      } else {
        icon.classList.add('bi-star');
        toast('Eliminado de favoritos 💔','info');
      }
    } catch (err) {
      console.error(err);
      toast('Error al actualizar favorito','error');
    } finally {
      btn.disabled = false;
    }
  });

  // 3️⃣ Helper de toast
  function toast(txt, type='info') {
    const t = document.createElement('div');
    t.className = `toast-msg toast-${type}`;
    t.textContent = txt;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => {
      t.classList.remove('show');
      setTimeout(() => t.remove(), 300);
    }, 2000);
  }
});
