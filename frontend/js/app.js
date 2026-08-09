/**
 * TechNews 资讯聚合网站 - 首页逻辑
 * 处理资讯列表、筛选、搜索、主题切换、分页等
 * 支持 SSR 预渲染数据降级、URL 状态同步、事件委托
 */

(function () {
  'use strict';

  // ---- 状态管理 ----
  const state = {
    category: 'all',
    search: '',
    sort: 'latest',
    page: 1,
    limit: 20,
    totalPages: 1,
    totalArticles: 0,
    ssrReady: false // 标记 SSR 数据是否已消费
  };

  // ---- DOM 元素 ----
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    navTabs: $$('.nav-tab'),
    searchInput: $('#searchInput'),
    sortBtns: $$('.sort-btn'),
    articleGrid: $('#articleGrid'),
    hotSection: $('#hotSection'),
    hotScroll: $('#hotScroll'),
    hotPrev: $('.hot-scroll-prev'),
    hotNext: $('.hot-scroll-next'),
    pagination: $('#pagination'),
    toast: $('#toast')
  };

  // ---- 工具函数 ----
  function formatTime(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return diffMin + ' 分钟前';
    if (diffHr < 24) return diffHr + ' 小时前';
    if (diffDay < 7) return diffDay + ' 天前';
    return dateStr.slice(0, 10);
  }

  function formatNumber(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + 'w';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return n.toString();
  }

  function getPlatformColor(platform) {
    const map = { youtube: '#FF0000', tiktok: '#000000', github: '#6e5494', hackernews: '#FF6600', bilibili: '#00A1D6', blog: '#0ea5e9', reddit: '#FF4500' };
    return map[platform] || '#64748b';
  }

  function getPlatformIcon(platform) {
    const map = { youtube: 'YT', tiktok: 'TT', github: 'GH', hackernews: 'HN', bilibili: 'BL', blog: 'BG', reddit: 'RD' };
    return map[platform] || '##';
  }

  function getPlatformName(platform) {
    const map = { youtube: 'YouTube', tiktok: 'TikTok', github: 'GitHub', hackernews: 'Hacker News', bilibili: 'Bilibili', blog: 'Blog', reddit: 'Reddit' };
    return map[platform] || platform;
  }

  function getCategoryName(cat) {
    const map = { tech: '科技', ai: 'AI', opensource: '开源' };
    return map[cat] || cat;
  }

  function showToast(msg, type) {
    type = type || 'info';
    const toast = dom.toast;
    toast.textContent = msg;
    toast.className = 'toast ' + type + ' show';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.classList.remove('show');
    }, 2500);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ---- URL 状态同步 ----
  function syncUrlState() {
    const params = new URLSearchParams();
    if (state.category && state.category !== 'all') {
      params.set('category', state.category);
    }
    if (state.search) {
      params.set('search', state.search);
    }
    if (state.sort && state.sort !== 'latest') {
      params.set('sort', state.sort);
    }
    if (state.page > 1) {
      params.set('page', String(state.page));
    }
    const queryString = params.toString();
    const newUrl = window.location.pathname + (queryString ? '?' + queryString : '');
    history.pushState({ category: state.category, search: state.search, sort: state.sort, page: state.page }, '', newUrl);
  }

  function restoreFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const category = params.get('category') || 'all';
    const search = params.get('search') || '';
    const sort = params.get('sort') || 'latest';
    const page = parseInt(params.get('page'), 10) || 1;

    state.category = category;
    state.search = search;
    state.sort = sort;
    state.page = page;

    // 同步 UI
    dom.navTabs.forEach(function (tab) {
      const isActive = tab.dataset.category === category;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      if (isActive) {
        tab.setAttribute('aria-current', 'page');
      } else {
        tab.removeAttribute('aria-current');
      }
    });

    dom.sortBtns.forEach(function (btn) {
      const isActive = btn.dataset.sort === sort;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    if (search) {
      dom.searchInput.value = search;
    }
  }

  // 监听浏览器前进/后退
  window.addEventListener('popstate', function (e) {
    if (e.state) {
      state.category = e.state.category || 'all';
      state.search = e.state.search || '';
      state.sort = e.state.sort || 'latest';
      state.page = e.state.page || 1;

      // 同步 UI
      dom.navTabs.forEach(function (tab) {
        const isActive = tab.dataset.category === state.category;
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      dom.sortBtns.forEach(function (btn) {
        const isActive = btn.dataset.sort === state.sort;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });
      dom.searchInput.value = state.search;

      // 热门推荐不受筛选影响，只重新加载文章列表
      loadArticles();
    }
  });

  // ---- API 调用 ----
  async function fetchHomeData() {
    const params = new URLSearchParams({
      category: state.category,
      search: state.search,
      sort: state.sort,
      page: String(state.page),
      limit: String(state.limit)
    });
    const resp = await fetch('/api/home?' + params);
    if (!resp.ok) throw new Error('网络请求失败');
    return resp.json();
  }

  async function fetchArticles() {
    const params = new URLSearchParams({
      category: state.category,
      search: state.search,
      sort: state.sort,
      page: String(state.page),
      limit: String(state.limit)
    });
    const resp = await fetch('/api/articles?' + params);
    if (!resp.ok) throw new Error('网络请求失败');
    return resp.json();
  }

  async function fetchHotArticles() {
    const resp = await fetch('/api/articles/hot?limit=10');
    if (!resp.ok) throw new Error('网络请求失败');
    return resp.json();
  }

  async function recordView(articleId) {
    try {
      await fetch('/api/articles/' + articleId + '/view', { method: 'POST' });
    } catch (e) { /* 静默失败 */ }
  }

  // ---- 渲染函数 ----
  function renderArticleCard(article) {
    const platformColor = getPlatformColor(article.source_platform);
    const platformIcon = getPlatformIcon(article.source_platform);
    const platformName = getPlatformName(article.source_platform);
    const timeStr = formatTime(article.published_at);
    const safeUrl = escapeHtml(article.source_url || '#');
    const detailUrl = '/article/' + article.id;

    return '<div class="article-card" data-id="' + article.id + '">' +
      '<div class="card-header">' +
        '<span class="platform-badge" style="background: ' + platformColor + '">' +
          platformIcon + ' ' + escapeHtml(platformName) +
        '</span>' +
        '<span class="category-tag ' + article.category + '">' + getCategoryName(article.category) + '</span>' +
        '<button class="fav-btn" data-fav-id="' + article.id + '" title="收藏" aria-label="收藏文章">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>' +
        '</button>' +
      '</div>' +
      '<a href="' + detailUrl + '" class="article-title-link" data-id="' + article.id + '">' +
        '<h3 class="article-title">' + escapeHtml(article.title) + '</h3>' +
      '</a>' +
      '<p class="article-summary">' + escapeHtml(article.summary || '暂无摘要') + '</p>' +
      '<div class="article-meta">' +
        (article.author ? '<span class="meta-item">by ' + escapeHtml(article.author) + '</span>' : '') +
        '<span class="meta-item">' + timeStr + '</span>' +
        (article.view_count > 0 ? '<span class="meta-item">' + formatNumber(article.view_count) + ' views</span>' : '') +
      '</div>' +
      '<div class="article-actions">' +
        '<a href="' + detailUrl + '" class="btn-source">阅读详情</a>' +
        '<a href="' + safeUrl + '" target="_blank" rel="noopener" class="btn-external" data-id="' + article.id + '">查看原文</a>' +
      '</div>' +
    '</div>';
  }

  function renderHotCard(article) {
    const platformColor = getPlatformColor(article.source_platform);
    const platformIcon = getPlatformIcon(article.source_platform);
    const platformName = getPlatformName(article.source_platform);
    const timeStr = formatTime(article.published_at);
    const safeUrl = escapeHtml(article.source_url || '#');

    return '<a href="' + safeUrl + '" target="_blank" rel="noopener" class="hot-card">' +
      '<span class="hot-badge">HOT</span>' +
      '<span class="hot-platform-badge" style="background: ' + platformColor + '">' +
        platformIcon + ' ' + escapeHtml(platformName) +
      '</span>' +
      '<h4 class="hot-title">' + escapeHtml(article.title) + '</h4>' +
      '<div class="hot-meta">' +
        '<span>' + getCategoryName(article.category) + '</span>' +
        '<span>·</span>' +
        '<span>' + timeStr + '</span>' +
      '</div>' +
    '</a>';
  }

  function renderPagination() {
    if (state.totalPages <= 1) {
      dom.pagination.innerHTML = '';
      return;
    }

    var html = '';
    var disabledPrev = state.page <= 1 ? ' disabled' : '';
    html += '<button class="page-btn" data-page="' + (state.page - 1) + '"' + disabledPrev + '>← 上一页</button>';

    var startPage = Math.max(1, state.page - 2);
    var endPage = Math.min(state.totalPages, state.page + 2);

    if (startPage > 1) {
      html += '<button class="page-btn" data-page="1">1</button>';
      if (startPage > 2) html += '<span class="page-ellipsis">...</span>';
    }

    for (var i = startPage; i <= endPage; i++) {
      var cls = i === state.page ? 'page-btn active' : 'page-btn';
      html += '<button class="' + cls + '" data-page="' + i + '" aria-current="page">' + i + '</button>';
    }

    if (endPage < state.totalPages) {
      if (endPage < state.totalPages - 1) html += '<span class="page-ellipsis">...</span>';
      html += '<button class="page-btn" data-page="' + state.totalPages + '">' + state.totalPages + '</button>';
    }

    var disabledNext = state.page >= state.totalPages ? ' disabled' : '';
    html += '<button class="page-btn" data-page="' + (state.page + 1) + '"' + disabledNext + '>下一页 →</button>';

    dom.pagination.innerHTML = html;
  }

  function renderEmpty() {
    var hint = state.search
      ? '试试换个关键词，或切换其他分类查看'
      : '正在从 GitHub、Hacker News、Bilibili 等平台抓取最新资讯，请稍后刷新';
    dom.articleGrid.innerHTML =
      '<div class="empty-state">' +
        '<div class="empty-icon">--</div>' +
        '<div class="empty-text">' + (state.search ? '没有找到相关资讯' : '暂无资讯') + '</div>' +
        '<div class="empty-hint">' + hint + '</div>' +
        (state.search ? '<button class="btn-retry" data-action="clear-search">清除搜索</button>' : '<button class="btn-retry" data-action="retry">刷新一下</button>') +
      '</div>';
  }

  function renderError(msg) {
    dom.articleGrid.innerHTML =
      '<div class="error-state">' +
        '<div class="empty-icon">!</div>' +
        '<div class="error-text">' + escapeHtml(msg || '加载失败') + '</div>' +
        '<button class="btn-retry" data-action="retry">重新加载</button>' +
      '</div>';
  }

  function renderLoading() {
    dom.articleGrid.innerHTML =
      '<div class="loading-indicator">' +
        '<div class="spinner"></div>' +
        '<div>正在加载最新资讯...</div>' +
      '</div>';
  }

  // ---- 数据加载 ----

  /**
   * 合并加载：一次性获取文章列表 + 热门推荐，减少首屏请求数
   */
  async function loadHomeData() {
    renderLoading();
    try {
      const res = await fetchHomeData();
      if (!res.success) throw new Error('API 返回错误');

      const data = res.data;
      // 处理文章列表
      const articlesData = data.articles;
      state.totalArticles = articlesData.total;
      state.totalPages = articlesData.total_pages;

      if (articlesData.articles.length === 0) {
        renderEmpty();
      } else {
        dom.articleGrid.innerHTML = articlesData.articles.map(renderArticleCard).join('');
      }
      renderPagination();

      // 处理热门推荐
      const hotArticles = data.hot;
      if (!hotArticles || hotArticles.length === 0) {
        dom.hotSection.style.display = 'none';
      } else {
        dom.hotSection.style.display = '';
        dom.hotScroll.innerHTML = hotArticles.map(renderHotCard).join('');
      }
    } catch (err) {
      console.error('加载首页数据失败:', err);
      renderError(err.message);
      dom.hotSection.style.display = 'none';
    }
  }

  async function loadArticles() {
    // 如果 SSR 已提供当前页数据，直接使用
    if (state.ssrReady) {
      state.ssrReady = false; // 消费一次后清除
      return;
    }

    renderLoading();
    try {
      const res = await fetchArticles();
      if (!res.success) throw new Error('API 返回错误');

      const data = res.data;
      state.totalArticles = data.total;
      state.totalPages = data.total_pages;

      if (data.articles.length === 0) {
        renderEmpty();
      } else {
        dom.articleGrid.innerHTML = data.articles.map(renderArticleCard).join('');
      }
      renderPagination();
    } catch (err) {
      console.error('加载文章失败:', err);
      renderError(err.message);
    }
  }

  async function loadHotArticles() {
    try {
      const res = await fetchHotArticles();
      if (!res.success || res.data.length === 0) {
        dom.hotSection.style.display = 'none';
        return;
      }
      dom.hotSection.style.display = '';
      dom.hotScroll.innerHTML = res.data.map(renderHotCard).join('');
    } catch (err) {
      dom.hotSection.style.display = 'none';
    }
  }

  function goToPage(page) {
    if (page < 1 || page > state.totalPages || page === state.page) return;
    state.page = page;
    syncUrlState();
    loadArticles();

    // 翻页时平滑滚动到内容区顶部（而非页面顶部）
    const contentTop = dom.articleGrid.getBoundingClientRect().top + window.scrollY - 80;
    window.scrollTo({ top: contentTop, behavior: 'smooth' });
  }

  // ---- 事件处理 ----
  function setCategory(category) {
    if (category === state.category) return;
    state.category = category;
    state.page = 1;
    // 注意：不再清除搜索词，保留用户筛选

    dom.navTabs.forEach(function (tab) {
      const isActive = tab.dataset.category === category;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      if (isActive) {
        tab.setAttribute('aria-current', 'page');
      } else {
        tab.removeAttribute('aria-current');
      }
    });

    syncUrlState();
    loadArticles();
  }

  function setSort(sort) {
    if (sort === state.sort) return;
    state.sort = sort;
    state.page = 1;

    dom.sortBtns.forEach(function (btn) {
      const isActive = btn.dataset.sort === sort;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    syncUrlState();
    loadArticles();
  }

  function handleSearch() {
    const query = dom.searchInput.value.trim();
    if (query === state.search) return;
    state.search = query;
    state.page = 1;
    syncUrlState();
    loadArticles();
  }

  // ---- 事件绑定（事件委托） ----

  // 防抖搜索
  let searchTimer;
  dom.searchInput.addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(handleSearch, 400);
  });
  dom.searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      clearTimeout(searchTimer);
      handleSearch();
    }
  });

  // 分类切换
  dom.navTabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      setCategory(tab.dataset.category);
    });
  });

  // 排序切换
  dom.sortBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      setSort(btn.dataset.sort);
    });
  });

  // 分页：事件委托
  dom.pagination.addEventListener('click', function (e) {
    const btn = e.target.closest('.page-btn');
    if (btn && !btn.disabled) {
      const page = parseInt(btn.dataset.page, 10);
      if (!isNaN(page)) goToPage(page);
    }
  });

  // 错误重试 + 清除搜索：事件委托
  dom.articleGrid.addEventListener('click', function (e) {
    var retryBtn = e.target.closest('[data-action="retry"]');
    var clearBtn = e.target.closest('[data-action="clear-search"]');
    if (retryBtn) {
      loadArticles();
    } else if (clearBtn) {
      dom.searchInput.value = '';
      state.search = '';
      state.page = 1;
      syncUrlState();
      loadArticles();
    }
  });

  // 文章卡片浏览计数：事件委托
  dom.articleGrid.addEventListener('click', function (e) {
    const link = e.target.closest('[data-id]');
    if (link) {
      const id = parseInt(link.dataset.id, 10);
      if (!isNaN(id)) recordView(id);
    }
  });

  // 收藏按钮：事件委托
  dom.articleGrid.addEventListener('click', function (e) {
    var favBtn = e.target.closest('.fav-btn');
    if (!favBtn) return;
    e.preventDefault();
    e.stopPropagation();

    var articleId = parseInt(favBtn.dataset.favId, 10);
    if (isNaN(articleId)) return;

    var isFavorited = favBtn.classList.contains('active');

    if (!window.TechNewsAuth || !window.TechNewsAuth.isLoggedIn()) {
      window.TechNewsAuthModal.open('login');
      return;
    }

    favBtn.disabled = true;
    window.TechNewsAuth.toggleFavorite(articleId, isFavorited).then(function (res) {
      favBtn.disabled = false;
      if (res.success) {
        favBtn.classList.toggle('active', res.data.favorited);
      } else if (res.needLogin) {
        window.TechNewsAuthModal.open('login');
      }
    });
  });

  // 热门卡片浏览计数：事件委托
  if (dom.hotScroll) {
    dom.hotScroll.addEventListener('click', function (e) {
      const card = e.target.closest('[data-id]');
      if (card) {
        const id = parseInt(card.dataset.id, 10);
        if (!isNaN(id)) recordView(id);
      }
    });
  }

  // 热门滚动导航按钮
  if (dom.hotPrev) {
    dom.hotPrev.addEventListener('click', function () {
      dom.hotScroll.scrollBy({ left: -320, behavior: 'smooth' });
    });
  }
  if (dom.hotNext) {
    dom.hotNext.addEventListener('click', function () {
      dom.hotScroll.scrollBy({ left: 320, behavior: 'smooth' });
    });
  }

  // ---- SSR 数据消费 ----
  function consumeSSRData() {
    const ssrEl = document.getElementById('ssr-data');
    if (!ssrEl || !ssrEl.textContent.trim()) return false;

    try {
      const data = JSON.parse(ssrEl.textContent);
      // 初始化状态
      state.totalArticles = data.total || 0;
      state.totalPages = data.total_pages || 1;
      state.page = data.page || 1;
      state.category = data.category || 'all';
      state.sort = data.sort || 'latest';
      state.search = data.search || '';
      state.ssrReady = true;

      // SSR 已渲染了 HTML，只需更新分页状态
      renderPagination();

      // 如果有 URL 参数覆盖了 SSR 状态（如用户从书签进入带筛选条件），则重新加载
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('category') || urlParams.get('search') || urlParams.get('sort') || urlParams.get('page')) {
        restoreFromUrl();
        state.ssrReady = false;
        return false;
      }

      return true;
    } catch (e) {
      console.warn('SSR 数据解析失败，降级为 CSR:', e);
      return false;
    }
  }

  // ---- 启动 ----
  function init() {
    // 尝试消费 SSR 数据
    const ssrOk = consumeSSRData();

    if (ssrOk) {
      // SSR 数据有效，不需要额外请求
      console.log('✅ SSR 预渲染数据已就绪');
    } else {
      // 降级为 CSR：从 URL 恢复状态后用合并接口一次性加载
      restoreFromUrl();
      loadHomeData();
    }
  }

  // DOM 就绪后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  console.log('TechNews ready');
})();
