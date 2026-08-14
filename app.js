/* app.js — US Library Census Wiki client-side search & filter
 * Loads condensed JSON data files, provides full-text search,
 * filtering, sorting, pagination, and a detail panel.
 */
(function () {
  'use strict';

  var DATA_DIR = 'data/';
  var PAGE_SIZE = 50;
  var allRecords = [];
  var hoursMap = {};
  var servicesMap = {};
  var filtered = [];
  var currentPage = 1;
  var loaded = false;

  // ---------- Data loading ----------
  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('Failed: ' + url);
      return r.json();
    });
  }

  function loadAll() {
    if (loaded) return Promise.resolve();
    loaded = true;
    var info = document.getElementById('searchInfo');
    if (info) info.textContent = 'Loading data…';

    return Promise.all([
      fetchJSON(DATA_DIR + 'public_libraries.json').catch(function () { return []; }),
      fetchJSON(DATA_DIR + 'private_libraries.json').catch(function () { return []; }),
      fetchJSON(DATA_DIR + 'gov_sites.json').catch(function () { return []; }),
      fetchJSON(DATA_DIR + 'library_hours.json').catch(function () { return {}; }),
      fetchJSON(DATA_DIR + 'library_services.json').catch(function () { return {}; }),
    ]).then(function (results) {
      hoursMap = results[3] || {};
      servicesMap = results[4] || {};
      // Merge all record types into one array
      allRecords = []
        .concat(results[0] || [])
        .concat(results[1] || [])
        .concat(results[2] || []);
      populateStateFilter();
      var info = document.getElementById('searchInfo');
      if (info) info.textContent = allRecords.length.toLocaleString() + ' records loaded. Start typing to search.';
      // Apply any URL params
      applyUrlParams();
      doSearch();
    }).catch(function (err) {
      var info = document.getElementById('searchInfo');
      if (info) info.textContent = 'Error loading data: ' + err.message;
    });
  }

  function populateStateFilter() {
    var sel = document.getElementById('stateFilter');
    if (!sel) return;
    var states = {};
    for (var i = 0; i < allRecords.length; i++) {
      var s = allRecords[i].state;
      if (s) states[s] = true;
    }
    var keys = Object.keys(states).sort();
    for (var k = 0; k < keys.length; k++) {
      var opt = document.createElement('option');
      opt.value = keys[k];
      opt.textContent = keys[k];
      sel.appendChild(opt);
    }
  }

  function applyUrlParams() {
    var params = new URLSearchParams(window.location.search);
    var q = params.get('q');
    var type = params.get('type');
    var state = params.get('state');
    var tier = params.get('tier');
    if (q) { var si = document.getElementById('searchInput'); if (si) si.value = q; }
    if (type) { var tf = document.getElementById('typeFilter'); if (tf) tf.value = type; }
    if (state) { var sf = document.getElementById('stateFilter'); if (sf) sf.value = state; }
    // tier filter — set type to gov and store tier
    if (tier) {
      var tf2 = document.getElementById('typeFilter');
      if (tf2) tf2.value = 'gov';
      window._tierFilter = tier;
    }
  }

  // ---------- Search & filter ----------
  window.doSearch = function () {
    if (!allRecords.length) {
      loadAll();
      return;
    }

    var q = (document.getElementById('searchInput').value || '').toLowerCase().trim();
    var state = document.getElementById('stateFilter').value;
    var type = document.getElementById('typeFilter').value;
    var sort = document.getElementById('sortFilter').value;
    var hasWeb = document.getElementById('hasWebsite').checked;
    var hasRating = document.getElementById('hasRating').checked;
    var tier = window._tierFilter || '';

    filtered = allRecords.filter(function (r) {
      if (state && r.state !== state) return false;
      if (type && r.type !== type) return false;
      if (type === 'gov' && tier && r.tier !== tier) return false;
      if (hasWeb && !(r.website || '').trim()) return false;
      if (hasRating && !(r.rating || '').trim()) return false;
      if (q) {
        var blob = ((r.name || '') + ' ' + (r.city || '') + ' ' + (r.state || '') + ' ' + (r.address || '') + ' ' + (r.tier || '')).toLowerCase();
        if (blob.indexOf(q) === -1) return false;
      }
      return true;
    });

    // Sort
    filtered.sort(function (a, b) {
      if (sort === 'rating') {
        return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
      } else if (sort === 'state') {
        return (a.state || '').localeCompare(b.state || '') || (a.name || '').localeCompare(b.name || '');
      } else if (sort === 'city') {
        return (a.city || '').localeCompare(b.city || '') || (a.name || '').localeCompare(b.name || '');
      }
      return (a.name || '').localeCompare(b.name || '');
    });

    currentPage = 1;
    renderResults();
  };

  function renderResults() {
    var info = document.getElementById('searchInfo');
    var results = document.getElementById('searchResults');
    var pagination = document.getElementById('pagination');
    if (!results) return;

    if (info) info.textContent = filtered.length.toLocaleString() + ' records found' +
      (filtered.length > PAGE_SIZE ? ' (showing page ' + currentPage + ')' : '');

    if (filtered.length === 0) {
      results.innerHTML = '<p class="no-results">No records match your search.</p>';
      if (pagination) pagination.innerHTML = '';
      return;
    }

    var totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * PAGE_SIZE;
    var end = Math.min(start + PAGE_SIZE, filtered.length);
    var pageItems = filtered.slice(start, end);

    var html = '<table class="data-table search-table"><thead><tr>' +
      '<th>Name</th><th>Type</th><th>City</th><th>State</th><th>Rating</th><th>Website</th>' +
      '</tr></thead><tbody>';

    for (var i = 0; i < pageItems.length; i++) {
      var r = pageItems[i];
      var idx = start + i;
      var web = (r.website || '').trim();
      var webHtml = web ? '<a href="' + esc(web) + '" target="_blank" rel="noopener">link</a>' : '—';
      var rating = (r.rating || '').trim();
      var ratingHtml = rating ? '<span class="rating">★ ' + esc(rating) + '</span>' : '—';
      var typeBadge = r.type;
      if (r.type === 'gov' && r.tier) typeBadge = 'gov/' + r.tier;
      html += '<tr class="result-row" data-idx="' + idx + '"><td><a href="#" onclick="showDetail(' + idx + ');return false">' +
        esc(r.name || '') + '</a></td><td><span class="type-badge type-' + esc(r.type) + '">' + esc(typeBadge) +
        '</span></td><td>' + esc(r.city || '') + '</td><td>' + esc(r.state || '') +
        '</td><td>' + ratingHtml + '</td><td>' + webHtml + '</td></tr>';
    }
    html += '</tbody></table>';
    results.innerHTML = html;

    // Pagination
    if (pagination) {
      if (totalPages <= 1) {
        pagination.innerHTML = '';
      } else {
        var ph = '';
        if (currentPage > 1) ph += '<a href="#" onclick="goPage(' + (currentPage - 1) + ');return false">← Prev</a>';
        var maxShow = Math.min(totalPages, 10);
        var pStart = Math.max(1, currentPage - 4);
        var pEnd = Math.min(totalPages, pStart + maxShow - 1);
        for (var p = pStart; p <= pEnd; p++) {
          ph += '<a href="#" class="' + (p === currentPage ? 'cur' : '') + '" onclick="goPage(' + p + ');return false">' + p + '</a>';
        }
        if (currentPage < totalPages) ph += '<a href="#" onclick="goPage(' + (currentPage + 1) + ');return false">Next →</a>';
        pagination.innerHTML = ph;
      }
    }
  }

  window.goPage = function (p) {
    currentPage = p;
    renderResults();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ---------- Detail panel ----------
  window.showDetail = function (idx) {
    var r = filtered[idx];
    if (!r) return;
    var panel = document.getElementById('detailPanel');
    var content = document.getElementById('detailContent');
    if (!panel || !content) return;

    var html = '<h2>' + esc(r.name || '') + '</h2>';
    html += '<div class="detail-meta"><span class="type-badge type-' + esc(r.type) + '">' + esc(r.type) + (r.tier ? '/' + esc(r.tier) : '') + '</span>';
    if (r.state) html += ' · ' + esc(r.state);
    if (r.city) html += ' · ' + esc(r.city);
    html += '</div>';

    html += '<table class="detail-table">';
    if (r.address) html += row('Address', esc(r.address) + (r.zip ? ', ' + esc(r.zip) : ''));
    if (r.phone) html += row('Phone', esc(r.phone));
    if (r.website) html += row('Website', '<a href="' + esc(r.website) + '" target="_blank" rel="noopener">' + esc(r.website) + '</a>');
    if (r.email) html += row('Email', '<a href="mailto:' + esc(r.email) + '">' + esc(r.email) + '</a>');
    if (r.fb) html += row('Facebook', '<a href="' + esc(r.fb) + '" target="_blank" rel="noopener">' + esc(r.fb) + '</a>');
    if (r.rating) html += row('Rating', '★ ' + esc(r.rating) + (r.rcount ? ' (' + esc(r.rcount) + ' reviews)' : '') + (r.rsrc ? ' <span class="rsrc">via ' + esc(r.rsrc) + '</span>' : ''));

    // Hours
    var hrs = hoursMap[r.id];
    if (hrs && hrs.raw) {
      html += row('Hours', esc(hrs.raw) + (hrs.structured ? '<br><code>' + esc(hrs.structured) + '</code>' : ''));
    }

    // Services
    var svc = servicesMap[r.id];
    if (svc) html += row('Services', esc(svc));

    if (r.pop) html += row('Area population', esc(r.pop));
    if (r.income) html += row('Median household income', esc(r.income));
    if (r.sqft) html += row('Building size', esc(r.sqft) + ' sqft');
    if (r.coll) html += row('Collection size', esc(r.coll) + ' items');
    if (r.psrv) html += row('Population served', esc(r.psrv));
    if (r.fsrc) html += row('Funding source', esc(r.fsrc));
    if (r.pov) html += row('Poverty rate', esc(r.pov) + '%');
    if (r.age) html += row('Median age', esc(r.age) + ' years');
    if (r.lat && r.lng) {
      var mapUrl = 'https://www.google.com/maps?q=' + encodeURIComponent(r.lat + ',' + r.lng);
      html += row('Coordinates', esc(r.lat) + ', ' + esc(r.lng) + ' · <a href="' + mapUrl + '" target="_blank" rel="noopener">View on Google Maps →</a>');
    }
    if (r.live !== undefined) {
      html += row('Status', r.live ? '<span class="live">● Live</span>' : '<span class="dead">○ Down</span>');
    }
    html += '</table>';

    content.innerHTML = html;
    panel.classList.add('open');
    document.body.style.overflow = 'hidden';
  };

  function row(label, val) {
    return '<tr><th>' + label + '</th><td>' + val + '</td></tr>';
  }

  window.closeDetail = function () {
    var panel = document.getElementById('detailPanel');
    if (panel) panel.classList.remove('open');
    document.body.style.overflow = '';
  };

  // Escaping
  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Close detail on overlay click
  document.addEventListener('DOMContentLoaded', function () {
    var panel = document.getElementById('detailPanel');
    if (panel) {
      panel.addEventListener('click', function (e) {
        if (e.target === panel) closeDetail();
      });
    }
    // Esc key closes
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDetail();
    });
    loadAll();
  });
})();
