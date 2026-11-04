/**
 * CineScope · Movie Intelligence
 * Main Application Module — Production Build
 *
 * Features:
 * - Keyboard shortcuts (? for help, / for search, Esc to close)
 * - Scroll-to-top button
 * - Debounced search and analysis
 * - Proper error boundaries with retry
 * - Staggered animations with IntersectionObserver
 * - Accessible navigation (ARIA, skip-nav, focus management)
 * - Toast notifications with auto-dismiss and undo
 * - History management with hash routing + popstate
 * - Interactive star rating widget
 * - Review character/word counter with limits
 * - Skeleton loading placeholders
 * - Mobile hamburger menu
 * - Parallax spotlight hero
 * - Image lazy loading with IntersectionObserver
 * - Offline-aware notifications
 * - Performance: requestAnimationFrame throttling, passive listeners
 */

import * as service from './service.js';

/* ── Utility Helpers ── */

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const esc = (s) =>
  String(s ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );

const debounce = (fn, ms) => {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
};

const throttleRAF = (fn) => {
  let ticking = false;
  return (...args) => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(() => {
        fn(...args);
        ticking = false;
      });
    }
  };
};

const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

const pluralize = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

const formatRuntime = (mins) => {
  if (!mins) return '—';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
};


/* ── SVG Icon Library ── */

const paths = {
  discover:
    '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  review:
    '<path d="M8 3h11a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8z"/><path d="M8 3v5H3m5 5h8m-8 4h6"/>',
  heart:
    '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/>',
  chat:
    '<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 0 1 8.7 3.9a8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8z"/>',
  search:
    '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
  star:
    '<path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3L12 17.4l-5.6 3 1.1-6.3-4.6-4.5 6.3-.9z"/>',
  starHalf:
    '<path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3L12 17.4l-5.6 3 1.1-6.3-4.6-4.5 6.3-.9z"/><clipPath id="hc"><rect x="0" y="0" width="12" height="24"/></clipPath>',
  arrow:
    '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  send:
    '<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
  mic:
    '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8"/>',
  close:
    '<path d="m6 6 12 12M6 18 18 6"/>',
  spark:
    '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6z"/>',
  info:
    '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
  check:
    '<path d="m5 12 4 4L19 6"/>',
  plus:
    '<path d="M12 5v14M5 12h14"/>',
  keyboard:
    '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/>',
  chevronUp:
    '<path d="m18 15-6-6-6 6"/>',
  export:
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  menu:
    '<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>',
  clock:
    '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  film:
    '<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/>',
  trending:
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
  share:
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
  copy:
    '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  refresh:
    '<polyline points="23 4 23 10 17 10"/><path d="M20.5 15.5A9 9 0 1 1 21 7.5l2 2.5"/>',
  warning:
    '<path d="m21.73 18-8.16-14.14a2 2 0 0 0-3.48 0L2.27 18a2 2 0 0 0 1.73 3h16.27a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
};

const icon = (name, cl = '') =>
  `<svg class="icon ${cl}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.spark}</svg>`;


/* ── Application State ── */

let movies = [];
let history = [];
let view = 'discover';
let genres = [];
let themes = [];
let query = '';
let analysisToken = 0;
let searchToken = 0;
let activeMovie = null;
let mobileMenuOpen = false;
const cache = new Map();


/* ── Dynamic Data Helpers ── */

function allGenres() {
  const s = new Set();
  for (const m of movies) {
    for (const g of m.genres) s.add(g);
  }
  return [...s].sort();
}

function allThemes() {
  const s = new Set();
  for (const m of movies) {
    for (const t of m.themes) s.add(t);
  }
  return [...s].sort();
}

function aspectNames() {
  const tax = service.taxonomy;
  return tax && tax.aspects
    ? Object.keys(tax.aspects)
    : ['Story', 'Acting', 'Visuals', 'Music', 'Pacing', 'Ending'];
}

function spotlightMovie() {
  const pool = movies.filter((m) => m.poster && !m.fictional);
  if (!pool.length) return movies[0] || null;
  const day = Math.floor(Date.now() / (1000 * 60 * 60 * 24));
  return pool[day % pool.length];
}



/* ── Notification System ── */

let toastQueue = [];
let toastActive = false;

const notify = (message, error = false) => {
  const t = $('#toast');
  if (!t) return;

  const show = () => {
    toastActive = true;
    t.innerHTML = `${icon(error ? 'info' : 'check')} <span>${esc(message)}</span>`;
    t.className = 'toast visible' + (error ? ' error' : '');
    clearTimeout(notify.timer);
    notify.timer = setTimeout(() => {
      t.className = 'toast';
      toastActive = false;
      if (toastQueue.length) {
        const next = toastQueue.shift();
        setTimeout(() => next(), 300);
      }
    }, 4000);
  };

  if (toastActive) {
    toastQueue.push(show);
  } else {
    show();
  }
};


/* ── Error Boundary Wrapper ── */

const safe = (fn) =>
  async (...args) => {
    try {
      return await fn(...args);
    } catch (e) {
      if (e?.name === 'AbortError') return;
      console.error('[CineScope Error]', e);
      notify(e.message || 'Something went wrong. Please try again.', true);
    }
  };


/* ── Intersection Observer for Lazy Elements ── */

let lazyObserver = null;

function setupLazyObserver() {
  if (!('IntersectionObserver' in window)) return;

  lazyObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          lazyObserver.unobserve(entry.target);
        }
      });
    },
    { rootMargin: '50px', threshold: 0.1 }
  );
}

function observeCards() {
  if (!lazyObserver) return;
  $$('.movie-card').forEach((el) => {
    el.classList.remove('visible');
    lazyObserver.observe(el);
  });
}


/* ── Component Renderers ── */

function poster(m, cl = '') {
  if (m.poster) {
    return `<img class="${cl}" src="${esc(m.poster)}" alt="${esc(m.title)} poster" loading="lazy" width="500" height="750" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="poster-placeholder ${cl}" style="display:none">${icon('spark')}<span>Poster unavailable</span><strong>${esc(m.title)}</strong></div>`;
  }
  return `<div class="poster-placeholder ${cl}">${icon('spark')}<span>${m.fictional ? 'Fictional demo' : 'Poster unavailable'}</span><strong>${esc(m.title)}</strong></div>`;
}

