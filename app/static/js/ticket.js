/*───────────────────────────────────────────────────────────────*/
/* ticket.js – SOLO para la pantalla de COMPRA                  */
/*───────────────────────────────────────────────────────────────*/

/* Utilidades globales seguras */
function $(id) { return document.getElementById(id); }

/*───────────────────────────────────────────────────────────────*/
/* 1. Lógica de cantidad, resumen y alertas                     */
/*───────────────────────────────────────────────────────────────*/
function adjustQuantity(delta) {
  const input = $('id_quantity');
  if (!input) return;
  const max = parseInt(input.dataset.max || '4');
  let v = parseInt(input.value || '0');
  if (isNaN(v)) v = 0;
  v = Math.max(1, Math.min(v + delta, max));
  input.value = v;
  actualizarResumen();
}

function actualizarResumen() {
  const qtyEl   = $('id_quantity');
  const typeEl  = $('id_type');
  const priceEl = $('precio_unitario');
  if (!qtyEl || !typeEl || !priceEl) return;

  let cantidad = parseInt(qtyEl.value) || 1;
  const maxPorUsuario = parseInt(qtyEl.dataset.max || '4');
  const capacidadRestante = parseInt($('remaining_capacity')?.value || '0');

  // --- Lo máximo que puede comprar el usuario según capacidad real
  const maxDisponible = Math.min(maxPorUsuario, capacidadRestante);

  // Validar que no se pase del tope
  if (cantidad > maxDisponible) {
    cantidad = maxDisponible;
    qtyEl.value = cantidad;
    qtyEl.classList.add("is-invalid");
    setTimeout(() => qtyEl.classList.remove("is-invalid"), 600);
  }

  // --- Calcular totales
  const unit = typeEl.value === 'VIP' ? 100 : 50;
  const subtotal = unit * cantidad;
  const impuestos = subtotal * 0.10;
  const total = subtotal + impuestos;

  priceEl.innerText = unit;
  $('resumen_cantidad').innerText = cantidad;
  $('subtotal').innerText = subtotal.toFixed(2);
  $('impuestos').innerText = impuestos.toFixed(2);
  $('total').innerText = total.toFixed(2);

  // --- Cartel gris: ¿cuánto más puede comprar?
  const cartelMax = $('cartel_maximo_comprable');
  if (cartelMax) {
    const restanteUsuario = maxDisponible - cantidad;
    if (maxDisponible === 0) {
      cartelMax.innerText = "Ya no podés comprar más entradas";
    } else if (restanteUsuario > 0) {
      cartelMax.innerText = `Podés comprar ${restanteUsuario} entrada${restanteUsuario === 1 ? '' : 's'} más`;
    } else {
      cartelMax.innerText = `Ya alcanzaste el máximo permitido (${maxDisponible})`;
    }
  }

  // --- Cartel amarillo o rojo: entradas disponibles reales
  const alerta = $('alerta_entradas');
  if (alerta) {
    alerta.classList.remove('alert-warning', 'alert-danger', 'd-none');
    alerta.innerHTML = '';

    if (capacidadRestante <= 0) {
      alerta.classList.add('alert-danger');
      alerta.innerHTML = '❌ No hay más entradas disponibles para este evento.';
    } else if (capacidadRestante <= 5) {
      alerta.classList.add('alert-warning');
      alerta.innerHTML = capacidadRestante === 1
        ? '⚠ <strong>¡Apurate!</strong> Solo queda 1 entrada disponible.'
        : `⚠ <strong>¡Apurate!</strong> Solo quedan ${capacidadRestante} entradas disponibles.`;
    } else {
      alerta.classList.add('d-none'); // no mostrar si hay muchas
    }
  }

  // --- Actualizar etiqueta del resumen (opcional)
  const lbl = $('remaining_label');
  const plr = $('plural_label');
  if (lbl) {
    lbl.innerText = capacidadRestante;
    if (plr) {
      plr.innerText = capacidadRestante === 1 ? '' : 's';
    }
  }
}

