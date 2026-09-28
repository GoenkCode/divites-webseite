/* Anfrageformular ohne Formulardienst.
 *
 * Die Seite liegt auf GitHub Pages und hat keinen Server, der ein
 * abgeschicktes Formular entgegennehmen koennte. Der uebliche Ausweg ist
 * ein Dienst wie Formspree: der laeuft in den USA, verlangt einen
 * Auftragsverarbeitungsvertrag und einen Abschnitt in der
 * Datenschutzerklaerung -- fuer ein Kontaktformular eines Quartetts ein
 * schlechtes Geschaeft.
 *
 * Deshalb baut dieses Skript aus den Eingaben eine mailto-Adresse und
 * uebergibt sie dem Mailprogramm der Besucherin. Die Daten verlassen den
 * Rechner nicht, bevor sie dort auf "Senden" drueckt. Es gibt keinen
 * Dritten, der sie sieht, und nichts, was in die Datenschutzerklaerung
 * muesste ausser dem Hinweis, dass genau das passiert.
 *
 * Ohne JavaScript bleibt das Formular stehen, ist aber nutzlos. Deshalb
 * steht die Mailadresse als normaler Link darueber und wird nie versteckt.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-anfrage]");
  if (!form) return;

  var ziel = form.getAttribute("data-anfrage");
  if (!ziel) return;

  // Erst jetzt einblenden: Ohne Skript waere ein Formular sichtbar, das
  // beim Absenden nichts tut. Ein Knopf, der nicht funktioniert, ist
  // schlimmer als kein Knopf.
  form.hidden = false;

  function wert(name) {
    var feld = form.elements[name];
    return feld && feld.value ? feld.value.trim() : "";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    var datum = wert("datum");
    var ort = wert("ort");

    var betreff = "Konzertanfrage";
    if (datum) betreff += " " + datum;
    if (ort) betreff += ", " + ort;

    var zeilen = [];
    [["Name", "name"], ["Datum und Uhrzeit", "datum"], ["Ort und Raum", "ort"],
     ["Anlass", "anlass"], ["Gewünschte Spieldauer", "dauer"]
    ].forEach(function (paar) {
      var v = wert(paar[1]);
      if (v) zeilen.push(paar[0] + ": " + v);
    });

    var text = wert("nachricht");
    if (text) zeilen.push("", text);

    if (!zeilen.length) {
      form.elements.nachricht.focus();
      return;
    }

    // encodeURIComponent auf beide Teile: Ein Umlaut oder ein Zeilenumbruch
    // im Betreff zerlegt sonst die URL, und das Mailprogramm oeffnet sich
    // mit halber Nachricht.
    var url = "mailto:" + ziel
            + "?subject=" + encodeURIComponent(betreff)
            + "&body=" + encodeURIComponent(zeilen.join("\n"));

    // Manche Mailprogramme und Browser kappen lange mailto-Adressen
    // stillschweigend. Lieber eine ehrliche Ansage als eine Nachricht,
    // die beim Empfaenger mitten im Satz aufhoert.
    if (url.length > 1800) {
      var lang = form.querySelector("[data-zulang]");
      if (lang) lang.hidden = false;
      form.elements.nachricht.focus();
      return;
    }

    window.location.href = url;

    var hinweis = form.querySelector("[data-hinweis]");
    if (hinweis) hinweis.hidden = false;
  });
})();