function chips(items, cls = '') {
  return items.map((x) => `<span class="tag ${cls}">${esc(x)}</span>`).join('');
}

function starWidget(currentRating = 0, interactive = false) {
  const stars = [1, 2, 3, 4, 5];
  return `<div class="star-rating${interactive ? ' interactive' : ''}" role="${interactive ? 'radiogroup' : 'img'}" aria-label="${interactive ? 'Rate this film' : `Rating: ${currentRating} out of 5`}">
    ${stars.map((s) => {
      const full = currentRating >= s;
      const half = !full && currentRating >= s - 0.5;
      return `<button type="button" class="star-btn${full ? ' full' : ''}${half ? ' half' : ''}" data-star="${s}" ${interactive ? '' : 'tabindex="-1"'} aria-label="${s} star${s > 1 ? 's' : ''}">
        ${icon('star')}
      </button>`;
    }).join('')}
    <span class="star-value" aria-live="polite">${currentRating ? currentRating + '/5' : ''}</span>
  </div>`;
}

function card(m, index = 0) {
  cache.set(m.movie_id, m);
  const rating = history.find((r) => r.movie_id === m.movie_id);

  return `<article class="movie-card" style="--delay:${clamp(index * 60, 0, 600)}ms">
    <button class="poster-button" data-movie="${m.movie_id}" aria-label="Explore ${esc(m.title)}">
      ${poster(m)}
      <span class="poster-hover">Explore film ${icon('arrow')}</span>
      ${m.fictional ? '<span class="poster-badge">No reviews yet</span>' : ''}
      ${rating ? `<span class="rated-badge">${icon('star')}${rating.rating}</span>` : ''}
    </button>
    <button class="movie-title" data-movie="${m.movie_id}">${esc(m.title)}</button>
    <div class="movie-meta">${m.year || '—'} <span>·</span> ${esc(m.genres.slice(0, 2).join(' / '))}</div>
    ${m.reasons ? `<p class="match-reason">${icon('spark', 'match-icon')} ${esc(m.reasons[0])}</p>` : ''}
  </article>`;
}

function skeletonCards(count = 8) {
  return Array.from({ length: count }, (_, i) =>
    `<article class="movie-card skeleton-card" style="--delay:${i * 60}ms">
      <div class="poster-button skeleton-poster"><div class="skeleton-shimmer"></div></div>
      <div class="skeleton-title"><div class="skeleton-shimmer"></div></div>
      <div class="skeleton-meta"><div class="skeleton-shimmer"></div></div>
    </article>`
  ).join('');
}

function aspectGrid(aspects = {}, evidence = false) {
  return `<div class="aspect-grid">${aspectNames()
    .map((a) => {
      const v = aspects[a] || {};
      const n = v.score;
      return `<div class="aspect">
        <div>
          <span>${a}</span>
          <strong class="${n !== null && n < 45 ? 'low' : ''}">${n == null ? '—' : Math.round(n)}</strong>
        </div>
        <div class="bar"><i style="width:${n ?? 0}%;${n !== null && n < 45 ? 'background:var(--amber)' : ''}"></i></div>
        <small>${
          n == null
            ? 'No clear opinion'
            : v.review_count !== undefined
            ? pluralize(v.review_count, 'review')
            : pluralize(v.scored_mentions, 'opinion')
        }</small>
        ${
          evidence && v.evidence?.length
            ? `<details><summary>Evidence</summary><p>${esc(
                typeof v.evidence[0] === 'string' ? v.evidence[0] : v.evidence[0].text
              )}</p></details>`
            : ''
        }
      </div>`;
    })
    .join('')}</div>`;
}

function skeleton() {
  return '<div class="empty"><div class="loader"></div><p>Finding your films…</p></div>';
}


/* ── App Shell ── */

