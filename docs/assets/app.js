/* Portal client-side script: theme toggle + lightweight full-text search */

(function () {
  // ----- theme toggle -----
  const toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const root = document.documentElement;
      root.classList.toggle('dark');
      localStorage.setItem('dai-theme', root.classList.contains('dark') ? 'dark' : 'light');
    });
  }

  // ----- search -----
  const input = document.getElementById('q');
  const panel = document.getElementById('search-panel');
  const panelBody = panel ? panel.querySelector('div') : null;
  let index = null;

  // Derive path prefix from the current location so we work under any base path.
  // e.g. /20260512-newsCollector-chatgpt/archive/2026-05-12/  -> /20260512-newsCollector-chatgpt
  function pathPrefix() {
    const parts = location.pathname.split('/').filter(Boolean);
    // If we're at /<repo>/archive/.../, the prefix is /<repo>.
    // If we're at /<repo>/, parts=[<repo>]. If at /, parts=[]. If at /<repo>/index.html, parts=[<repo>, 'index.html'].
    if (parts.length === 0) return '';
    if (parts[parts.length - 1].endsWith('.html')) parts.pop();
    if (parts[0] === 'archive') return '';
    if (parts.includes('archive')) {
      return '/' + parts.slice(0, parts.indexOf('archive')).join('/');
    }
    return '/' + parts.join('/');
  }
  const PREFIX = pathPrefix();

  async function loadIndex() {
    if (index) return index;
    try {
      const res = await fetch(PREFIX + '/search-index.json');
      const data = await res.json();
      index = data.items || [];
    } catch (e) { console.error('search-index load failed', e); index = []; }
    return index;
  }

  function escapeHTML(s) {
    return (s || '').replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function highlight(s, q) {
    if (!q) return escapeHTML(s);
    const re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
    return escapeHTML(s).replace(re, '<mark class="dai-hit">$1</mark>');
  }

  async function search(q) {
    const items = await loadIndex();
    q = q.trim().toLowerCase();
    if (!q) return [];
    return items.filter(it => {
      const hay = [it.title, it.summary, it.insight,
                   (it.tags || []).join(' '), it.section_label].join(' ').toLowerCase();
      return hay.includes(q);
    }).slice(0, 30);
  }

  let timer = null;
  if (input && panel && panelBody) {
    input.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const q = input.value;
        if (!q.trim()) { panel.classList.add('hidden'); return; }
        const hits = await search(q);
        panel.classList.remove('hidden');
        if (!hits.length) {
          panelBody.innerHTML = `<div class="py-4 text-slate-500">沒有結果</div>`;
          return;
        }
        panelBody.innerHTML = hits.map(h => `
          <a href="${h.permalink}" class="block py-2 border-b border-slate-100 dark:border-slate-800 last:border-b-0">
            <div class="text-xs text-slate-500">${h.date} · ${h.section_label || ''} · ${escapeHTML(h.source_name || '')}</div>
            <div class="font-medium">${highlight(h.title || '', q)}</div>
            <div class="text-sm text-slate-600 dark:text-slate-300 line-clamp-2">${highlight(h.summary || '', q)}</div>
            ${(h.tags || []).map(t => `<span class="inline-block text-[11px] mt-1 mr-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5">#${escapeHTML(t)}</span>`).join('')}
          </a>`).join('');
      }, 120);
    });

    // close on ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { panel.classList.add('hidden'); input.blur(); }
      if (e.key === '/' && document.activeElement !== input) {
        e.preventDefault(); input.focus();
      }
    });
  }

  // ----- archive page filters -----
  const list = document.getElementById('edition-list');
  const tagInput = document.getElementById('filter-tag');
  const dateInput = document.getElementById('filter-date');
  const secSelect = document.getElementById('filter-section');
  const clearBtn = document.getElementById('clear-filters');
  const resultsEl = document.getElementById('search-results');
  if (list && resultsEl) {
    loadIndex().then(items => {
      // populate sections dropdown
      const sections = Array.from(new Set(items.map(i => i.section_label).filter(Boolean))).sort();
      sections.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        secSelect.appendChild(opt);
      });
    });
    const applyFilters = async () => {
      const items = await loadIndex();
      const tag = (tagInput.value || '').trim().toLowerCase();
      const date = (dateInput.value || '').trim();
      const sec = (secSelect.value || '').trim();
      if (!tag && !date && !sec) { resultsEl.innerHTML = ''; list.style.display = ''; return; }
      list.style.display = 'none';
      const filtered = items.filter(it =>
        (!tag || (it.tags || []).map(t => t.toLowerCase()).includes(tag)) &&
        (!date || it.date === date) &&
        (!sec || it.section_label === sec)
      ).slice(0, 80);
      resultsEl.innerHTML = filtered.length
        ? filtered.map(h => `
            <a href="${h.permalink}" class="block rounded-lg border border-slate-200 dark:border-slate-800
                       bg-white dark:bg-slate-900 p-3 my-2 hover:bg-slate-50 dark:hover:bg-slate-800">
              <div class="text-xs text-slate-500">${h.date} · ${h.section_label || ''} · ${escapeHTML(h.source_name || '')}</div>
              <div class="font-medium">${escapeHTML(h.title || '')}</div>
              <div class="text-sm text-slate-600 dark:text-slate-300">${escapeHTML(h.summary || '')}</div>
            </a>`).join('')
        : `<div class="text-slate-500 py-4">沒有符合條件的內容</div>`;
    };
    [tagInput, dateInput, secSelect].forEach(el => el && el.addEventListener('change', applyFilters));
    tagInput && tagInput.addEventListener('keyup', applyFilters);
    clearBtn && clearBtn.addEventListener('click', () => {
      tagInput.value = ''; dateInput.value = ''; secSelect.value = '';
      applyFilters();
    });
  }
})();
