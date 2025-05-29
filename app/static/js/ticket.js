// Variables globales (solo declaradas una vez)
var descuentoValor = 0;
var descuentoTipo = null;

function adjustQuantity(amount) {
  const input = document.getElementById("id_quantity");
  const max = parseInt(input.getAttribute("data-max")) || 4;  // Por defecto, 4
  let value = parseInt(input.value || 0);

  if (isNaN(value)) value = 0;
  value += amount;
  // Limitar entre 1 y max
  value = Math.max(1, Math.min(value, max));
  input.value = value;
  actualizarResumen();
}

function actualizarResumen() {
  const cantidad = parseInt(document.getElementById("id_quantity").value) || 1;
  const tipo = document.getElementById("id_type").value;
  const precioUnitario = tipo === "VIP" ? 100 : 50;
  const subtotalOriginal = precioUnitario * cantidad;

  // Aplicar descuento si corresponde
  let descuento = 0;
  if (descuentoTipo === 'fixed') {
    descuento = descuentoValor;
  } else if (descuentoTipo === 'percent') {
    descuento = subtotalOriginal * (descuentoValor / 100);
  }

  let subtotalConDescuento = subtotalOriginal - descuento;
  if (subtotalConDescuento < 0) subtotalConDescuento = 0;

  const impuestos = subtotalOriginal * 0.10;
  const total = subtotalConDescuento + impuestos;

  // Logs para depuración
  console.log("Descuento tipo:", descuentoTipo);
  console.log("Descuento valor:", descuentoValor);
  console.log("Subtotal original:", subtotalOriginal);
  console.log("Subtotal con descuento:", subtotalConDescuento);
  console.log("Total con impuestos:", total);

  // Actualizar la UI
  document.getElementById("precio_unitario").innerText = precioUnitario.toFixed(2);
  document.getElementById("resumen_cantidad").innerText = cantidad;
  // Aquí mostramos el subtotal ya con descuento
  document.getElementById("subtotal").innerText = subtotalConDescuento.toFixed(2);
  document.getElementById("impuestos").innerText = impuestos.toFixed(2);
  document.getElementById("total").innerText = total.toFixed(2);
}

function validarPago() {
  const campos = ['card_number', 'card_expiry', 'card_cvv', 'card_name'];
  for (const id of campos) {
    const campo = document.getElementById(id);
    if (!campo || !campo.value.trim()) {
      Swal.fire({ title: 'Error', text: 'Por favor completa todos los campos.', icon: 'error', confirmButtonText: 'Aceptar' });
      campo?.focus();
      return false;
    }
  }
  if (!document.getElementById('accept_terms').checked) {
    Swal.fire({ title: 'Error', text: 'Debes aceptar los términos y condiciones.', icon: 'error', confirmButtonText: 'Aceptar' });
    return false;
  }
  const tarjeta = document.getElementById('card_number').value.replace(/\s/g, '');
  if (tarjeta.length !== 16) {
    Swal.fire({ title: 'Error', text: 'El número de tarjeta debe tener 16 dígitos.', icon: 'error', confirmButtonText: 'Aceptar' });
    return false;
  }
  if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(document.getElementById('card_expiry').value)) {
    Swal.fire({ title: 'Error', text: 'La fecha de expiración debe ser MM/AA.', icon: 'error', confirmButtonText: 'Aceptar' });
    return false;
  }
  if (!/^\d{3}$/.test(document.getElementById('card_cvv').value)) {
    Swal.fire({ title: 'Error', text: 'El CVV debe tener 3 dígitos.', icon: 'error', confirmButtonText: 'Aceptar' });
    return false;
  }
  return true;
}

window.addEventListener("DOMContentLoaded", () => {
  // Bindings iniciales
  document.getElementById("id_quantity").addEventListener("input", actualizarResumen);
  document.getElementById("id_type").addEventListener("change", actualizarResumen);
  actualizarResumen();

  // Hacer quantity readonly
  const quantityInput = document.getElementById("id_quantity");
  if (quantityInput) {
    quantityInput.setAttribute("readonly", "true");
    quantityInput.addEventListener("keydown", e => e.preventDefault());
    quantityInput.addEventListener("paste", e => e.preventDefault());
  }

  // Validación de formulario
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", e => {
      if (!validarPago()) e.preventDefault();
    });
  }

  // Formateos de inputs de tarjeta
  formatearNumerosTarjeta(document.getElementById("card_number"));
  formatearFechaExp(document.getElementById("card_expiry"));
  validarCVV(document.getElementById("card_cvv"));
  validarNombre(document.getElementById("card_name"));

  // Botón de aplicar descuento
  const applyBtn = document.getElementById('apply-discount');
  applyBtn.addEventListener('click', async () => {
    const codigo = document.getElementById('id_discount_code').value.trim();
    const eventId = applyBtn.dataset.eventId;
    const errorDiv = document.getElementById('discount-error');

    if (!codigo) {
      errorDiv.style.display = 'block';
      errorDiv.classList.add('text-danger');
      errorDiv.textContent = 'No se introdujo un cupón';
      return;
    }
    errorDiv.style.display = 'none';

    try {
      const res = await fetch(`/ajax/validar-cupon/?codigo=${encodeURIComponent(codigo)}&event_id=${eventId}`);
      const data = await res.json();

      if (data.status === 'ok') {
        errorDiv.style.display = 'block';
        errorDiv.classList.replace('text-danger','text-success');
        errorDiv.textContent = data.message;
        descuentoValor = data.discount_value;
        descuentoTipo = data.discount_type;   // 'fixed' o 'percent'
      } else {
        errorDiv.style.display = 'block';
        errorDiv.classList.replace('text-success','text-danger');
        errorDiv.textContent = data.message;
        descuentoValor = 0;
        descuentoTipo = null;
      }
      actualizarResumen();
    } catch {
      errorDiv.style.display = 'block';
      errorDiv.classList.replace('text-success','text-danger');
      errorDiv.textContent = 'Error al validar el cupón';
      descuentoValor = 0;
      descuentoTipo = null;
      actualizarResumen();
    }
  });
});

// Funciones auxiliares para formateo
function formatearNumerosTarjeta(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    let v = input.value.replace(/\D/g, "").substring(0,16);
    input.value = v.replace(/(.{4})/g,"$1 ").trim();
  });
}

function formatearFechaExp(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    let v = input.value.replace(/\D/g,"").substring(0,4);
    if (v.length >= 3) v = v.replace(/^(\d{2})(\d{1,2})/,"$1/$2");
    input.value = v;
  });
}

function validarCVV(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g,"").substring(0,3);
  });
}

function validarNombre(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    input.value = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g,"");
  });
}