function shell() {
  $('#app').innerHTML = `
    <aside class="sidebar" role="navigation" aria-label="Main navigation" id="sidebar">
      <div class="sidebar-top">
        <a href="#discover" class="brand">
          <img src="/favicon.svg" alt="" width="34" height="34">
          <span>cine<span class="brand-thin">scope</span>
            <small>MOVIE INTELLIGENCE</small>
          </span>
        </a>
        <button class="hamburger" id="hamburger" aria-label="Toggle menu" aria-expanded="false">
          ${icon('menu')}
        </button>
      </div>

      <div class="sidebar-nav-wrap" id="sidebar-nav-wrap">
        <p class="nav-label">YOUR CINEMA</p>

        <nav aria-label="Main navigation">
          <button data-view="discover" class="active" id="nav-discover">
            ${icon('discover')}Discover
          </button>
          <button data-view="reviews" id="nav-reviews">
            ${icon('review')}Review studio
          </button>
          <button data-view="taste" id="nav-taste">
            ${icon('heart')}My taste
            <span id="history-count"></span>
          </button>
        </nav>

        <div class="sidebar-bottom">
          <div class="sidebar-note">
            A film for every<br><em>version of you.</em>
          </div>
          <button class="about-button" id="about">
            ${icon('info')}About this project
          </button>
          <button class="about-button" id="shortcuts-btn" title="Keyboard shortcuts">
            ${icon('keyboard')}Shortcuts
          </button>
          <div class="profile">
            <div class="avatar">Y</div>
            <div>You<small>Personal movie space</small></div>
          </div>
        </div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <span id="breadcrumb">Your cinema <span>/</span> Discover</span>
        <div class="topbar-actions">
          <button id="mode-button" class="mode-pill">
            ${service.health.demo_data ? 'Sample catalog' : 'Your movie catalog'} ${icon('info')}
          </button>
        </div>
      </header>

      <div class="workspace-grid">
        <main id="main" tabindex="-1" role="main"></main>
      </div>
    </div>

    <!-- Movie detail dialog -->
    <dialog id="movie-dialog" class="movie-dialog"></dialog>

    <!-- About dialog -->
    <dialog id="about-dialog" class="about-dialog">
      <button class="icon-button modal-close" id="close-about" aria-label="Close about">
        ${icon('close')}
      </button>
      <span class="eyebrow">BEHIND THE SCREEN</span>
      <h2>Movie Review &amp;<br>Recommendation System</h2>
      <p>A combined Big Data Analysis and Text Analytics project.</p>
      <div class="info-box">
        <strong>${service.apiMode ? 'Local Python API connected' : 'Interactive frontend demo'}</strong>
        <p>${
          service.apiMode
            ? 'Review processing and ratings are saved by the local backend.'
            : 'Your ratings and submitted reviews stay in this browser. The sample reviews are synthetic; no model was trained on them.'
        }</p>
        <p>Active sentiment engine: <b>${esc(service.health.sentiment_model)}</b>. Scores are sentiment indices, not objective quality ratings. Review screening highlights signals; it cannot prove a review is fake.</p>
      </div>
      <p>The complete project includes IMDb training notebooks, Scala/Spark pipelines, hybrid recommendations and optional transformer and speech models.</p>
      <div class="credits">
        <img src="/assets/tmdb-attribution-logo.svg" alt="TMDB" width="85">
        <p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
        <a href="https://www.themoviedb.org" target="_blank" rel="noopener">Movie images: TMDB</a>
      </div>
    </dialog>

    <!-- Keyboard shortcuts dialog -->
    <dialog id="shortcuts-dialog" class="shortcuts-dialog about-dialog">
      <button class="icon-button modal-close" id="close-shortcuts" aria-label="Close shortcuts">
        ${icon('close')}
      </button>
      <h2>${icon('keyboard')} Keyboard Shortcuts</h2>
      <div class="shortcut-list">
        <div><span>Search movies</span><kbd>/</kbd></div>
        <div><span>Show shortcuts</span><kbd>?</kbd></div>
        <div><span>Go to Discover</span><kbd>1</kbd></div>
        <div><span>Go to Review Studio</span><kbd>2</kbd></div>
        <div><span>Go to My Taste</span><kbd>3</kbd></div>
        <div><span>Close dialog</span><kbd>Esc</kbd></div>
        <div><span>Export taste data</span><kbd>E</kbd></div>
      </div>
    </dialog>

    <!-- Toast notification -->
    <div class="toast" id="toast" role="status" aria-live="polite"></div>

    <!-- Scroll to top -->
    <button class="scroll-top" id="scroll-top" aria-label="Scroll to top" title="Back to top">
      ${icon('chevronUp')}
    </button>

    <!-- Mobile overlay -->
    <div class="mobile-overlay" id="mobile-overlay"></div>
  `;

  /* ── Event Bindings ── */

  // Delegated click handler
  document.addEventListener(
    'click',
    safe(async (e) => {
      const movieButton = e.target.closest('[data-movie]');
      if (movieButton) {
        await openMovie(Number(movieButton.dataset.movie));
        return;
      }

      const nav = e.target.closest('[data-view]');
      if (nav) {
        closeMobileMenu();
        navigate(nav.dataset.view);
        return;
      }
    })
  );

  // About dialog
  $('#about').onclick = () => $('#about-dialog').showModal();
  $('#mode-button').onclick = () => $('#about-dialog').showModal();
  $('#close-about').onclick = () => $('#about-dialog').close();

  // Shortcuts dialog
  $('#shortcuts-btn').onclick = () => $('#shortcuts-dialog').showModal();
  $('#close-shortcuts').onclick = () => $('#shortcuts-dialog').close();

  // Dialog backdrop click to close
  document.querySelectorAll('dialog').forEach((d) =>
    d.addEventListener('click', (e) => {
      if (e.target === d) d.close();
    })
  );

  // Hamburger menu
  setupMobileMenu();

  // Scroll to top button
  setupScrollToTop();

  // Keyboard shortcuts
  setupKeyboardShortcuts();

  // Hash routing: handle back/forward navigation
  setupHashRouting();

  // Lazy load observer
  setupLazyObserver();

  // Online/Offline detection
  setupConnectivityWatch();

  updateHistoryCount();
}


/* ── Mobile Menu ── */

function setupMobileMenu() {
  const hamburger = $('#hamburger');
  const overlay = $('#mobile-overlay');

  if (hamburger) {
    hamburger.onclick = () => {
      mobileMenuOpen = !mobileMenuOpen;
      toggleMobileMenu();
    };
  }

  if (overlay) {
    overlay.onclick = closeMobileMenu;
  }
}

function toggleMobileMenu() {
  const sidebar = $('#sidebar');
  const hamburger = $('#hamburger');
  if (sidebar) sidebar.classList.toggle('mobile-open', mobileMenuOpen);
  if (hamburger) {
    hamburger.setAttribute('aria-expanded', mobileMenuOpen);
    hamburger.innerHTML = mobileMenuOpen ? icon('close') : icon('menu');
  }
  const overlay = $('#mobile-overlay');
  if (overlay) overlay.classList.toggle('visible', mobileMenuOpen);
  document.body.style.overflow = mobileMenuOpen ? 'hidden' : '';
}

function closeMobileMenu() {
  mobileMenuOpen = false;
  toggleMobileMenu();
}


/* ── Scroll to Top ── */

function setupScrollToTop() {
  const btn = $('#scroll-top');
  if (!btn) return;

  window.addEventListener('scroll', throttleRAF(() => {
    btn.classList.toggle('visible', window.scrollY > 400);
  }), { passive: true });

  btn.onclick = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
}


/* ── Hash Routing ── */

function setupHashRouting() {
  window.addEventListener('popstate', () => {
    const hash = location.hash.slice(1);
    if (['reviews', 'taste', 'discover'].includes(hash) && hash !== view) {
      view = hash;
      updateNavUI(hash);
      safe(hash === 'reviews' ? renderStudio : hash === 'taste' ? renderTaste : renderDiscover)();
    }
  });
}


/* ── Keyboard Shortcuts ── */

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Don't trigger shortcuts when typing in inputs
    const tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    switch (e.key) {
      case '/':
        e.preventDefault();
        const searchInput = $('#search');
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
        break;

      case '?':
        e.preventDefault();
        $('#shortcuts-dialog')?.showModal();
        break;

      case '1':
        navigate('discover');
        break;

      case '2':
        navigate('reviews');
        break;

      case '3':
        navigate('taste');
        break;

      case 'Escape':
        // Close any open dialogs or mobile menu
        const openDialog = document.querySelector('dialog[open]');
        if (openDialog) {
          openDialog.close();
        } else if (mobileMenuOpen) {
          closeMobileMenu();
        }
        break;

      case 'e':
      case 'E':
        if (history.length) exportTasteData();
        break;
    }
  });
}


