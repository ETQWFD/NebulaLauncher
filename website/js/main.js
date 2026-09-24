/* Nebula Launcher 官网脚本：滚动效果与导航状态 */
(function () {
  "use strict";

  var nav = document.querySelector(".nav");
  window.addEventListener("scroll", function () {
    nav.classList.toggle("scrolled", window.scrollY > 16);
  });

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("show");
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll(".section-title, .card, .shots figure, .step, .badge, .hero h1, .lead, .hero-actions, .hero-stats, .dl, .code")
    .forEach(function (el) { el.classList.add("reveal"); observer.observe(el); });
})();
