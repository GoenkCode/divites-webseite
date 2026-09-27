/* Trennt kommende von vergangenen Terminen im Browser.
 *
 * Warum ueberhaupt: Die Seite ist statisch und wird von Hand exportiert.
 * Der Generator vergleicht die Termine einmal beim Bauen mit dem Datum
 * dieses Tages und schreibt das Ergebnis fest ins HTML. Ohne dieses
 * Skript zeigt die Seite also den Stand des letzten Exports -- ein
 * gestriges Konzert stuende weiter unter "kommend", und auf der
 * Startseite als naechstes. Auffallen wuerde das niemandem, denn nichts
 * sieht kaputt aus. Es ist nur falsch.
 *
 * Progressive Enhancement wie beim Ortsfilter: Das HTML enthaelt alle
 * Termine mit ihrem Datum. Faellt dieses Skript aus, fehlt die
 * Nachfuehrung, aber jeder Termin bleibt lesbar. Eine Terminliste, die
 * ohne JavaScript leer bleibt, waere ein Totalausfall.
 *
 * Laeuft vor filter.js, damit der Ortsfilter schon die nachgefuehrte
 * Liste sieht. Beide sind mit defer eingebunden und laufen in der
 * Reihenfolge, in der sie im HTML stehen.
 */
(function () {
  "use strict";

  // Datum ohne Uhrzeit: Ein Konzert gilt den ganzen Tag ueber als
  // kommend, auch abends um elf. Wer um 20:30 spielt, soll um 20:31
  // nicht aus der Liste fallen.
  var heute = new Date();
  heute = new Date(heute.getFullYear(), heute.getMonth(), heute.getDate());

  function istVergangen(li) {
    var roh = li.getAttribute("data-datum");
    if (!roh) return false;
    var teile = roh.split("-");
    if (teile.length !== 3) return false;
    var d = new Date(+teile[0], +teile[1] - 1, +teile[2]);
    if (isNaN(d.getTime())) return false;   // unlesbares Datum: stehen lassen
    return d < heute;
  }

  /* --- Startseite: die naechsten drei ------------------------------------ */
  /* Im HTML stehen zwoelf. Welche drei gezeigt werden, entscheidet sich
     hier, damit die Auswahl nicht auf dem Exporttag festhaengt. */
  var kurz = document.querySelector("[data-naechste]");
  if (kurz) {
    var wunsch = parseInt(kurz.getAttribute("data-naechste"), 10) || 3;
    var gezeigt = 0;
    Array.prototype.forEach.call(kurz.querySelectorAll(".termin"), function (li) {
      if (istVergangen(li) || gezeigt >= wunsch) {
        li.remove();
      } else {
        gezeigt++;
      }
    });
    // Ist alles verstrichen, bliebe sonst eine leere Liste unter der
    // Ueberschrift "Die naechsten Konzerte" stehen. Das sieht nach Fehler
    // aus, obwohl nur nichts ansteht.
    if (!gezeigt) {
      var satz = document.createElement("p");
      satz.className = "leer";
      satz.textContent = "Zurzeit sind keine Termine angekündigt.";
      kurz.parentNode.replaceChild(satz, kurz);
    }
    return;   // auf der Startseite gibt es sonst nichts zu tun
  }

  /* --- Termineseite: Verstrichenes umhaengen ----------------------------- */
  var ziel = document.querySelector("[data-vergangen-liste]");
  var block = document.querySelector("[data-vergangen]");
  if (!ziel || !block) return;

  // Nur Termine ausserhalb des Vergangen-Blocks pruefen. Was dort schon
  // liegt, ist beim Bauen einsortiert worden und steht richtig.
  var umzuhaengen = [];
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-monat] .termin"), function (li) {
      if (istVergangen(li)) umzuhaengen.push(li);
    });

  // Der Vergangen-Block ist absteigend sortiert, das juengste Konzert
  // steht oben. umzuhaengen liegt in Dokumentreihenfolge vor, also
  // aufsteigend; wird jedes Element vorne eingefuegt, dreht sich die
  // Reihenfolge dabei von selbst um. Ein zusaetzliches reverse() drehte
  // sie ein zweites Mal und stellte das aelteste Konzert nach oben.
  umzuhaengen.forEach(function (li) {
    // Die Markierung "zweiter Termin am selben Tag" gilt nur innerhalb
    // der Monatsgliederung. In der flachen Liste wuerde sie ein Datum
    // unterschlagen.
    li.classList.remove("termin--folge");
    ziel.insertBefore(li, ziel.firstChild);
  });

  if (umzuhaengen.length) block.hidden = false;

  // Monate, aus denen alles abgewandert ist, verschwinden mitsamt ihrer
  // Ueberschrift. Sonst stuende "September 2026" ueber einer leeren Liste.
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-monat]"), function (abschnitt) {
      if (!abschnitt.querySelector(".termin")) abschnitt.hidden = true;
    });

  // Steht gar nichts Kommendes mehr an, braucht es einen Satz dazu --
  // eine Seite, die zwischen Filterleiste und Vergangenem nichts zeigt,
  // sieht nach Fehler aus.
  var nochKommend = document.querySelector("[data-monat]:not([hidden]) .termin");
  if (!nochKommend && !document.querySelector(".leer")) {
    var hinweis = document.createElement("p");
    hinweis.className = "leer";
    hinweis.textContent = "Zurzeit sind keine Termine angekündigt.";
    block.parentNode.insertBefore(hinweis, block);
  }

  // Ortsknoepfe, zu denen es keinen kommenden Termin mehr gibt, entfernen.
  // Ein Filter, der auf eine leere Liste fuehrt, ist schlimmer als keiner.
  var leiste = document.querySelector("[data-filter]");
  if (leiste) {
    var offen = {};
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-monat]:not([hidden]) .termin"), function (li) {
        offen[li.getAttribute("data-ort")] = true;
      });
    var uebrig = 0;
    Array.prototype.forEach.call(
      leiste.querySelectorAll(".filter__knopf"), function (knopf) {
        var ort = knopf.getAttribute("data-ort");
        if (ort === "*") return;
        if (offen[ort]) uebrig++; else knopf.remove();
      });
    // Bleibt hoechstens eine Stadt uebrig, ist nichts mehr zu filtern.
    // Die Leiste wird entfernt statt versteckt: filter.js laeuft danach
    // und wuerde ein verstecktes Element wieder sichtbar machen.
    if (uebrig < 2) leiste.remove();
  }
})();
