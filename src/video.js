/* Zwei-Klick-Einbettung fuer YouTube.
 *
 * Ein normales <iframe> nimmt schon beim Laden der Seite Verbindung zu
 * Google auf und uebertraegt die IP-Adresse der Besucherin — auch wenn
 * das Video nie abgespielt wird. Selbst das Vorschaubild kaeme von dort.
 * Deshalb wird vor dem Klick nichts Externes geladen, nicht einmal ein Bild.
 *
 * Erst der Klick erzeugt das iframe.
 *
 * Ohne JavaScript bleibt die Flaeche stehen; darunter steht ein normaler
 * Link zu YouTube. Niemand steht vor einem toten Kasten.
 */
(function () {
  "use strict";

  var flaechen = Array.prototype.slice.call(
    document.querySelectorAll(".video__flaeche[data-video]"));
  if (!flaechen.length) return;

  flaechen.forEach(function (knopf) {
    knopf.addEventListener("click", function () {
      var id = knopf.getAttribute("data-video");
      var titel = knopf.getAttribute("data-titel") || "Video";
      if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return;   // nur echte Video-IDs

      var rahmen = document.createElement("iframe");
      // youtube.com statt youtube-nocookie.com: Der nocookie-Dienst
      // loeste regelmaessig YouTubes Bot-Pruefung aus ("Melde dich an,
      // damit wir sehen, dass du kein Bot bist"), weil dort keine
      // Session existiert. Der Datenschutzgewinn war damit wertlos:
      // das Video lief gar nicht erst.
      // Vertretbar, weil die Verbindung ohnehin erst nach dem Klick
      // entsteht, also mit Einwilligung.
      rahmen.src = "https://www.youtube.com/embed/" + id + "?autoplay=1&rel=0";
      rahmen.title = titel;
      rahmen.loading = "lazy";
      rahmen.allow = "accelerometer; autoplay; encrypted-media; picture-in-picture";
      rahmen.setAttribute("allowfullscreen", "");
      rahmen.className = "video__rahmen";

      knopf.parentNode.replaceChild(rahmen, knopf);
      rahmen.focus();
    });
  });
})();
