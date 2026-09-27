/* Sanfter Wechsel der Stimmen im Kopfbereich.
 *
 * Bewusst kein Slider: keine Pfeile, keine Punkte, kein Wischen. Die
 * Zitate loesen einander ruhig ab, mehr nicht. Wer stehenbleiben will,
 * faehrt mit der Maus darueber.
 *
 * Drei Bedingungen, die nicht verhandelbar sind:
 *
 * 1. Ohne JavaScript stehen alle Zitate untereinander da. Das Markup
 *    ist vollstaendig, dieses Skript stapelt sie erst uebereinander.
 * 2. prefers-reduced-motion wird respektiert. Bewegung loest bei
 *    manchen Menschen Schwindel und Uebelkeit aus; das ist kein
 *    Geschmacksthema. Dann bleibt alles stehen.
 * 3. Bei weniger als zwei Zitaten passiert nichts. Ein einzelnes
 *    Zitat, das sich mit sich selbst abwechselt, waere albern.
 */
(function () {
  "use strict";

  var bereich = document.querySelector("[data-stimmen]");
  if (!bereich) return;

  var stimmen = Array.prototype.slice.call(bereich.querySelectorAll(".stimme"));
  if (stimmen.length < 2) return;

  var ruhig = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)");
  if (ruhig && ruhig.matches) return;

  bereich.classList.add("stimmen--wechsel");
  var aktuell = 0;
  stimmen.forEach(function (s, i) {
    s.classList.toggle("stimme--sichtbar", i === 0);
    s.setAttribute("aria-hidden", i === 0 ? "false" : "true");
  });

  var laeuft = true;
  bereich.addEventListener("mouseenter", function () { laeuft = false; });
  bereich.addEventListener("mouseleave", function () { laeuft = true; });
  bereich.addEventListener("focusin", function () { laeuft = false; });

  setInterval(function () {
    if (!laeuft || document.hidden) return;
    stimmen[aktuell].classList.remove("stimme--sichtbar");
    stimmen[aktuell].setAttribute("aria-hidden", "true");
    aktuell = (aktuell + 1) % stimmen.length;
    stimmen[aktuell].classList.add("stimme--sichtbar");
    stimmen[aktuell].setAttribute("aria-hidden", "false");
  }, 7000);
})();
