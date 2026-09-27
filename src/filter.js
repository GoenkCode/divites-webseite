/* Ortsfilter fuer die Terminliste.
 *
 * Progressive Enhancement, und das ist hier keine Stilfrage:
 * Die vollstaendige Terminliste steht im HTML. Dieses Skript blendet nur aus.
 * Faellt es aus — blockiert, Fehler, altes Geraet — fehlt der Filter, aber
 * alle Termine sind da. Eine Terminliste, die ohne JavaScript leer bleibt,
 * waere ein Totalausfall.
 *
 * Deshalb ist die Filterleiste im HTML mit "hidden" ausgezeichnet und wird
 * erst hier sichtbar gemacht: ohne Skript keine Knoepfe, die nichts tun.
 *
 * Kein Framework, kein CDN, kein Cookie, kein Tracking. Damit bleibt die
 * Datenschutzerklaerung so kurz, wie sie ist.
 */
(function () {
  "use strict";

  var leiste = document.querySelector("[data-filter]");
  var liste = document.querySelector("[data-termine]");
  if (!leiste || !liste) return;

  var knoepfe = Array.prototype.slice.call(
    leiste.querySelectorAll(".filter__knopf"));
  var eintraege = Array.prototype.slice.call(
    liste.querySelectorAll(".termin"));
  if (!knoepfe.length || !eintraege.length) return;

  leiste.hidden = false;

  // Sichtbare Rueckmeldung fuer Screenreader, wenn gefiltert wurde.
  var meldung = document.createElement("p");
  meldung.className = "filter__meldung";
  meldung.setAttribute("role", "status");
  meldung.setAttribute("aria-live", "polite");
  meldung.style.cssText = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap";
  leiste.appendChild(meldung);

  function filtern(ort) {
    var sichtbar = 0;
    eintraege.forEach(function (eintrag) {
      var treffer = (ort === "*") || (eintrag.getAttribute("data-ort") === ort);
      eintrag.hidden = !treffer;
      if (treffer) sichtbar++;
    });
    knoepfe.forEach(function (knopf) {
      knopf.setAttribute("aria-pressed",
        knopf.getAttribute("data-ort") === ort ? "true" : "false");
    });
    meldung.textContent = sichtbar === 1
      ? "1 Termin angezeigt"
      : sichtbar + " Termine angezeigt";
  }

  knoepfe.forEach(function (knopf) {
    knopf.addEventListener("click", function () {
      filtern(knopf.getAttribute("data-ort"));
    });
  });
})();
