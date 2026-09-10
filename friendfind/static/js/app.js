/* Theme toggle (Girly Pop / Goth Babe), WebAudio chimes, heart-sparkle burst. */
(function () {
  "use strict";

  /* ---- theme ---- */
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("ff-theme");
    if (saved === "melody" || saved === "kuromi") root.dataset.theme = saved;
  } catch (e) {}
  /* ---- collapsible nav on small screens ---- */
  var navToggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");
  if (navToggle && nav) navToggle.addEventListener("click", function () {
    var open = nav.classList.toggle("nav-open");
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  var toggle = document.getElementById("theme-toggle");
  if (toggle) toggle.addEventListener("click", function () {
    var next = root.dataset.theme === "kuromi" ? "melody" : "kuromi";
    root.dataset.theme = next;
    try { localStorage.setItem("ff-theme", next); } catch (e) {}
  });

  /* ---- chimes (synthesized, no audio files) ---- */
  function playChime(kind) {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    var ctx = new Ctx();
    var notes = { twinkle: [880, 1174.7, 1568], bell: [659.3, 987.8], pop: [392, 523.3] }[kind]
             || [880, 1174.7, 1568];
    notes.forEach(function (freq, i) {
      var osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.type = kind === "pop" ? "triangle" : "sine";
      osc.frequency.value = freq;
      var t = ctx.currentTime + i * 0.09;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.18, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.7);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t); osc.stop(t + 0.75);
    });
    setTimeout(function () { ctx.close(); }, 1500);
  }

  function chimePrefs() {
    try {
      return {
        enabled: localStorage.getItem("ff-chime") === "on",
        choice: localStorage.getItem("ff-chime-choice") || "twinkle"
      };
    } catch (e) { return { enabled: false, choice: "twinkle" }; }
  }

  var chimeEnabled = document.getElementById("chime-enabled");
  var chimeChoice = document.getElementById("chime-choice");
  var chimePreview = document.getElementById("chime-preview");
  if (chimeEnabled) {
    var p = chimePrefs();
    chimeEnabled.checked = p.enabled;
    chimeChoice.value = p.choice;
    chimeEnabled.addEventListener("change", function () {
      try { localStorage.setItem("ff-chime", chimeEnabled.checked ? "on" : "off"); } catch (e) {}
    });
    chimeChoice.addEventListener("change", function () {
      try { localStorage.setItem("ff-chime-choice", chimeChoice.value); } catch (e) {}
    });
    chimePreview.addEventListener("click", function () { playChime(chimeChoice.value); });
  }

  // Chime on in-app notifications (success flashes, celebrations).
  var wantsChime = document.querySelector('[data-chime="success"]');
  if (wantsChime) {
    var prefs = chimePrefs();
    if (prefs.enabled) playChime(prefs.choice);
  }

  /* ---- heart-sparkle burst on check-in ---- */
  var stage = document.querySelector(".burst-stage");
  if (stage) {
    var glyphs = ["💗", "✨", "💖", "⭐", "🎀", "✦", "💜"];
    for (var i = 0; i < 26; i++) {
      var el = document.createElement("span");
      el.className = "burst-particle";
      el.textContent = glyphs[i % glyphs.length];
      var angle = Math.random() * Math.PI * 2;
      var dist = 60 + Math.random() * 160;
      el.style.setProperty("--dx", Math.cos(angle) * dist + "px");
      el.style.setProperty("--dy", (Math.sin(angle) * dist - 60) + "px");
      el.style.setProperty("--rot", (Math.random() * 240 - 120) + "deg");
      el.style.animationDelay = (Math.random() * 0.35) + "s";
      stage.appendChild(el);
    }
    setTimeout(function () { stage.innerHTML = ""; }, 2500);
  }
})();
