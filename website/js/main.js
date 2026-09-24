/* Nebula Launcher 官网脚本：星空粒子 + 滚动效果 */
(function () {
  "use strict";

  // 顶栏滚动状态
  var nav = document.getElementById("nav");
  window.addEventListener("scroll", function () {
    nav.classList.toggle("scrolled", window.scrollY > 20);
  });

  // 滚动显现动画
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("show");
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".section-head, .card, .shots figure, .split, .repo, .hero-inner")
    .forEach(function (el) { el.classList.add("reveal"); observer.observe(el); });

  // 星空粒子
  var canvas = document.getElementById("stars");
  if (canvas) {
    var ctx = canvas.getContext("2d");
    var W, H, stars = [];
    function resize() {
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
    }
    function init() {
      resize();
      stars = [];
      var n = Math.min(160, Math.floor(W * H / 9000));
      for (var i = 0; i < n; i++) {
        stars.push({
          x: Math.random() * W,
          y: Math.random() * H,
          r: Math.random() * 1.6 + 0.3,
          a: Math.random() * 0.7 + 0.2,
          v: Math.random() * 0.12 + 0.02,
          tw: Math.random() * Math.PI * 2
        });
      }
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < stars.length; i++) {
        var s = stars[i];
        s.y -= s.v;
        if (s.y < -4) { s.y = H + 4; s.x = Math.random() * W; }
        s.tw += 0.02;
        var alpha = s.a * (0.5 + 0.5 * Math.sin(s.tw));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(180,210,255," + alpha.toFixed(3) + ")";
        ctx.fill();
      }
      requestAnimationFrame(draw);
    }
    window.addEventListener("resize", init);
    init();
    draw();
  }
})();