/*───────────────────────────────────────────────────────────────*/
/* 2. Validación de pago & helpers                             */
/*───────────────────────────────────────────────────────────────*/
function validarPago() {
  const qtyEl = $('id_quantity');
  const remEl = $('remaining_capacity');
  if (!qtyEl || !remEl) return true;

  // SALTAR validación de pago si no hay entradas disponibles
  const max = parseInt(qtyEl.dataset.max || '0');
  if (max === 0) {
    return true;  // dejamos pasar para que Django maneje el error
  }

  // === Validaciones normales de forma ===
  const cantidad = parseInt(qtyEl.value);
  const cupo = parseInt(remEl.value);
  if (cantidad > cupo) {
    toast(`Cupo insuficiente: solo quedan ${cupo} entradas.`, 'warning');
    return false;
  }

  const campos = ['card_number', 'card_expiry', 'card_cvv', 'card_name'];
  for (const id of campos) {
    const c = $(id);
    if (c && !c.value.trim()) {
      toast('Por favor completa todos los datos de pago.', 'error');
      c.focus();
      return false;
    }
  }
  if ($('card_number').value.replace(/\s/g, '').length !== 16) {
    toast('El número de tarjeta debe tener 16 dígitos.', 'error');
    return false;
  }
  if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test($('card_expiry').value)) {
    toast('La fecha de expiración debe tener formato MM/AA.', 'error');
    return false;
  }
  if (!/^\d{3}$/.test($('card_cvv').value)) {
    toast('El CVV debe tener 3 dígitos.', 'error');
    return false;
  }
  if (!$('accept_terms').checked) {
    toast('Debes aceptar los términos y condiciones.', 'error');
    return false;
  }

  return true;
}

/* Enmascaradores de inputs */
function formatearNumerosTarjeta(i) {
  i?.addEventListener('input', () => {
    let n = i.value.replace(/\D/g, '').substring(0, 16);
    i.value = n.replace(/(.{4})/g, '$1 ').trim();
  });
}
function formatearFechaExp(i) {
  i?.addEventListener('input', () => {
    let v = i.value.replace(/\D/g, '').substring(0, 4);
    if (v.length >= 3) v = v.replace(/^(\d{2})(\d{1,2})/, '$1/$2');
    i.value = v;
  });
}
function validarCVV(i) {
  i?.addEventListener('input', () => {
    i.value = i.value.replace(/\D/g, '').substring(0, 3);
  });
}
function validarNombre(i) {
  i?.addEventListener('input', () => {
    i.value = i.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
  });
}

/*───────────────────────────────────────────────────────────────*/
/* 3. Inicialización                                            */
/*───────────────────────────────────────────────────────────────*/
document.addEventListener('DOMContentLoaded', () => {
  const qty = $('id_quantity');
  const cap = $('remaining_capacity');
  if (qty && cap) {
    const max = parseInt(qty.dataset.max || '0');
    
    // Sólo si quedan entradas, registramos listeners de resumen y bloqueamos edición manual
    qty.addEventListener('input', actualizarResumen);
    $('id_type')?.addEventListener('change', actualizarResumen);
    qty.addEventListener('blur', () => adjustQuantity(0));
    actualizarResumen();

    

    // Listener de envío
    const form = document.querySelector('form');
    form?.addEventListener('submit', e => {
      if (!validarPago()) e.preventDefault();
    });

    // Formateadores
    formatearNumerosTarjeta($('card_number'));
    formatearFechaExp($('card_expiry'));
    validarCVV($('card_cvv'));
    validarNombre($('card_name'));
  }

  // Toast de éxito si viene ?compra=ok
  if (window.location.search.includes('compra=ok')) {
    toast('¡Compra realizada con éxito! 🎉', 'success');
  }
});

/*───────────────────────────────────────────────────────────────*/
/* Toast reutilizable (SweetAlert)                              */
/*───────────────────────────────────────────────────────────────*/
function toast(t, m = 'info') {
  Swal.fire({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 2500,
    icon: m,
    title: t,
    customClass: { popup: 'swal2-toast' }
  });
}
