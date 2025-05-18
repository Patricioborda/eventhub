// Tabla ↔ tarjetas y eliminación de “Mis Favoritos”
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('toggleView');
  const tblWrap   = document.querySelector('.table-wrapper-fav');
  const cardWrap  = document.getElementById('cardView');
  if (!toggleBtn || !tblWrap || !cardWrap) return;

  // 1️⃣ Restaurar vista guardada
  if (localStorage.getItem('favoritos_view') === 'cards') {
    tblWrap.classList.add('d-none');
    cardWrap.classList.remove('d-none');
    toggleBtn.textContent = 'Ver como tabla';
  }

  // 2️⃣ Cambiar entre tabla y tarjetas
  toggleBtn.addEventListener('click', () => {
    const showCards = tblWrap.classList.toggle('d-none');
    cardWrap.classList.toggle('d-none');
    toggleBtn.textContent = showCards
      ? 'Ver como tabla'
      : 'Ver como tarjetas';
    localStorage.setItem('favoritos_view', showCards ? 'cards' : 'table');
  });

  // 3️⃣ Delegación: quitar favorito solo en la vista de favoritos
  document.addEventListener('click', async ev => {
    const btn = ev.target.closest('.btn-fav-remove');
    if (!btn) return;              // solo nuestros botones de eliminar
    ev.preventDefault();

    const id = btn.dataset.eventId;
    if (!id) return;

    // confirmación con SweetAlert2
    const { isConfirmed } = await Swal.fire({
      title: '¿Eliminar de favoritos?',
      text:  'Esta acción quitará este evento de tu lista.',
      icon:  'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, quitar',
      cancelButtonText:  'Cancelar',
      confirmButtonColor:'#d33'
    });
    if (!isConfirmed) return;

    // petición al server
    try {
      const res = await fetch(`/favorites/toggle/${id}/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': window.getCsrfToken() }
      });
      if (!res.ok) throw new Error(res.statusText);
      const js = await res.json();

      // si se quitó del server, lo eliminamos del DOM
      if (js.favorito === false) {
        removeDom(id);
        toast('Eliminado de favoritos 💔','info');
      }
    } catch (err) {
      console.error(err);
      toast('Error al eliminar favorito','error');
    }
  });

  // 4️⃣ Helpers
  function removeDom(id) {
    // elimina filas y cards
    document.querySelectorAll(`[data-event-id="${id}"]`)
            .forEach(el => {
      el.classList.add('fade-out-remove');
      setTimeout(() => el.remove(), 300);
    });
    // si quedó vacío, mostramos empty‐state
    setTimeout(() => {
      if (!document.querySelector('[data-event-id]')) showEmpty();
    }, 350);
  }

  function showEmpty() {
    const html = `
      <div class="empty-state text-center p-5">
        <div class="icon mb-3">🌟</div>
        <h4 class="text-dark">Aún no tenés eventos favoritos</h4>
        <p class="text-muted">Marcá eventos con la estrella para tenerlos siempre a mano.</p>
      </div>`;
    tblWrap.remove();
    cardWrap.remove();
    document.querySelector('.containerFavoritos')
            .insertAdjacentHTML('beforeend', html);
  }

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
