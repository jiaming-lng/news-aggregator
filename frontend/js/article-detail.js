/**
 * TechNews - 文章详情页逻辑
 * 从 API 获取文章详情 + 相关推荐，渲染到页面
 */

(function () {
  'use strict';

  // ---- 工具函数（复用首页逻辑） ----
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

  function formatNumber(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + 'w';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function getPlatformColor(platform) {
    var map = { youtube: '#FF0000', github: '#6e5494', hackernews: '#FF6600', bilibili: '#00A1D6', blog: '#0ea5e9', reddit: '#FF4500' };
    return map[platform] || '#64748b';
  }

  function getPlatformIcon(platform) {
    var map = { youtube: 'YT', github: 'GH', hackernews: 'HN', bilibili: 'BL', blog: 'BG', reddit: 'RD' };
    return map[platform] || '##';
  }

  function getPlatformName(platform) {
    var map = { youtube: 'YouTube', github: 'GitHub', hackernews: 'Hacker News', bilibili: 'Bilibili', blog: 'Blog', reddit: 'Reddit' };
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

  // ---- 从 URL 提取文章 ID ----
  function getArticleId() {
    var match = window.location.pathname.match(/\/article\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  // ---- API 调用 ----
  async function fetchArticleDetail(id) {
    var resp = await fetch('/api/articles/' + id);
    if (!resp.ok) throw new Error('请求失败');
    return resp.json();
  }

  // ---- 渲染函数 ----
  function renderArticle(data) {
    var article = data.article;
    var platform = article.source_platform;
    var platformColor = getPlatformColor(platform);
    var platformIcon = getPlatformIcon(platform);
    var platformName = getPlatformName(platform);
    var category = article.category;
    var categoryName = getCategoryName(category);
    var timeStr = formatTime(article.published_at);
    var sourceUrl = article.source_url || '#';

    // 平台徽章
    var badgeEl = document.getElementById('detailPlatform');
    badgeEl.textContent = platformIcon + ' ' + platformName;
    badgeEl.style.background = platformColor;

    // 分类标签
    var catEl = document.getElementById('detailCategory');
    catEl.textContent = categoryName;
    catEl.className = 'category-tag ' + category;

    // 标题
    document.getElementById('detailTitle').textContent = article.title;
    document.title = article.title + ' - TechNews';

    // 元信息
    var metaParts = [];
    if (article.author) metaParts.push('<span class="meta-item">by ' + escapeHtml(article.author) + '</span>');
    metaParts.push('<span class="meta-item">' + timeStr + '</span>');
    if (article.view_count > 0) metaParts.push('<span class="meta-item">' + formatNumber(article.view_count + 1) + ' views</span>');
    document.getElementById('detailMeta').innerHTML = metaParts.join('');

    // 摘要
    var summaryEl = document.getElementById('detailSummary');
    var summary = article.summary || '暂无摘要';
    // 如果摘要包含 | 分隔符（Bilibili/HN格式），按行展示
    if (summary.indexOf(' | ') > -1) {
      var parts = summary.split(' | ').filter(function (s) { return s.trim(); });
      summaryEl.innerHTML = parts.map(function (p) {
        return '<p>' + escapeHtml(p) + '</p>';
      }).join('');
    } else {
      summaryEl.innerHTML = '<p>' + escapeHtml(summary) + '</p>';
    }

    // 原文链接
    var sourceLink = document.getElementById('detailSourceLink');
    sourceLink.href = sourceUrl;
    if (sourceUrl === '#' || !sourceUrl) {
      sourceLink.style.display = 'none';
    }

    // 关键词标签
    var keywordsEl = document.getElementById('detailKeywords');
    if (article.keywords) {
      var keywords = article.keywords.split(',').filter(function (k) { return k.trim(); });
      if (keywords.length > 0) {
        keywordsEl.innerHTML = keywords.map(function (kw) {
          return '<span class="keyword-tag">' + escapeHtml(kw) + '</span>';
        }).join('');
      }
    }

    // 显示文章，隐藏加载状态
    document.getElementById('loadingIndicator').style.display = 'none';
    document.getElementById('articleDetail').style.display = '';

    // 检查收藏状态
    checkFavoriteStatus(article.id);
  }

  // ---- 收藏状态检查 ----
  async function checkFavoriteStatus(articleId) {
    var btn = document.getElementById('btnFavorite');
    if (!btn) return;
    if (!window.TechNewsAuth || !TechNewsAuth.isLoggedIn()) return;

    try {
      var resp = await fetch('/api/favorites', { headers: { 'Authorization': 'Bearer ' + TechNewsAuth.token } });
      var res = await resp.json();
      if (res.success) {
        var ids = res.data.articles.map(function (a) { return a.id; });
        if (ids.indexOf(articleId) > -1) {
          btn.classList.add('active');
          btn.querySelector('.fav-text').textContent = '已收藏';
        }
      }
    } catch (e) { /* 忽略 */ }
  }

  // ---- 收藏按钮点击 ----
  async function handleFavorite(articleId) {
    var btn = document.getElementById('btnFavorite');
    if (!btn) return;

    if (!TechNewsAuth.isLoggedIn()) {
      showToast('请先登录后再收藏', 'info');
      if (window.TechNewsAuthModal) TechNewsAuthModal.open('login');
      return;
    }

    var isFavorited = btn.classList.contains('active');
    btn.disabled = true;

    try {
      var res = await TechNewsAuth.toggleFavorite(articleId, isFavorited);
      if (res.success) {
        if (isFavorited) {
          btn.classList.remove('active');
          btn.querySelector('.fav-text').textContent = '收藏';
          showToast('已取消收藏', 'info');
        } else {
          btn.classList.add('active');
          btn.querySelector('.fav-text').textContent = '已收藏';
          showToast('收藏成功！', 'success');
        }
      } else if (res.needLogin) {
        showToast('请先登录后再收藏', 'info');
        if (window.TechNewsAuthModal) TechNewsAuthModal.open('login');
      } else {
        showToast(res.error || '操作失败', 'error');
      }
    } catch (e) {
      showToast('网络错误，请重试', 'error');
    }
    btn.disabled = false;
  }

  function renderRelated(related) {
    if (!related || related.length === 0) {
      document.getElementById('relatedSection').style.display = 'none';
      return;
    }

    var html = related.map(function (article) {
      var platformColor = getPlatformColor(article.source_platform);
      var platformIcon = getPlatformIcon(article.source_platform);
      var platformName = getPlatformName(article.source_platform);
      var timeStr = formatTime(article.published_at);
      var detailUrl = '/article/' + article.id;
      var categoryName = getCategoryName(article.category);

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
        '<p class="article-summary">' + escapeHtml(article.summary || '暂无摘要') + '</p>' +
        '<div class="article-meta">' +
          '<span class="meta-item">' + timeStr + '</span>' +
        '</div>' +
        '<div class="article-actions">' +
          '<a href="' + detailUrl + '" class="btn-source">阅读详情</a>' +
        '</div>' +
      '</div>';
    }).join('');

    document.getElementById('relatedGrid').innerHTML = html;
    document.getElementById('relatedSection').style.display = '';
  }

  function renderError() {
    document.getElementById('loadingIndicator').style.display = 'none';
    document.getElementById('errorState').style.display = '';
  }

  // ---- 分享功能 ----
  function handleShare() {
    var url = window.location.href;
    var title = document.title;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function () {});
    } else {
      // 降级：复制链接到剪贴板
      var textarea = document.createElement('textarea');
      textarea.value = url;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        showToast('链接已复制到剪贴板', 'success');
      } catch (e) {
        showToast('复制失败，请手动复制地址栏链接', 'info');
      }
      document.body.removeChild(textarea);
    }
  }

  // ---- 初始化 ----
  async function init() {
    var articleId = getArticleId();
    if (!articleId) {
      renderError();
      return;
    }

    try {
      var res = await fetchArticleDetail(articleId);
      if (!res.success) {
        renderError();
        return;
      }
      renderArticle(res.data);
      renderRelated(res.data.related);
    } catch (err) {
      console.error('加载文章详情失败:', err);
      renderError();
    }

    // 分享按钮
    var btnShare = document.getElementById('btnShare');
    if (btnShare) {
      btnShare.addEventListener('click', handleShare);
    }

    // 收藏按钮
    var btnFav = document.getElementById('btnFavorite');
    if (btnFav && articleId) {
      btnFav.addEventListener('click', function () { handleFavorite(articleId); });
    }

    // 监听登录状态变化，重新检查收藏
    document.addEventListener('auth:stateChanged', function () {
      if (articleId) checkFavoriteStatus(articleId);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
