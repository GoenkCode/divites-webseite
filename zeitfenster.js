/* Blendet Inhalte nach Datum ein und aus.
 *
 * Warum ueberhaupt: Manche Saetze haben ein Verfallsdatum. "Vorbestellen,
 * Auslieferung ab 11. Dezember" ist am 11. Dezember falsch, und niemand
 * merkt es, weil nichts kaputt aussieht. Exportiert wird von Hand und nur,
 * wenn sich Inhalte aendern -- nicht, weil Zeit vergeht. Dasselbe Prinzip
 * wie bei termine.js.
 *
 * Zwei Attribute, beide mit einem Datum JJJJ-MM-TT:
 *   data-ab="2026-12-11"   sichtbar ab diesem Tag, 0:00 Ortszeit
 *   data-bis="2026-12-11"  unsichtbar ab diesem Tag, 0:00 Ortszeit
 * Beide an einem Element ergeben ein Fenster.
 *
 * Der Generator setzt hidden schon beim Bauen nach dem Exporttag. Faellt
 * dieses Skript aus, steht also der Stand des Exports da -- veraltet
 * vielleicht, aber nie leer. Ein unlesbares Datum laesst das Element so,
 * wie der Generator es gebaut hat; der bricht bei einem solchen Datum
 * ohnehin ab.
 */
(function () {
  "use strict";

  function tag(roh) {
    var m = (roh || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return null;
    var d = new Date(+m[1], +m[2] - 1, +m[3]);
    return isNaN(d.getTime()) ? null : d;
  }

  var jetzt = new Date();
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-ab], [data-bis]"), function (el) {
      var abRoh = el.getAttribute("data-ab");
      var bisRoh = el.getAttribute("data-bis");
      var ab = tag(abRoh);
      var bis = tag(bisRoh);
      if ((abRoh && !ab) || (bisRoh && !bis)) return;
      var zeigen = (!ab || jetzt >= ab) && (!bis || jetzt < bis);
      el.hidden = !zeigen;
    });
})();
