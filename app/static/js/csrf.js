// Solo una función global para obtener el CSRF token
window.getCsrfToken = function() {
  const m = document.cookie.match(/(^|; )csrftoken=([^;]+)/);
  return m ? m[2] : '';
};
