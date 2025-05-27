/*───────────────────────────────────────────────────────────────*/
/* Ticket purchase helpers – capacidad, pago, alertas & toasts   */
/*───────────────────────────────────────────────────────────────*/

function adjustQuantity(amount) {
  const input = document.getElementById("id_quantity");
  const max = parseInt(input.getAttribute("data-max")) || 4;  // Por defecto, 4
  let value = parseInt(input.value || 0);
  if (isNaN(value)) value = 0;
  value = Math.max(1, Math.min(value + amount, max));
  input.value = value;
  actualizarResumen();
}

/*----------------------------------------------------------------
  Re-calcula totales + alerta “quedan pocas entradas”
----------------------------------------------------------------*/
function actualizarResumen() {
  const cantidad = parseInt(document.getElementById("id_quantity").value) || 1;
  const tipo     = document.getElementById("id_type").value;
  const precioUnitario = tipo === "VIP" ? 100 : 50;
  const subtotal = precioUnitario * cantidad;
  const impuestos = subtotal * 0.10;
  const total     = subtotal + impuestos;

  document.getElementById("precio_unitario").innerText = precioUnitario;
  document.getElementById("resumen_cantidad").innerText = cantidad;
  document.getElementById("subtotal").innerText         = subtotal.toFixed(2);
  document.getElementById("impuestos").innerText        = impuestos.toFixed(2);
  document.getElementById("total").innerText            = total.toFixed(2);

  const restante = parseInt(document.getElementById("remaining_capacity")?.value || "0");
  const alerta   = document.getElementById("alerta_entradas");

  if (alerta) {
    const disponible = restante - cantidad;
    if (disponible <= 5 && disponible > 0) {
      alerta.classList.remove("d-none");
      alerta.innerHTML =
        `⚠ <strong>¡Apurate!</strong> Solo quedan ${disponible} ` +
        `entrada${disponible === 1 ? "" : "s"} disponibles.`;
    } else {
      alerta.classList.add("d-none");
      alerta.innerHTML = "";
    }
  }
}

/*----------------------------------------------------------------
  Validaciones antes de enviar el formulario de pago
----------------------------------------------------------------*/
function validarPago() {
  const cantidad = parseInt(document.getElementById("id_quantity").value);
  const cupo     = parseInt(document.getElementById("remaining_capacity").value);

  if (cantidad > cupo) {
    toast(`Cupo insuficiente: solo quedan ${cupo} entradas.`, "warning");
    return false;
  }

  const campos = ["card_number", "card_expiry", "card_cvv", "card_name"];
  for (const id of campos) {
    const c = document.getElementById(id);
    if (!c || !c.value.trim()) {
      toast("Por favor completa todos los datos de pago.", "error");
      c?.focus();
      return false;
    }
  }

  if (document.getElementById("card_number").value.replace(/\s/g, "").length !== 16) {
    toast("El número de tarjeta debe tener 16 dígitos.", "error");
    return false;
  }

  const expiry = document.getElementById("card_expiry").value;
  if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry)) {
    toast("La fecha de expiración debe tener formato MM/AA.", "error");
    return false;
  }

  const cvv = document.getElementById("card_cvv").value;
  if (!/^\d{3}$/.test(cvv)) {
    toast("El CVV debe tener 3 dígitos.", "error");
    return false;
  }

  if (!document.getElementById("accept_terms").checked) {
    toast("Debes aceptar los términos y condiciones.", "error");
    return false;
  }

  return true;
}

/*----------------------------------------------------------------
  Utilidades de formato (tarjeta/fecha/cvv/nombre)
----------------------------------------------------------------*/
function formatearNumerosTarjeta(input) {
  input.addEventListener("input", () => {
    let nums = input.value.replace(/\D/g, "").substring(0, 16);
    nums = nums.replace(/(.{4})/g, "$1 ").trim();
    input.value = nums;
  });
}

function formatearFechaExp(input) {
  input.addEventListener("input", () => {
    let v = input.value.replace(/\D/g, "").substring(0, 4);
    if (v.length >= 3) v = v.replace(/^(\d{2})(\d{1,2})/, "$1/$2");
    input.value = v;
  });
}

function validarCVV(input) {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "").substring(0, 3);
  });
}

function validarNombre(input) {
  input.addEventListener("input", () => {
    let nombre = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, "");
    input.value = nombre;
  });
}

/*----------------------------------------------------------------
  Toast helper usando SweetAlert2
----------------------------------------------------------------*/
function toast(texto, tipo = "info") {
  Swal.fire({
    toast: true,
    position: "top-end",
    showConfirmButton: false,
    timer: 2500,
    icon: tipo,
    title: texto,
    customClass: {
      popup: "swal2-toast"
    }
  });
}

/*----------------------------------------------------------------
  Setup al cargar página
----------------------------------------------------------------*/
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("id_quantity")?.addEventListener("input", actualizarResumen);
  document.getElementById("id_type")?.addEventListener("change", actualizarResumen);
  document.getElementById("id_quantity")?.addEventListener("blur", () => adjustQuantity(0));

  actualizarResumen();

  const quantityInput = document.getElementById("id_quantity");
  if (quantityInput) {
    quantityInput.setAttribute("readonly", "true");

    quantityInput.addEventListener("keydown", (e) => e.preventDefault());
    quantityInput.addEventListener("paste", (e) => e.preventDefault());
  }

  const form = document.querySelector("form");
  form?.addEventListener("submit", (e) => {
    if (!validarPago()) e.preventDefault();
  });

  formatearNumerosTarjeta(document.getElementById("card_number"));
  formatearFechaExp(document.getElementById("card_expiry"));
  validarCVV(document.getElementById("card_cvv"));
  validarNombre(document.getElementById("card_name"));
});
