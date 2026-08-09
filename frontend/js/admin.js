/**
 * TechNews 资讯聚合网站 - 管理后台逻辑
 * 数据统计、图表展示、爬取状态监控
 * 使用 Visibility API 优化后台轮询，避免标签页不可见时浪费资源
 */

(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);

  // ---- 带认证的请求封装 ----
  function authHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    const token = localStorage.getItem('technews_token');
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return headers;
  }

  // ---- 数据加载 ----
  async function loadStats() {
    try {
      const resp = await fetch('/api/stats', { headers: authHeaders() });
      if (resp.status === 401) throw new Error('未登录');
      if (!resp.ok) throw new Error('请求失败');
      const res = await resp.json();
      if (!res.success) throw new Error('数据获取失败');
      return res.data;
    } catch (err) {
      console.error('加载统计数据失败:', err);
      return null;
    }
  }

  async function loadCrawlLogs() {
    try {
      const resp = await fetch('/api/crawl-logs?limit=30', { headers: authHeaders() });
      if (resp.status === 401) throw new Error('未登录');
      if (!resp.ok) throw new Error('请求失败');
      const res = await resp.json();
      if (!res.success) throw new Error('日志获取失败');
      return res.data;
    } catch (err) {
      console.error('加载爬取日志失败:', err);
      return [];
    }
  }

  // ---- 渲染函数 ----
  function renderStats(stats) {
    if (!stats) {
      $('#statsGrid').innerHTML = '<p style="color: var(--text-muted);">统计数据加载失败</p>';
      return;
    }

    $('#statTotal').textContent = stats.total_articles.toLocaleString();
    $('#statToday').textContent = stats.today_articles.toLocaleString();
    $('#statCrawls').textContent = stats.success_crawls + '/' + stats.total_crawls;

    renderBarChart('categoryChart', stats.by_category, {
      tech: { label: '科技', class: 'tech' },
      ai: { label: 'AI', class: 'ai' },
      opensource: { label: '开源', class: 'opensource' }
    }, '资讯分类分布');

    renderBarChart('platformChart', stats.by_platform, {
      youtube: { label: 'YouTube', class: 'youtube' },
      github: { label: 'GitHub', class: 'github' },
      hackernews: { label: 'Hacker News', class: 'hackernews' },
      bilibili: { label: 'Bilibili', class: 'bilibili' },
      tiktok: { label: 'TikTok', class: 'tiktok' },
      blog: { label: 'Blog', class: 'blog' }
    }, '数据来源平台分布');

    renderDailyTrend(stats.daily_new);
  }

  function renderBarChart(containerId, data, labels, ariaLabel) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // 更新 aria-label 包含具体数据
    const entries = Object.entries(data);
    if (entries.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">暂无数据</p>';
      return;
    }

    const maxVal = Math.max.apply(null, entries.map(function (e) { return e[1]; }).concat([1]));

    // 构建 aria 描述文本
    const descParts = entries.map(function (e) {
      var info = labels[e[0]] || { label: e[0] };
      return info.label + ': ' + e[1] + ' 条';
    });
    container.setAttribute('aria-label', ariaLabel + '：' + descParts.join('，'));

    var html = '<div class="bar-chart">';
    entries.forEach(function (entry) {
      var key = entry[0], val = entry[1];
      var info = labels[key] || { label: key, class: 'tech' };
      var pct = Math.round((val / maxVal) * 100);
      html +=
        '<div class="bar-row">' +
          '<div class="bar-label">' + info.label + '</div>' +
          '<div class="bar-track">' +
            '<div class="bar-fill ' + info.class + '" style="width: ' + pct + '%"></div>' +
          '</div>' +
          '<div class="bar-value">' + val + '</div>' +
        '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  function renderDailyTrend(dailyData) {
    const container = document.getElementById('dailyTrend');
    if (!container) return;

    const entries = Object.entries(dailyData || {}).sort();
    if (entries.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">暂无数据</p>';
      return;
    }

    // 构建 aria 描述
    var descParts = entries.map(function (e) { return e[0] + ': ' + e[1] + ' 条'; });
    container.setAttribute('aria-label', '近7日每日新增趋势：' + descParts.join('，'));

    var width = container.clientWidth || 500;
    var height = 200;
    var padding = { top: 20, right: 20, bottom: 40, left: 50 };
    var chartW = width - padding.left - padding.right;
    var chartH = height - padding.top - padding.bottom;

    var maxVal = Math.max.apply(null, entries.map(function (e) { return e[1]; }).concat([1]));
    var points = entries.map(function (entry, i) {
      return {
        x: padding.left + (i / Math.max(entries.length - 1, 1)) * chartW,
        y: padding.top + chartH - (entry[1] / maxVal) * chartH,
        day: entry[0].slice(5),
        val: entry[1]
      };
    });

    var pathD = points.map(function (p, i) {
      return (i === 0 ? 'M' : 'L') + p.x + ',' + p.y;
    }).join(' ');

    var dots = points.map(function (p) {
      return '<circle cx="' + p.x + '" cy="' + p.y + '" r="4" fill="var(--accent)" stroke="var(--bg-card)" stroke-width="2"/>';
    }).join('');

    var xLabels = points.filter(function (_, i) {
      if (points.length <= 7) return true;
      return i % Math.ceil(points.length / 7) === 0 || i === points.length - 1;
    }).map(function (p) {
      return '<text x="' + p.x + '" y="' + (height - 10) + '" text-anchor="middle" font-size="11" fill="var(--text-muted)">' + p.day + '</text>';
    }).join('');

    container.innerHTML =
      '<svg width="100%" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '" style="display: block;" role="img" aria-label="每日新增趋势折线图">' +
        '<line x1="' + padding.left + '" y1="' + padding.top + '" x2="' + padding.left + '" y2="' + (height - padding.bottom) + '" stroke="var(--border-color)" stroke-width="1"/>' +
        '<line x1="' + padding.left + '" y1="' + (height - padding.bottom) + '" x2="' + (width - padding.right) + '" y2="' + (height - padding.bottom) + '" stroke="var(--border-color)" stroke-width="1"/>' +
        '<path d="' + pathD + '" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<path d="' + pathD + ' L' + points[points.length - 1].x + ',' + (height - padding.bottom) + ' L' + points[0].x + ',' + (height - padding.bottom) + ' Z" fill="var(--accent)" opacity="0.08"/>' +
        dots + xLabels +
      '</svg>';
  }

  function renderCrawlLogs(logs) {
    const tbody = $('#logTbody');
    if (!tbody) return;

    if (logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 40px;">暂无爬取记录</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(function (log) {
      var statusClass = log.status === 'success' ? 'success' : log.status === 'failed' ? 'failed' : 'running';
      var statusText = log.status === 'success' ? '成功' : log.status === 'failed' ? '失败' : '运行中';

      return '<tr>' +
        '<td>' + log.platform + '</td>' +
        '<td><span class="status-badge ' + statusClass + '">' + statusText + '</span></td>' +
        '<td>' + (log.articles_fetched || 0) + ' 条</td>' +
        '<td>' + (log.articles_new || 0) + ' 条</td>' +
        '<td>' + (log.started_at ? new Date(log.started_at).toLocaleString('zh-CN') : '-') + '</td>' +
      '</tr>';
    }).join('');
  }

  // ---- 爬取触发 ----
  async function triggerCrawl() {
    const btn = $('#btnTriggerCrawl');
    const status = $('#crawlStatusMsg');

    btn.disabled = true;
    btn.textContent = '爬取中...';
    status.className = 'crawl-status running';
    status.textContent = '正在爬取各平台最新资讯...';

    try {
      const resp = await fetch('/api/crawl/trigger', { method: 'POST', headers: authHeaders() });
      const res = await resp.json();

      if (res.success) {
        status.className = 'crawl-status success';
        status.textContent = res.data.message;
      } else {
        throw new Error(res.error || '爬取失败');
      }
    } catch (err) {
      status.className = 'crawl-status failed';
      status.textContent = '爬取出错: ' + err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = '手动触发爬取';
    }

    setTimeout(refreshAll, 1000);
  }

  // 绑定事件
  const btnTrigger = $('#btnTriggerCrawl');
  if (btnTrigger) {
    btnTrigger.addEventListener('click', triggerCrawl);
  }

  // ---- 刷新（基于页面可见性优化） ----
  async function refreshAll() {
    const stats = await loadStats();
    renderStats(stats);

    const logs = await loadCrawlLogs();
    renderCrawlLogs(logs);
  }

  // 使用 Visibility API 控制轮询：标签页不可见时暂停
  var refreshTimer = null;
  var REFRESH_INTERVAL = 60000;

  function startAutoRefresh() {
    if (refreshTimer) return;
    refreshTimer = setInterval(refreshAll, REFRESH_INTERVAL);
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      stopAutoRefresh();
    } else {
      // 页面重新可见时立即刷新一次，然后恢复定时
      refreshAll();
      startAutoRefresh();
    }
  });

  // ---- 启动 ----
  function init() {
    // 登录检查：未登录引导登录，不加载数据
    if (window.TechNewsAuth && !window.TechNewsAuth.isLoggedIn()) {
      const container = document.getElementById('statsGrid');
      if (container) {
        container.innerHTML = '<p style="color: var(--text-muted); padding: 40px; text-align: center;">管理后台需要登录后才能访问 🔒<br><br><button onclick="window.TechNewsAuthModal.open(\'login\')" style="padding: 10px 28px; border-radius: 100px; border: none; background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; cursor: pointer;">去登录</button></p>';
      }
      return;
    }
    refreshAll();
    startAutoRefresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 登录成功后自动刷新后台数据
  document.addEventListener('auth:stateChanged', function () {
    if (window.TechNewsAuth && window.TechNewsAuth.isLoggedIn()) {
      location.reload();
    }
  });

  console.log('Admin dashboard ready');
})();
