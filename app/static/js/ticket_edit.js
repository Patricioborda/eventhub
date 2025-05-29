/*───────────────────────────────────────────────────────────────*/
/* Ticket_edit.js  –  Edición de tickets por el organizador      */
/*───────────────────────────────────────────────────────────────*/

(function () {
  /*
   *  Variables de referencia
   *  ------------------------------------------------------------------
   */
  const qtyInput  = document.getElementById('id_quantity');
  const maxEntradas = parseInt(qtyInput?.dataset.max || '4');   // viene del context
  const tipoInput = document.getElementById('id_type');         // select
 
  if (!qtyInput) return;  // Si por algún motivo no existe, no hacemos nada
  normalizarCantidad();
  /*
   *  1. Limitar y mostrar cuántas entradas quedan mientras escribe
   *  ----------------------------------------------------------------
   */
  function normalizarCantidad() {
    let v = parseInt(qtyInput.value || '0');
    if (isNaN(v) || v < 1) v = 1;

    if (v > maxEntradas) {
        v = maxEntradas;

        // Feedback opcional: flash visual del input si se forzó el máximo
        qtyInput.classList.add("is-invalid");
        setTimeout(() => qtyInput.classList.remove("is-invalid"), 600);
    }

    qtyInput.value = v;
  }

  qtyInput.addEventListener('input',  normalizarCantidad);
  qtyInput.addEventListener('blur',   normalizarCantidad);

  /*
   *  2. Evitar envío si la cantidad quedó fuera de rango (doble seguridad)
   *  ---------------------------------------------------------------------
   */
  const form = qtyInput.closest('form');
  form?.addEventListener('submit', (e) => {
    normalizarCantidad();   // corrige antes de validar
    const cantidad = parseInt(qtyInput.value);
    if (cantidad > maxEntradas) {
      e.preventDefault();
      Swal.fire({
        icon: 'warning',
        title: 'Cantidad inválida',
        text: `Solo quedan ${maxEntradas} entradas disponibles para este usuario.`,
        confirmButtonText: 'Entendido'
      });
    }
  });

  /*
   *  3. UI: actualiza automáticamente la etiqueta “Disponibles”
   *      por si en el futuro quisieras hacerlo dinámico.
   *  -----------------------------------------------------------
   */
  const lblDisponibles = document.querySelector(
      '.form-text.text-muted');   // el <small> que pintamos en el template
  if (lblDisponibles) {
    lblDisponibles.innerText = `Disponibles: ${maxEntradas}`;
  }

  /*
   *  4. (Sintáctico) – si querés manejar algo extra cuando cambie el tipo,
   *      dejá este stub.
   */
  tipoInput?.addEventListener('change', () => {
    /* Ejemplo: podrías mostrar precio unitario distinto */
  });
})();
