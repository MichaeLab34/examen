// Amélioration progressive uniquement.
//
// Le portail est entièrement fonctionnel sans JavaScript : filtres, pagination,
// capacité et simulation de seuil passent par des formulaires GET et des liens.
// Ce fichier se contente de resoumettre le formulaire quand un critère change,
// pour éviter un clic. Aucune donnée n'est traitée ni stockée côté client, et
// aucune ressource distante n'est chargée (CSP `default-src 'self'`).

(function () {
  "use strict";

  var forms = document.querySelectorAll("form.filters");

  Array.prototype.forEach.call(forms, function (form) {
    if (form.method && form.method.toLowerCase() !== "get") {
      return;
    }
    var controls = form.querySelectorAll("select, input[type=checkbox]");
    Array.prototype.forEach.call(controls, function (control) {
      control.addEventListener("change", function () {
        form.submit();
      });
    });
  });
})();
