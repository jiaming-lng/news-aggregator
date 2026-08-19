/**
 * TechNews - 收藏页逻辑
 * 获取当前用户收藏的文章列表，支持取消收藏
 */

(function () {
  'use strict';

  var currentPage = 1;
  var totalPages = 1;

  // ---- 工具函数 ----
  function formatTime(dateStr) {
    if (!dateStr) return '';
    var date = new Date(dateStr.replace(' ', 'T'));
    var now = new Date();
    var diffMs = now - date;
    var diffMin = Math.floor(diffMs / 60000);
    var diffHr = Math.floor(diffMs / 3600000);
    var diffDay = Math.floor(diffMs / 86400000);
    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return diffMin + ' 分钟前';
    if (diffHr < 24) return diffHr + ' 小时前';
    if (diffDay < 7) return diffDay + ' 天前';
    return dateStr.slice(0, 10);
  }

  function getPlatformColor(platform) {
    var map = { youtube: '#FF0000', github: '#6e5494', hackernews: '#FF6600', bilibili: '#00A1D6', blog: '#0ea5e9', reddit: '#FF4500', github_trending: '#24292f', ithome: '#e60012', leiphone: '#00a383', sspai: '#e03e2d', solidot: '#ff6600', oschina: '#d2691e' };
    return map[platform] || '#64748b';
  }

  function getPlatformIcon(platform) {
    var map = { youtube: 'YT', github: 'GH', hackernews: 'HN', bilibili: 'BL', blog: 'BG', reddit: 'RD', github_trending: 'GT', ithome: 'IT', leiphone: 'LP', sspai: 'SP', solidot: 'SD', oschina: 'OS' };
    return map[platform] || '##';
  }

  function getPlatformName(platform) {
    var map = { youtube: 'YouTube', github: 'GitHub', hackernews: 'Hacker News', bilibili: 'Bilibili', blog: 'Blog', reddit: 'Reddit', github_trending: 'GitHub Trending', ithome: 'IT之家', leiphone: '雷峰网', sspai: '少数派', solidot: 'Solidot', oschina: '开源中国' };
    return map[platform] || platform;
  }

  function getCategoryName(cat) {
    var map = { tech: '科技', ai: 'AI', opensource: '开源' };
    return map[cat] || cat;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function showToast(msg, type) {
    var toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + (type || 'info') + ' show';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.classList.remove('show');
    }, 2500);
  }

  // ---- 渲染收藏卡片 ----
  function renderCard(article) {
    var platformColor = getPlatformColor(article.source_platform);
    var platformIcon = getPlatformIcon(article.source_platform);
    var platformName = getPlatformName(article.source_platform);
    var categoryName = getCategoryName(article.category);
    var timeStr = formatTime(article.published_at);
    var detailUrl = '/article/' + article.id;
    var sourceUrl = article.source_url || '#';
    var summary = article.summary || '暂无摘要';
    if (summary.length > 120) summary = summary.slice(0, 120) + '...';

    return '<div class="article-card" data-id="' + article.id + '">' +
      '<div class="card-header">' +
        '<span class="platform-badge" style="background: ' + platformColor + '">' +
          platformIcon + ' ' + escapeHtml(platformName) +
        '</span>' +
        '<span class="category-tag ' + article.category + '">' + categoryName + '</span>' +
      '</div>' +
      '<a href="' + detailUrl + '" class="article-title-link">' +
        '<h3 class="article-title">' + escapeHtml(article.title) + '</h3>' +
      '</a>' +
      '<p class="article-summary">' + escapeHtml(summary) + '</p>' +
      '<div class="article-meta">' +
        '<span class="meta-item">' + timeStr + '</span>' +
      '</div>' +
      '<div class="article-actions">' +
        '<a href="' + detailUrl + '" class="btn-source">阅读详情</a>' +
        (sourceUrl && sourceUrl !== '#' ? '<a href="' + escapeHtml(sourceUrl) + '" target="_blank" rel="noopener" class="btn-external">查看原文</a>' : '') +
        '<button class="fav-btn active" data-id="' + article.id + '" title="取消收藏">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>' +
        '</button>' +
      '</div>' +
    '</div>';
  }

  function renderPagination(page, total) {
    if (total <= 1) return '';
    var html = '';
    if (page > 1) {
      html += '<button class="page-btn" data-page="' + (page - 1) + '">上一页</button>';
    }
    html += '<span class="page-info">第 ' + page + ' / ' + total + ' 页</span>';
    if (page < total) {
      html += '<button class="page-btn" data-page="' + (page + 1) + '">下一页</button>';
    }
    return html;
  }

  // ---- 加载收藏列表 ----
  async function loadFavorites(page) {
    currentPage = page || 1;

    if (!TechNewsAuth.isLoggedIn()) {
      document.getElementById('loginPrompt').style.display = '';
      document.getElementById('loadingIndicator').style.display = 'none';
      document.getElementById('favoritesGrid').innerHTML = '';
      document.getElementById('emptyState').style.display = 'none';
      document.getElementById('pagination').innerHTML = '';
      return;
    }

    document.getElementById('loginPrompt').style.display = 'none';
    document.getElementById('loadingIndicator').style.display = '';
    document.getElementById('favoritesGrid').innerHTML = '';
    document.getElementById('emptyState').style.display = 'none';

    try {
      var resp = await fetch('/api/favorites?page=' + currentPage + '&limit=20', {
        headers: { 'Authorization': 'Bearer ' + TechNewsAuth.token }
      });
      var res = await resp.json();

      document.getElementById('loadingIndicator').style.display = 'none';

      if (!res.success) {
        showToast(res.error || '加载失败', 'error');
        return;
      }

      var data = res.data;
      totalPages = data.total_pages || 1;

      if (!data.articles || data.articles.length === 0) {
        document.getElementById('emptyState').style.display = '';
        document.getElementById('pagination').innerHTML = '';
        return;
      }

      var html = data.articles.map(renderCard).join('');
      document.getElementById('favoritesGrid').innerHTML = html;
      document.getElementById('pagination').innerHTML = renderPagination(currentPage, totalPages);
    } catch (err) {
      document.getElementById('loadingIndicator').style.display = 'none';
      showToast('网络错误，请刷新重试', 'error');
    }
  }

  // ---- 取消收藏 ----
  async function handleUnfavorite(articleId, cardEl) {
    if (!TechNewsAuth.isLoggedIn()) return;

    try {
      var res = await TechNewsAuth.toggleFavorite(articleId, true);
      if (res.success) {
        cardEl.style.opacity = '0';
        cardEl.style.transform = 'scale(0.9)';
        cardEl.style.transition = 'all 0.3s ease';
        setTimeout(function () {
          cardEl.remove();
          // 如果列表空了，显示空状态
          var grid = document.getElementById('favoritesGrid');
          if (!grid.children.length) {
            document.getElementById('emptyState').style.display = '';
            document.getElementById('pagination').innerHTML = '';
          }
        }, 300);
        showToast('已取消收藏', 'info');
      } else {
        showToast(res.error || '操作失败', 'error');
      }
    } catch (e) {
      showToast('网络错误', 'error');
    }
  }

  // ---- 事件绑定 ----
  function bindEvents() {
    // 事件委托：取消收藏按钮
    document.getElementById('favoritesGrid').addEventListener('click', function (e) {
      var favBtn = e.target.closest('.fav-btn');
      if (favBtn) {
        e.preventDefault();
        e.stopPropagation();
        var card = favBtn.closest('.article-card');
        var articleId = parseInt(favBtn.dataset.id, 10);
        handleUnfavorite(articleId, card);
      }
    });

    // 分页按钮
    document.getElementById('pagination').addEventListener('click', function (e) {
      if (e.target.classList.contains('page-btn')) {
        var page = parseInt(e.target.dataset.page, 10);
        loadFavorites(page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });

    // 登录提示按钮
    var loginPromptBtn = document.getElementById('loginPromptBtn');
    if (loginPromptBtn) {
      loginPromptBtn.addEventListener('click', function () {
        if (window.TechNewsAuthModal) TechNewsAuthModal.open('login');
      });
    }

    // 登录状态变化时重新加载
    document.addEventListener('auth:stateChanged', function () {
      loadFavorites(1);
    });
  }

  // ---- 初始化 ----
  function init() {
    bindEvents();
    loadFavorites(1);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
