// Bouton « Agrandir » : la figure occupe tout l'écran ; Plotly se redimensionne sur l'événement resize.
// Échap ou un second clic la remet en place.
(function () {
  function basculer(bouton) {
    var figure = bouton.closest(".figure");
    var actif = figure.classList.toggle("plein-ecran");
    bouton.textContent = actif ? "Réduire" : "Agrandir";
    document.body.classList.toggle("sans-defilement", actif);
    setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 30);
  }

  document.addEventListener("click", function (e) {
    var bouton = e.target.closest(".bouton-agrandir");
    if (bouton) basculer(bouton);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var figure = document.querySelector(".figure.plein-ecran");
    if (figure) basculer(figure.querySelector(".bouton-agrandir"));
  });
})();
