/**
 * 爬虫健康状态检测（看门狗前端）
 * 拉取 /api/crawler/status，若爬虫停摆（超过阈值无更新）则显示告警条。
 * 页面加载时检查一次，之后每 5 分钟复查。
 */
(function () {
  'use strict';

  var CHECK_INTERVAL_MS = 5 * 60 * 1000; // 5 分钟

  function checkCrawlerStatus() {
    fetch('/api/crawler/status', {
      headers: { 'Accept': 'application/json' },
      cache: 'no-store'
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data || !data.success) return;
        var st = data.data;
        var alertEl = document.getElementById('crawlerAlert');
        if (!alertEl) return;

        if (!st.healthy) {
          var minsEl = document.getElementById('crawlerAlertMinutes');
          if (minsEl) {
            minsEl.textContent = st.minutes_since_last_crawl != null
              ? st.minutes_since_last_crawl
              : '--';
          }
          alertEl.style.display = 'flex';
        } else {
          alertEl.style.display = 'none';
        }
      })
      .catch(function () {
        // 网络异常不打扰用户，静默跳过
      });
  }

  // 首次检查
  checkCrawlerStatus();
  // 定期复查
  setInterval(checkCrawlerStatus, CHECK_INTERVAL_MS);
})();
