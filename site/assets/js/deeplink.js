/* ==========================================================================
   Deep-link order CTA.

   THE APPROACH, and why it is this way
   ------------------------------------
   Research showed that both DoorDash and Uber Eats already publish an
   apple-app-site-association file that CLAIMS their own HTTPS store URLs:

     doordash.com  ->  com.doordash.DoorDashConsumer   path  */store/*
     ubereats.com  ->  com.ubercab.UberEats.Dev        path  /store/*/*

   Because of that, a plain https:// link to the store page is ALREADY an
   App Link / Universal Link. The operating system resolves it to the app when
   installed, and to the browser when not. No JavaScript is required for the
   happy path.

   So the primary CTA is a plain <a href="https://...">. That is deliberate:
   it works when JS is off, inside email clients, from search results, and it
   cannot be broken by a timer race.

   The script below only layers on the fallback that matters:
     1. inside an in-app browser (Instagram, Facebook) mobile browsers block
        app switching, so we detect that and skip the app attempt entirely
     2. on desktop we never even try
     3. if the user explicitly opts in ("open in app"), we attempt the custom
        scheme with a visibility-change timeout fallback

   Weight: ~2 KB. No dependencies. Runs after paint.
   ========================================================================== */
(function () {
  'use strict';

  var SCHEME = '[data-scheme]';          // elements carrying a custom scheme
  var APP_TRIGGER = '[data-app-only]';   // opt-in "open in app" controls
  var STATUS = '[data-dl-status]';       // live region for announcements

  function isDesktop() {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches
      && window.innerWidth >= 1024;
  }

  /* An in-app webview (Instagram/Facebook browser) refuses to hand off to
     another app. Attempting anyway drops the user into a dead screen. */
  function inAppBrowser() {
    var ua = navigator.userAgent || '';
    return /FBAN|FBAV|Instagram|Line\/|MicroMessenger|Twitter/i.test(ua);
  }

  function announce(msg) {
    var el = document.querySelector(STATUS);
    if (el) { el.textContent = msg; }
  }

  /* iOS refuses to open a custom scheme unless it is inside a user gesture,
     so we only ever fire these from a real click/tap handler. */
  function tryScheme(el) {
    var scheme = el.getAttribute('data-scheme');
    if (!scheme) return;

    if (scheme.indexOf('{STORE_UUID}') > -1) {
      announce('Opening the Uber Eats app is not configured yet.');
      return;
    }
    if (isDesktop() || inAppBrowser()) {
      // fall through to the normal https link instead
      return;
    }

    var started = Date.now();
    var hidden = false;

    function onHide() {
      if (document.hidden) { hidden = true; }
    }
    document.addEventListener('visibilitychange', onHide);
    window.addEventListener('pagehide', function onHide2() {
      if (document.hidden) { hidden = true; }
    });

    window.location.href = scheme;

    // If the app did not take over within 1.4s we are still here: the app is
    // not installed. Send them to the web store page instead of a blank screen.
    window.setTimeout(function () {
      document.removeEventListener('visibilitychange', onHide);
      if (!hidden) {
        var web = el.getAttribute('href');
        if (web) { window.location.href = web; }
      }
    }, 1400);
  }

  function init() {
    // Enhance, never replace: the href stays a real https URL.
    document.querySelectorAll(SCHEME).forEach(function (el) {
      el.addEventListener('click', function () { tryScheme(el); });
    });

    document.querySelectorAll(APP_TRIGGER).forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.preventDefault();
        tryScheme(el);
      });
    });

    // Strip the "open in app" affordance where it can never work.
    if (isDesktop()) {
      document.querySelectorAll(SCHEME).forEach(function (el) {
        el.removeAttribute('data-scheme');
      });
      var n = document.querySelector('[data-dl-desktop]');
      if (n) { n.hidden = false; }
    }

    // Mark today's hours row.
    var today = document.querySelector('[data-today-row]');
    if (today) {
      var d = new Date().getDay();          // 0=Sun
      var map = { 1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri', 6: 'sat', 0: 'sun' };
      var sel = '[data-day="' + map[d] + '"]';
      var row = document.querySelector(sel);
      if (row) { row.classList.add('hours-row--today'); }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
