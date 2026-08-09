/**
 * TechNews 公共模块 - 主题切换
 * 所有页面共享，消除 5 个 JS 文件中的重复代码
 * SVG 图标方案：太阳（亮色模式）/ 月亮（暗色模式）
 */

(function () {
  'use strict';

  var SUN_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  var MOON_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>';

  function getTheme() {
    var saved = localStorage.getItem('technews-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return saved || (prefersDark ? 'dark' : 'light');
  }

  function updateToggleUI(theme) {
    var toggles = document.querySelectorAll('.theme-toggle');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].innerHTML = theme === 'dark' ? SUN_SVG : MOON_SVG;
      toggles[i].setAttribute('aria-label', theme === 'dark' ? '切换到亮色主题' : '切换到暗色主题');
      toggles[i].setAttribute('title', theme === 'dark' ? '切换到亮色主题' : '切换到暗色主题');
    }
  }

  function initTheme() {
    var theme = getTheme();
    document.documentElement.setAttribute('data-theme', theme);
    updateToggleUI(theme);
  }

  function toggleTheme() {
    var html = document.documentElement;
    var current = html.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('technews-theme', next);
    updateToggleUI(next);
  }

  function bindToggles() {
    var toggles = document.querySelectorAll('.theme-toggle');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener('click', toggleTheme);
    }
  }

  window.TechNewsTheme = {
    init: initTheme,
    toggle: toggleTheme,
    getTheme: getTheme
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTheme();
      bindToggles();
    });
  } else {
    initTheme();
    bindToggles();
  }
})();
