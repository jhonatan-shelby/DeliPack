/* DeliPack — mejoras progresivas. Todo funciona sin JavaScript; esto lo hace más ágil. (≈ 6 KB) */
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } }
  function leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  // ---------- aviso flotante ----------
  var temporizador;
  function aviso(texto) {
    var t = $(".toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "toast"; t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite");
      document.body.appendChild(t);
    }
    t.textContent = texto;
    requestAnimationFrame(function () { t.classList.add("visible"); });
    clearTimeout(temporizador);
    temporizador = setTimeout(function () { t.classList.remove("visible"); }, 2800);
  }

  // ---------- menú en celular ----------
  var botonMenu = $(".menu-boton"), menu = $(".menu");
  if (botonMenu && menu) {
    botonMenu.addEventListener("click", function () {
      var abierto = menu.classList.toggle("abierto");
      botonMenu.setAttribute("aria-expanded", String(abierto));
    });
  }

  // ---------- filtros: se aplican solos al marcar ----------
  var formFiltros = $("#filtros-form");
  if (formFiltros) {
    formFiltros.addEventListener("change", function (e) {
      if (e.target.name === "q") return;
      formFiltros.requestSubmit ? formFiltros.requestSubmit() : formFiltros.submit();
    });
  }

  // ---------- cantidad + / − ----------
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-paso]");
    if (!b) return;
    var input = b.parentNode.querySelector("input");
    var v = (parseInt(input.value, 10) || 1) + parseInt(b.dataset.paso, 10);
    var max = parseInt(input.max, 10) || 30;
    input.value = Math.max(1, Math.min(max, v));
  });

  // ---------- guardar en el carrito sin recargar ----------
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches("[data-carrito]")) return;
    e.preventDefault();
    var boton = form.querySelector("button[type=submit]");
    if (boton) boton.disabled = true;
    fetch(form.action, {
      method: "POST", body: new FormData(form), credentials: "same-origin",
      headers: { "Accept": "application/json", "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value }
    }).then(function (r) { return r.json(); }).then(function (d) {
      aviso(d.mensaje);
      $$(".burbuja").forEach(function (el) { el.textContent = d.cantidad; el.hidden = d.cantidad === 0; });
    }).catch(function () { form.submit(); })
      .finally(function () { if (boton) boton.disabled = false; });
  });

  // ---------- ventanas (detalle de producto y promoción) ----------
  function prepararDialogo(d) {
    d.addEventListener("click", function (e) {
      if (e.target === d || e.target.closest(".cerrar")) d.close();
    });
  }

  var detalle = $("#ventana-detalle");
  if (detalle) {
    prepararDialogo(detalle);
    var contenido = $(".ventana__contenido", detalle);
    var cache = {};
    document.addEventListener("click", function (e) {
      var enlace = e.target.closest("a[data-detalle]");
      if (!enlace || e.ctrlKey || e.metaKey || e.shiftKey) return;
      e.preventDefault();
      var url = enlace.getAttribute("href");
      var mostrar = function (html) { contenido.innerHTML = html; if (!detalle.open) detalle.showModal(); };
      if (cache[url]) return mostrar(cache[url]);
      fetch(url + "?parcial=1", { credentials: "same-origin" })
        .then(function (r) { if (!r.ok) throw r; return r.text(); })
        .then(function (html) { cache[url] = html; mostrar(html); })
        .catch(function () { window.location.href = url; });
    });
  }

  var promo = $("#ventana-promo");
  if (promo) {
    prepararDialogo(promo);
    var modo = promo.dataset.modo;
    if (modo === "bienvenida") {
      promo.showModal();
    } else if (modo === "invitacion" && !leer("delipack_promo_vista")) {
      setTimeout(function () {
        if (document.querySelector("dialog[open]")) return;
        guardar("delipack_promo_vista", "1");
        promo.showModal();
      }, 8000);
    }
  }

  // ---------- contraseña fuerte: lista de requisitos en vivo ----------
  var clave = $("input[data-fuerza]");
  var lista = $("#requisitos");
  if (clave && lista) {
    var reglas = {
      largo: function (v) { return v.length >= 10; },
      mayus: function (v) { return /[A-ZÁÉÍÓÚÑ]/.test(v); },
      minus: function (v) { return /[a-záéíóúñ]/.test(v); },
      numero: function (v) { return /\d/.test(v); },
      simbolo: function (v) { return /[^\w\s]|_/.test(v); }
    };
    clave.addEventListener("input", function () {
      $$("li", lista).forEach(function (li) { li.classList.toggle("ok", reglas[li.dataset.regla](clave.value)); });
    });
  }

  // ---------- pago: mostrar solo los campos que aplican ----------
  var formPago = $("#form-pago");
  if (formPago) {
    var ajustar = function () {
      var entrega = formPago.querySelector("[name=tipo_entrega]:checked");
      var pago = formPago.querySelector("[name=metodo_pago]:checked");
      var retiro = entrega && entrega.value === "RETIRO";
      $$("[data-si-entrega]", formPago).forEach(function (el) { el.hidden = retiro; });
      $$("[data-si-transferencia]", formPago).forEach(function (el) {
        el.hidden = !(pago && pago.value === "TRANSFERENCIA");
      });
    };
    formPago.addEventListener("change", ajustar);
    ajustar();
    formPago.addEventListener("submit", function () {
      var b = formPago.querySelector("button[type=submit]");
      setTimeout(function () { b.disabled = true; b.textContent = "Enviando pedido…"; }, 0);
    });
  }

  // ---------- carrito: actualizar cantidad al cambiarla ----------
  $$("form[data-auto]").forEach(function (f) {
    f.addEventListener("change", function () { f.submit(); });
  });
})();
