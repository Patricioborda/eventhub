function adjustQuantity(amount) {
  const input = document.getElementById("id_quantity");
  let value = parseInt(input.value || 0);
  if (isNaN(value)) value = 0;
  value = Math.max(1, value + amount);
  input.value = value;
  actualizarResumen(); 
}

function actualizarResumen() {
  const cantidad = parseInt(document.getElementById("id_quantity").value) || 1;
  const tipo = document.getElementById("id_type").value;
  const precioUnitario = tipo === "VIP" ? 100 : 50;
  const subtotal = precioUnitario * cantidad;
  const impuestos = subtotal * 0.10;
  const total = subtotal + impuestos;

  document.getElementById("precio_unitario").innerText = precioUnitario;
  document.getElementById("resumen_cantidad").innerText = cantidad;
  document.getElementById("subtotal").innerText = subtotal.toFixed(2);
  document.getElementById("impuestos").innerText = impuestos.toFixed(2);
  document.getElementById("total").innerText = total.toFixed(2);
}

function validarPago() {
  const campos = ['card_number', 'card_expiry', 'card_cvv', 'card_name'];
  
  // Validar campos del formulario de pago
  for (const id of campos) {
    const campo = document.getElementById(id);
    if (!campo || !campo.value.trim()) {
      // Usar SweetAlert para mostrar el mensaje
      Swal.fire({
        title: 'Error',
        text: 'Por favor completa todos los campos del método de pago.',
        icon: 'error',
        confirmButtonText: 'Aceptar'
      });
      campo?.focus();
      return false;
    }
  }

  // Verificar aceptación de términos
  const termsAccepted = document.getElementById('accept_terms').checked;
  if (!termsAccepted) {
    Swal.fire({
      title: 'Error',
      text: 'Debes aceptar los términos y condiciones antes de continuar.',
      icon: 'error',
      confirmButtonText: 'Aceptar'
    });
    return false; // Evita que se envíe el formulario
  }

  return true;  // Si todo está bien, se envía el formulario
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("id_quantity").addEventListener("input", actualizarResumen);
  document.getElementById("id_type").addEventListener("change", actualizarResumen);
  actualizarResumen();

  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", (e) => {
      if (!validarPago()) {
        e.preventDefault();  // Evita que el formulario se envíe si hay error
      }
    });
  }

  formatearNumerosTarjeta(document.getElementById("card_number"));
  formatearFechaExp(document.getElementById("card_expiry"));
  validarCVV(document.getElementById("card_cvv"))
});

function formatearNumerosTarjeta (input){
  input.addEventListener("input", () => {
    let numeros = input.value.replace(/\D/g, "").substring(0, 16);
    numeros = numeros.replace(/(.{4})/g, "$1 ").trim();
    input.value = numeros;
  })
}

function formatearFechaExp (input) {
  input.addEventListener("input", () => {

    let fecha = input.value.replace (/\D/g, "").substring (0,4);
    
    if (fecha.length >= 3){
      fecha = fecha.replace(/^(\d{2})(\d{1,2})/, "$1/$2");
    }

    input.value = fecha;
  })
}

function validarCVV (input){
  input.addEventListener("input", () =>{

    let cvv = input.value.replace (/\D/g, "").substring (0,3);
    input.value = cvv;

  })
}