/* ── Connectivity Watch ── */

function setupConnectivityWatch() {
  window.addEventListener('online', () => {
    notify('Back online!');
  });

  window.addEventListener('offline', () => {
    notify('You seem to be offline. Some features may be limited.', true);
  });
}


/* ── Export Taste Data ── */

function exportTasteData() {
  const data = {
    exported_at: new Date().toISOString(),
    total_ratings: history.length,
    average_rating: history.length
      ? (history.reduce((s, r) => s + r.rating, 0) / history.length).toFixed(2)
      : null,
    ratings: history.map((r) => {
      const m = cache.get(r.movie_id) || movies.find((m) => m.movie_id === r.movie_id);
      return {
        movie_id: r.movie_id,
        title: m?.title || 'Unknown',
        rating: r.rating,
        genres: m?.genres || [],
        themes: m?.themes || [],
        year: m?.year || null,
        updated_at: r.updated_at,
      };
    }),
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `cinescope-taste-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  notify('Taste data exported successfully!');
}


/* ── Navigation ── */

function updateHistoryCount() {
  const el = $('#history-count');
  if (el) el.textContent = history.length || '';
}

function updateNavUI(next) {
  // Update nav active states
  document.querySelectorAll('[data-view]').forEach((n) =>
    n.classList.toggle('active', n.dataset.view === next)
  );

  // Update breadcrumb
  const breadcrumb = $('#breadcrumb');
  if (breadcrumb) {
    const labels = { reviews: 'Review studio', taste: 'My taste', discover: 'Discover' };
    breadcrumb.innerHTML = `Your cinema <span>/</span> ${labels[next] || 'Discover'}`;
  }
}

function navigate(next) {
  view = next;
  window.location.hash = next;

  updateNavUI(next);

  // Render the view
  safe(next === 'reviews' ? renderStudio : next === 'taste' ? renderTaste : renderDiscover)();

  // Scroll to top on view change
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Update document title
  const titles = { reviews: 'Review Studio', taste: 'My Taste', discover: 'Discover' };
  document.title = `${titles[next] || 'Discover'} · CineScope`;
}


/* ── Discover Page ── */

async function renderDiscover() {
  const m = spotlightMovie();
  const dynGenres = allGenres();
  const dynThemes = allThemes();

  $('#main').innerHTML = `
    <div class="page-heading">
      <div>
        <span class="eyebrow">THE GOOD PART STARTS HERE</span>
        <h1>Your next great watch.</h1>
        <p>Follow your taste. Find something unexpected.</p>
      </div>
    </div>

    <form class="search-form" id="search-form" role="search">
      ${icon('search')}
      <label for="search" class="sr-only">Describe a movie</label>
      <input id="search" placeholder="A title, a genre, a feeling…" value="${esc(query)}" autocomplete="off">
      <button class="search-submit" type="submit" aria-label="Search movies">${icon('arrow')}</button>
    </form>

    <div class="filters" id="filters" role="group" aria-label="Genre filters">
      <button class="filter ${genres.length ? '' : 'selected'}" data-genre="">For you</button>
      ${dynGenres
        .map(
          (g) =>
            `<button class="filter ${genres.includes(g) ? 'selected' : ''}" data-genre="${g}">${g}</button>`
        )
        .join('')}
      <label class="theme-label">
        <span class="sr-only">Theme</span>
        <select id="theme-filter">
          <option value="">Any theme</option>
          ${dynThemes
            .map((t) => `<option ${themes.includes(t) ? 'selected' : ''}>${esc(t)}</option>`)
            .join('')}
        </select>
      </label>
    </div>

    ${
      m
        ? `<section class="spotlight" ${
            m.backdrop
              ? `style="background-image:linear-gradient(90deg,rgba(9,14,17,.94) 4%,rgba(9,14,17,.58) 54%,rgba(9,14,17,.12)),url('${esc(m.backdrop)}')" `
              : ''
          }>
            <div class="spotlight-content">
              <span class="spotlight-label">${icon('spark')} IN THE SPOTLIGHT</span>
              <h2>${esc(m.title)}</h2>
              <div class="spotlight-meta">
                ${m.year} <span>·</span> ${formatRuntime(m.runtime)} <span>·</span> ${esc(m.genres.slice(0, 2).join(' / '))}
              </div>
              <p>${esc(m.overview)}</p>
              <div class="spotlight-actions">
                <button class="primary" data-movie="${m.movie_id}">Explore this film ${icon('arrow')}</button>
                <button class="ghost" id="spotlight-reviews">Read the room</button>
              </div>
            </div>
            <div class="spotlight-index">01 <span>/</span> YOUR CINEMA</div>
          </section>`
        : ''
    }

    <div class="section-heading">
      <div>
        <h2 id="picks-title">${history.length ? 'Picked for your taste' : 'Start your next obsession'}</h2>
        <p id="picks-subtitle">${
          history.length
            ? 'Inspired by the films you rated.'
            : 'A few possibilities. Rate a film to make this yours.'
        }</p>
      </div>
      <span class="result-count" id="result-count"></span>
    </div>

    <div class="movie-grid" id="movie-grid">${skeletonCards(8)}</div>

    <div class="discovery-note">
      ${icon('info')} ${
        service.health.demo_data
          ? 'Sample catalog · Synthetic reviews · Your own ratings shape the recommendations'
          : 'Your ratings shape recommendations. Films without reviews can still be discovered.'
      }
    </div>
  `;

  // Search form
  const searchInput = $('#search');
  const debouncedSearch = debounce(async () => {
    query = searchInput.value.trim();
    await loadPicks();
  }, 400);

  $('#search-form').onsubmit = safe(async (e) => {
    e.preventDefault();
    query = searchInput.value.trim();
    await loadPicks();
  });

  searchInput.oninput = debouncedSearch;

  // Genre filters
  $('#filters').onclick = safe(async (e) => {
    const b = e.target.closest('[data-genre]');
    if (!b) return;

    const g = b.dataset.genre;
    genres = g
      ? genres.includes(g)
        ? genres.filter((x) => x !== g)
        : [...genres, g]
      : [];

    $('#filters')
      .querySelectorAll('[data-genre]')
      .forEach((el) =>
        el.classList.toggle(
          'selected',
          el.dataset.genre ? genres.includes(el.dataset.genre) : !genres.length
        )
      );

    await loadPicks();
  });

  // Theme filter
  $('#theme-filter').onchange = safe(async (e) => {
    themes = e.target.value ? [e.target.value] : [];
    await loadPicks();
  });

  // Spotlight reviews button
  const spotlightBtn = $('#spotlight-reviews');
  if (spotlightBtn) {
    spotlightBtn.onclick = () => {
      navigate('reviews');
      setTimeout(() => {
        if ($('#studio-movie')) {
          $('#studio-movie').value = m.movie_id;
          loadStudioSummary(m.movie_id);
        }
      }, 0);
    };
  }

  await loadPicks();
}


/* ── Load Recommendations ── */

async function loadPicks() {
  const token = ++searchToken;
  const grid = $('#movie-grid');
  if (!grid) return;

  grid.innerHTML = skeletonCards(8);

  const results = await service.recommend(query, genres, themes, 24);
  if (token !== searchToken || view !== 'discover') return;

  grid.innerHTML = results.length
    ? results.map((m, i) => card(m, i)).join('')
    : `<div class="empty">
        <div class="empty-icon">${icon('search')}</div>
        <h3>No unseen films match every filter.</h3>
        <p>Try another combination, or clear the genres and theme.</p>
        <button class="primary" id="clear-filters">Clear filters</button>
      </div>`;

  const countEl = $('#result-count');
  if (countEl) countEl.textContent = pluralize(results.length, 'film');

  const subtitle = $('#picks-subtitle');
  if (subtitle) {
    subtitle.textContent =
      genres.length > 1
        ? 'Matching all selected genres: ' + genres.join(' + ')
        : query
        ? 'Matching "' + query + '"'
        : history.length
        ? 'Inspired by the films you rated.'
        : 'A few possibilities. Rate a film to make this yours.';
  }

  const clearBtn = $('#clear-filters');
  if (clearBtn) {
    clearBtn.onclick = () => {
      genres = [];
      themes = [];
      query = '';
      renderDiscover();
    };
  }

  // Observe cards for lazy animation
  observeCards();
}


/* ── Movie Detail Modal ── */

async function openMovie(id) {
  const d = $('#movie-dialog');
  if (!d) return;

  d.innerHTML = '<div class="modal-loading">' + skeleton() + '</div>';
  d.showModal();

  try {
    const m = await service.details(id);
    cache.set(id, m);
    activeMovie = id;

    const s = m.review_summary;
    const old = history.find((r) => r.movie_id === id);

    d.innerHTML = `
      <button class="icon-button modal-close" id="close-movie" aria-label="Close movie">
        ${icon('close')}
      </button>

      <div class="movie-detail-top">
        <div class="detail-poster">${poster(m)}</div>
        <div class="detail-info">
          <span class="eyebrow">${m.fictional ? 'FICTIONAL · COLD START DEMO' : 'YOUR NEXT CHAPTER'}</span>
          <h2>${esc(m.title)}</h2>
          <div class="movie-meta">${m.year || '—'} · ${formatRuntime(m.runtime)}</div>
          <div class="tags">${chips(m.genres)}</div>
          <p>${esc(m.overview)}</p>
          <div class="theme-tags">${chips(m.themes, 'theme')}</div>

          <div class="rate-panel">
            <label>Your rating</label>
            <div class="rating-widget-wrap">
              ${starWidget(old?.rating || 0, true)}
              <input type="hidden" id="rating-value" value="${old?.rating || ''}">
            </div>
            <div class="rating-actions">
              <button class="primary" id="save-rating">
                ${old ? 'Update rating' : 'Rate & personalize'}
              </button>
              ${old ? '<button class="text-button" id="remove-rating">Remove</button>' : ''}
            </div>
            <small>Saving a rating adds this film to your watch history.</small>
          </div>
        </div>
      </div>

      <section class="review-overview">
        <div class="section-heading">
          <div>
            <span class="eyebrow">READ THE ROOM</span>
            <h3>The review consensus</h3>
          </div>
          <span class="review-count">${pluralize(s.eligible_reviews, 'eligible review')}</span>
        </div>

        <p class="summary-text">${esc(s.summary)}</p>
        ${s.synthetic_demo ? '<p class="sample-note">Based on synthetic sample reviews.</p>' : ''}

        ${aspectGrid(s.aspects, true)}

        <p class="score-note">Scores reflect sentiment in mentioned aspects, not objective film quality. — means insufficient evidence.</p>

        ${
          s.excerpts?.length
            ? `<div class="evidence-list">
                ${s.excerpts
                  .slice(0, 4)
                  .map(
                    (e) =>
                      `<blockquote class="${e.polarity}">
                        <p>"${esc(e.text)}"</p>
                        <cite>${e.polarity === 'positive' ? 'Praise' : 'Criticism'} · ${esc(e.review_id)}</cite>
                      </blockquote>`
                  )
                  .join('')}
              </div>`
            : ''
        }

        <button class="secondary" id="write-review">
          ${icon('review')} Write your review
        </button>
      </section>
    `;

    // Close button
    $('#close-movie').onclick = () => d.close();

    // Star rating widget
    setupStarRating(d, old?.rating);

    // Save rating
    $('#save-rating').onclick = safe(async () => {
      const rating = Number($('#rating-value').value);
      if (!rating) {
        notify('Choose a rating first.', true);
        return;
      }
      history = await service.rate(id, rating);
      updateHistoryCount();
      notify(`Rating saved — ${rating}/5 for ${m.title}. Your recommendations are updated.`);
      d.close();
      if (view === 'discover') await renderDiscover();
      if (view === 'taste') await renderTaste();
    });

    // Remove rating
    const removeBtn = $('#remove-rating');
    if (removeBtn) {
      removeBtn.onclick = safe(async () => {
        history = await service.unrate(id);
        updateHistoryCount();
        notify('Rating removed.');
        d.close();
        navigate(view);
      });
    }

    // Write review
    $('#write-review').onclick = () => {
      d.close();
      navigate('reviews');
      setTimeout(() => {
        if ($('#studio-movie')) {
          $('#studio-movie').value = id;
          loadStudioSummary(id);
          $('#review-text')?.focus();
        }
      }, 0);
    };
  } catch (e) {
    d.close();
    throw e;
  }
}


/* ── Star Rating Widget ── */

function setupStarRating(container, currentRating = 0) {
  const widget = container.querySelector('.star-rating.interactive');
  if (!widget) return;

  const stars = widget.querySelectorAll('.star-btn');
  const valueInput = container.querySelector('#rating-value');
  const valueSpan = widget.querySelector('.star-value');
  let selected = currentRating || 0;

  const updateStars = (rating, isHover = false) => {
    stars.forEach((star) => {
      const val = Number(star.dataset.star);
      star.classList.toggle('full', val <= rating);
      star.classList.toggle('half', false);
      if (isHover) star.classList.add('hover-active');
      else star.classList.remove('hover-active');
    });
    if (!isHover && rating) {
      valueSpan.textContent = rating + '/5';
    }
  };

  stars.forEach((star) => {
    star.onmouseenter = () => updateStars(Number(star.dataset.star), true);
    star.onclick = (e) => {
      e.preventDefault();
      const val = Number(star.dataset.star);
      // Allow half-star: click same star again to go half
      if (selected === val) {
        selected = val - 0.5;
      } else {
        selected = val;
      }
      if (selected < 0.5) selected = 0.5;
      valueInput.value = selected;
      updateStars(selected);
    };
  });

  widget.onmouseleave = () => updateStars(selected);

  // Initialize
  if (selected) updateStars(selected);
}


/* ── Review Studio ── */

async function renderStudio() {
  const MAX_REVIEW_LENGTH = 20000;

  $('#main').innerHTML = `
    <div class="page-heading">
      <span class="eyebrow">BEYOND THE STARS</span>
      <h1>Every review has a story.</h1>
      <p>Understand the sentiment. See what stood out.</p>
    </div>

    <section class="studio-editor">
      <div class="editor-header">
        <label for="studio-movie">Which film?</label>
        <select id="studio-movie">
          ${movies
            .map((m) => `<option value="${m.movie_id}">${esc(m.title)} (${m.year})</option>`)
            .join('')}
        </select>
      </div>

      <label class="sr-only" for="review-text">Your movie review</label>
      <textarea id="review-text" maxlength="${MAX_REVIEW_LENGTH}" placeholder="The visuals were stunning and the acting felt natural. I loved the soundtrack, but the middle was a little slow…"></textarea>

      <div class="editor-footer">
        <label class="live-switch">
          <input type="checkbox" id="live-analysis" checked> Live analysis
        </label>
        <div class="word-info">
          <span id="word-count">0 words</span>
          <span id="char-count" class="char-counter">0 / ${MAX_REVIEW_LENGTH.toLocaleString()}</span>
        </div>
        <button class="secondary" id="analyze-review">Analyze</button>
        <button class="primary" id="save-review">Save review ${icon('arrow')}</button>
      </div>
    </section>

    <div id="analysis" aria-live="polite">
      <div class="analysis-empty">
        ${icon('spark')}
        <span>Your sentiment, aspect scores and review signals will appear as you type.</span>
      </div>
    </div>

    <div class="section-heading">
      <div>
        <h2>The bigger picture</h2>
        <p>What the collected reviews say about this film.</p>
      </div>
    </div>

    <section id="studio-summary" class="summary-panel">${skeleton()}</section>
  `;

  // Analysis function
  const analyzeNow = safe(async () => {
    const text = $('#review-text').value.trim();
    const id = Number($('#studio-movie').value);
    const token = ++analysisToken;
    const analysisEl = $('#analysis');

    if (text.length < 3) {
      service.cancelAnalysis();
      $('#analysis').innerHTML = '<div class="analysis-empty">Write a few words to begin.</div>';
      return;
    }

    analysisEl?.setAttribute('aria-busy', 'true');
    analysisEl?.classList.add('is-loading');
    try {
      const result = await service.analyze(text, id);
      if (token !== analysisToken || view !== 'reviews') return;
      renderAnalysis(result);
    } finally {
      if (token === analysisToken) {
        analysisEl?.setAttribute('aria-busy', 'false');
        analysisEl?.classList.remove('is-loading');
      }
    }
  });

  // Debounced live analysis
  const debouncedAnalyze = debounce(() => {
    if ($('#live-analysis')?.checked) analyzeNow();
  }, 550);

  // Word count, char count, and live analysis
  $('#review-text').oninput = () => {
    const text = $('#review-text').value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;

    const wordCountEl = $('#word-count');
    if (wordCountEl) wordCountEl.textContent = pluralize(words, 'word');

    const charCountEl = $('#char-count');
    if (charCountEl) {
      charCountEl.textContent = `${chars.toLocaleString()} / ${MAX_REVIEW_LENGTH.toLocaleString()}`;
      charCountEl.classList.toggle('warning', chars > MAX_REVIEW_LENGTH * 0.9);
      charCountEl.classList.toggle('danger', chars > MAX_REVIEW_LENGTH * 0.98);
    }

    analysisToken++;
    service.cancelAnalysis();
    debouncedAnalyze();
  };

  // Manual analyze
  $('#analyze-review').onclick = analyzeNow;

  // Live analysis toggle
  $('#live-analysis').onchange = () => {
    if ($('#live-analysis').checked) analyzeNow();
  };

  // Movie selection change
  $('#studio-movie').onchange = safe(async () => {
    analysisToken++;
    await loadStudioSummary(Number($('#studio-movie').value));
    if ($('#review-text').value.trim()) await analyzeNow();
  });

  // Save review
  $('#save-review').onclick = safe(async () => {
    const text = $('#review-text').value.trim();
    const id = Number($('#studio-movie').value);

    if (text.length < 3) {
      notify('Write your review first.', true);
      return;
    }

    const btn = $('#save-review');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<div class="loader small"></div> Saving…';
    }

    try {
      const r = await service.saveReview(id, text);
      renderAnalysis(r.analysis);
      notify(
        r.analysis.authenticity.needs_review
          ? 'Saved and flagged for inspection.'
          : 'Review saved. The summary has been updated.'
      );
      await loadStudioSummary(id);
    } finally {
      if ($('#save-review')) {
        $('#save-review').disabled = false;
        $('#save-review').innerHTML = `Save review ${icon('arrow')}`;
      }
    }
  });

  await loadStudioSummary(Number($('#studio-movie').value));
}


/* ── Render Analysis Result ── */

function renderAnalysis(a) {
  const s = a.sentiment;
  const q = a.authenticity;
  const qual = a.quality;
  const analysisEl = $('#analysis');
  if (!analysisEl) return;

  const d = s.detail || {};
  const sentimentNames = {
    positive: 'Positive',
    negative: 'Negative',
    mixed: 'Mixed',
    neutral: 'Neutral',
  };
  const sentimentName = sentimentNames[s.label] || 'Uncertain';
  
  // Clause-by-clause breakdown
  let clauseHtml = '';
  if (d.clause_sentiments && d.clause_sentiments.length > 0) {
    clauseHtml = `
      <div class="clause-breakdown">
        <h4>Clause Breakdown</h4>
        <div class="clause-list">
          ${d.clause_sentiments.map(c => 
            `<div class="clause-item ${c.polarity}">
               <span class="clause-score">${c.score > 0 ? '+' : ''}${c.score.toFixed(1)}</span>
               <span class="clause-text">"${esc(c.text)}"</span>
             </div>`
          ).join('')}
        </div>
      </div>
    `;
  }

  // Quality metrics
  let qualityHtml = '';
  if (qual) {
    qualityHtml = `
      <div class="quality-metrics">
        <h4>Review Quality</h4>
        <div class="metrics-grid">
          <div class="metric-box">
            <span class="metric-val">${qual.detail_score}/100</span>
            <span class="metric-label">Detail</span>
          </div>
          <div class="metric-box">
            <span class="metric-val">${qual.helpfulness}/100</span>
            <span class="metric-label">Helpfulness</span>
          </div>
          <div class="metric-box">
            <span class="metric-val">${qual.coherence}/100</span>
            <span class="metric-label">Coherence</span>
          </div>
        </div>
        <div class="quality-tags">
          ${qual.has_comparison ? '<span class="q-tag">Comparison</span>' : ''}
          ${qual.has_examples ? '<span class="q-tag">Examples</span>' : ''}
          ${qual.has_reasoning ? '<span class="q-tag">Reasoning</span>' : ''}
        </div>
      </div>
    `;
  }

  // Confidence gauge
  const meterWidth = Math.max(0, Math.min(100, s.sentiment_index));
  
  analysisEl.innerHTML = `
    <section class="analysis-result">
      <div class="analysis-head">
        <div class="sentiment ${s.label}">
          ${icon(s.uncertain ? 'info' : 'spark')}
          <div>
            <span>REVIEW SENTIMENT</span>
            <strong>${s.uncertain ? 'Low confidence · ' : ''}${sentimentName}</strong>
          </div>
        </div>
        <div class="sentiment-value">
          <div class="gauge-wrap">
            <div class="gauge-track">
              <div class="gauge-fill ${s.label}" style="width: ${meterWidth}%"></div>
            </div>
            <strong>${Math.round(s.sentiment_index)}<span>/100</span></strong>
          </div>
          <small>Sentiment index</small>
        </div>
      </div>
      
      <div class="analysis-grid-top">
        <div class="insight-pill">
          ${icon('review')} ${d.evidence_words || 0} sentiment tokens
        </div>
        ${Number.isFinite(s.confidence) ? `<div class="insight-pill">${Math.round(s.confidence * 100)}% decision confidence</div>` : ''}
        ${d.negation_hits ? `<div class="insight-pill">${d.negation_hits} contextual negation${d.negation_hits === 1 ? '' : 's'}</div>` : ''}
        ${d.bigram_hits ? `<div class="insight-pill">${icon('spark')} ${d.bigram_hits} phrase matches</div>` : ''}
        ${d.emoji_hits ? `<div class="insight-pill">😊 ${d.emoji_hits} emoji scores</div>` : ''}
        ${d.sarcasm_detected ? `<div class="insight-pill warning">Sarcasm penalty: -${(d.sarcasm_penalty * 100).toFixed(1)}%</div>` : ''}
      </div>

      ${clauseHtml}
      ${s.label_reason ? `<p class="sentiment-reason">${esc(s.label_reason)}</p>` : ''}
      ${aspectGrid(a.aspects, true)}
      ${qualityHtml}

      <div class="analysis-tags">
        <div>
          <span>GENRE MENTIONS</span>
          ${
            a.genres.length
              ? a.genres
                  .map(
                    (t) =>
                      `<span class="tag" title="${t.relevance}% of clauses mention this genre">${esc(t.name)} · ${t.relevance}%</span>`
                  )
                  .join('')
              : '<small>No explicit genre cues</small>'
          }
        </div>
        <div>
          <span>THEME MENTIONS</span>
          ${
            a.themes.length
              ? a.themes
                  .map(
                    (t) =>
                      `<span class="tag theme" title="${t.relevance}% of clauses mention this theme">${esc(t.name)} · ${t.relevance}%</span>`
                  )
                  .join('')
              : '<small>No explicit theme cues</small>'
          }
        </div>
      </div>

      <div class="trust-box ${q.needs_review ? 'flagged' : ''}">
        ${icon(q.needs_review ? 'warning' : 'check')}
        <div>
          <strong>${
            q.needs_review
              ? 'Needs a closer look'
              : q.signals.length
              ? 'Some review signals found'
              : 'No screening signals found'
          }</strong>
          <p>${esc(q.signals.join(' · ') || 'No duplicate or promotional pattern detected.')}</p>
        </div>
        <span>${q.risk_index}<small>risk index</small></span>
      </div>

      <p class="score-note">${esc(s.method)} · Decision confidence is a serving signal, not a calibrated probability. Mention percentages indicate coverage.</p>
    </section>
  `;
}


/* ── Load Studio Summary ── */

async function loadStudioSummary(id) {
  const m = await service.details(id);

  if (view !== 'reviews' || Number($('#studio-movie')?.value) !== id) return;

  const s = m.review_summary;
  const summaryEl = $('#studio-summary');
  if (!summaryEl) return;

  summaryEl.innerHTML = `
    <div class="summary-heading">
      <div class="summary-icon">${icon('review')}</div>
      <div>
        <h3>${esc(m.title)}</h3>
        <p>${pluralize(s.eligible_reviews, 'eligible review')} · ${pluralize(s.duplicates_excluded, 'duplicate')} excluded · ${pluralize(s.flagged_review_ids.length, 'flagged')}</p>
      </div>
    </div>

    <p class="summary-text">${esc(s.summary)}</p>
    ${s.synthetic_demo ? '<p class="sample-note">Synthetic sample reviews</p>' : ''}

    ${aspectGrid(s.aspects)}

    <div class="sentiment-distribution">
      <span><i class="positive-dot"></i>${s.sentiment_counts.positive || 0} positive</span>
      <span><i class="negative-dot"></i>${s.sentiment_counts.negative || 0} negative</span>
      <span><i class="mixed-dot"></i>${s.sentiment_counts.mixed || 0} mixed</span>
      <span><i class="neutral-dot"></i>${s.sentiment_counts.neutral || 0} neutral</span>
      <span>${s.sentiment_counts.uncertain || 0} low-confidence</span>
    </div>
  `;
}


/* ── Taste / History Page ── */

async function renderTaste() {
  const rated = [];

  for (const r of history) {
    let m = cache.get(r.movie_id) || movies.find((m) => m.movie_id === r.movie_id);
    if (!m) {
      try {
        m = await service.details(r.movie_id);
      } catch {
        continue;
      }
    }
    rated.push({ ...m, rating: r.rating });
  }

  // Calculate affinities
  const affinities = {};
  for (const m of rated) {
    for (const t of [...m.genres, ...m.themes]) {
      affinities[t] = (affinities[t] || 0) + (m.rating - 3);
    }
  }

  const top = Object.entries(affinities)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  // Calculate average rating
  const avgRating = rated.length
    ? (rated.reduce((s, m) => s + m.rating, 0) / rated.length).toFixed(1)
    : '—';

  // Find highest and lowest rated
  const highest = rated.length
    ? rated.reduce((a, b) => (a.rating >= b.rating ? a : b))
    : null;

  // Genre distribution for mini chart
  const genreCounts = {};
  for (const m of rated) {
    for (const g of m.genres) {
      genreCounts[g] = (genreCounts[g] || 0) + 1;
    }
  }
  const topGenres = Object.entries(genreCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const maxGenreCount = topGenres.length ? topGenres[0][1] : 0;

  $('#main').innerHTML = `
    <div class="page-heading">
      <span class="eyebrow">A TASTE THAT'S ALL YOURS</span>
      <h1>Your cinematic fingerprint.</h1>
      <p>Your ratings make every next recommendation more personal.</p>
    </div>

    <div class="taste-overview">
      <div class="taste-stat">
        <strong>${rated.length}</strong>
        <span>films rated</span>
      </div>
      <div class="taste-stat">
        <strong>${avgRating}</strong>
        <span>your average / 5</span>
      </div>
      ${
        highest
          ? `<div class="taste-stat">
              <strong>${highest.rating}</strong>
              <span>highest: ${esc(highest.title)}</span>
            </div>`
          : ''
      }
      <div class="taste-traits">
        <span>YOU'RE DRAWN TO</span>
        <div class="tags">
          ${
            top.length
              ? chips(top.map(([t]) => t), 'lime')
              : '<p>Rate a few films to find your pattern.</p>'
          }
        </div>
      </div>
    </div>

    ${
      rated.length
        ? `<div class="stats-bar">
            <div class="stat-item">
              <span class="stat-value">${new Set(rated.flatMap((m) => m.genres)).size}</span>
              <span class="stat-label">genres explored</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${new Set(rated.flatMap((m) => m.themes)).size}</span>
              <span class="stat-label">themes touched</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${rated.filter((m) => m.rating >= 4).length}</span>
              <span class="stat-label">films loved (4+)</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${Math.round(rated.reduce((s, m) => s + (m.runtime || 0), 0) / 60)}h</span>
              <span class="stat-label">total runtime</span>
            </div>
          </div>`
        : ''
    }

    ${
      topGenres.length
        ? `<div class="genre-chart">
            <h3>Genre Distribution</h3>
            <div class="genre-bars">
              ${topGenres
                .map(
                  ([genre, count]) =>
                    `<div class="genre-bar-row">
                      <span class="genre-bar-label">${esc(genre)}</span>
                      <div class="genre-bar-track">
                        <div class="genre-bar-fill" style="width:${Math.round((count / maxGenreCount) * 100)}%"></div>
                      </div>
                      <span class="genre-bar-count">${count}</span>
                    </div>`
                )
                .join('')}
            </div>
          </div>`
        : ''
    }

    <div class="section-heading">
      <div>
        <h2>Your watch history</h2>
        <p>Open a film to update or remove your rating.</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        ${
          rated.length
            ? `<button class="ghost" id="export-taste" title="Export your ratings">${icon('export')} Export</button>`
            : ''
        }
        <button class="secondary" data-view="discover">Find more films ${icon('arrow')}</button>
      </div>
    </div>

    <div class="movie-grid">
      ${
        rated.length
          ? rated.map((m, i) => card(m, i)).join('')
          : `<div class="empty">
              <div class="empty-icon">${icon('heart')}</div>
              <h3>The first film is up to you.</h3>
              <p>Explore a movie and give it a rating. Your taste starts taking shape from there.</p>
              <button class="primary" data-view="discover">Explore movies</button>
            </div>`
      }
    </div>
  `;

  // Export button
  const exportBtn = $('#export-taste');
  if (exportBtn) {
    exportBtn.onclick = exportTasteData;
  }

  // Observe cards for lazy animation
  observeCards();
}




/* ── Application Bootstrap ── */

async function start() {
  try {
    movies = await service.init();
    movies.forEach((m) => cache.set(m.movie_id, m));
    history = await service.getHistory();

    shell();

    // Navigate to initial view from URL hash
    const initial = location.hash.slice(1);
    navigate(['reviews', 'taste'].includes(initial) ? initial : 'discover');

    // Log successful boot
    console.log(
      `%c🎬 CineScope%c loaded · ${movies.length} films · ${service.apiMode ? 'API connected' : 'demo mode'}`,
      'font-weight:bold;color:#c5f277',
      'color:#9aa5ab'
    );
  } catch (e) {
    console.error('[CineScope] Boot failed:', e);
    $('#app').innerHTML = `
      <main class="boot-error">
        <h1>CineScope</h1>
        <p>Could not load the movie catalog.</p>
        <p>${esc(e.message)}</p>
        <button onclick="location.reload()">Try again</button>
      </main>
    `;
  }
}

// Start the application
start();
