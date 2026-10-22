/* Wendekarten der Ensembleseite: Antippen dreht die Karte.
 *
 * Maus und Tastatur erledigt das Stylesheet (:hover, :focus-visible).
 * Dieses Skript ist nur fuer Touchgeraete da, die kein Hover kennen.
 * Auf Geraeten mit Maus tut es nichts: Ein Klick wuerde die Karte sonst
 * gedreht festhalten, und sie drehte sich beim Wegfahren nicht zurueck.
 *
 * - Ein Tipp dreht um, der naechste zurueck.
 * - Ein Tipp auf einen Link der Rueckseite (Marta) oeffnet den Link und
 *   dreht nicht.
 * - Eine gedrehte Karte dreht sich zurueck, sobald eine andere angetippt
 *   wird. Sonst stehen nach einer Weile alle auf der Rueckseite.
 */
(function () {
  "use strict";

  var karten = Array.prototype.slice.call(document.querySelectorAll(".karte"));
  if (!karten.length) return;

  var maus = window.matchMedia && window.matchMedia("(hover: hover)");

  karten.forEach(function (karte) {
    karte.addEventListener("click", function (e) {
      if (maus && maus.matches) return;
      if (e.target.closest("a")) return;
      var gedreht = !karte.classList.contains("karte--gedreht");
      karten.forEach(function (k) { k.classList.remove("karte--gedreht"); });
      if (gedreht) karte.classList.add("karte--gedreht");
    });
  });
})();
