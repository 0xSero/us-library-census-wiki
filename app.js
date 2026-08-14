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
  function fmtMoney(s) {
    var n = parseFloat(s);
    if (isNaN(n)) return esc(s);
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return '$' + (n / 1e3).toFixed(0) + 'K';
    return '$' + n.toLocaleString();
  }
  function fmtBytes(s) {
    var n = parseInt(s, 10);
    if (isNaN(n)) return esc(s);
    if (n >= 1048576) return (n / 1048576).toFixed(1) + ' MB';
    if (n >= 1024) return (n / 1024).toFixed(1) + ' KB';
    return n + ' B';
  }
  function fmtStatus(code) {
    var n = parseInt(code, 10);
    var label = esc(code);
    var cls = 'status-other';
    if (n >= 200 && n < 300) cls = 'status-ok';
    else if (n >= 300 && n < 400) cls = 'status-redir';
    else if (n >= 400 && n < 500) cls = 'status-warn';
    else if (n >= 500) cls = 'status-err';
    else if (n === 0) cls = 'status-err';
    return '<span class="' + cls + '">' + label + '</span>';
  }
  function fmtNum(s) {
    var n = parseFloat(s);
    if (isNaN(n)) return esc(s);
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toLocaleString();
  }
  function section(title) {
    return '<tr class="detail-section"><td colspan="2">' + esc(title) + '</td></tr>';
  }

  window.showDetail = function (idx) {
    var r = filtered[idx];
    if (!r) return;
    var panel = document.getElementById('detailPanel');
    var content = document.getElementById('detailContent');
    if (!panel || !content) return;

    var isGov = r.type === 'gov';
    var html = '<h2>' + esc(r.name || '') + '</h2>';
    html += '<div class="detail-meta"><span class="type-badge type-' + esc(r.type) + '">' + esc(r.type) + (r.tier ? '/' + esc(r.tier) : '') + '</span>';
    if (r.state) html += ' · ' + esc(r.state);
    if (r.city) html += ' · ' + esc(r.city);
    html += '</div>';

    html += '<table class="detail-table">';

    // ---- Contact ----
    var hasContact = r.address || r.phone || r.email || r.fb || r.tw || r.ig || r.yt;
    if (hasContact) {
      html += section('Contact');
      if (r.address) html += row('Address', esc(r.address) + (r.zip ? ', ' + esc(r.zip) : ''));
      if (r.phone) html += row('Phone', esc(r.phone));
      if (r.email) html += row('Email', '<a href="mailto:' + esc(r.email) + '">' + esc(r.email) + '</a>');
      if (r.fb) html += row('Facebook', '<a href="' + esc(r.fb) + '" target="_blank" rel="noopener">' + esc(r.fb) + '</a>');
      if (r.tw) html += row('Twitter / X', '<a href="' + esc(r.tw) + '" target="_blank" rel="noopener">' + esc(r.tw) + '</a>');
      if (r.ig) html += row('Instagram', '<a href="' + esc(r.ig) + '" target="_blank" rel="noopener">' + esc(r.ig) + '</a>');
      if (r.yt) html += row('YouTube', '<a href="' + esc(r.yt) + '" target="_blank" rel="noopener">' + esc(r.yt) + '</a>');
    }

    // ---- Website & verification ----
    var hasWeb = r.website || r.ttl || r.furl || r.ulive || r.hstat || r.srv || r.ctype || r.clen || r.lmod || r.redir || r.cerr || r.cat;
    if (hasWeb) {
      html += section('Website');
      if (r.website) html += row('Website', '<a href="' + esc(r.website) + '" target="_blank" rel="noopener">' + esc(r.website) + '</a>');
      if (r.ttl) html += row('Page title', esc(r.ttl));
      if (r.furl && r.furl !== r.website) html += row('Final URL', '<a href="' + esc(r.furl) + '" target="_blank" rel="noopener">' + esc(r.furl) + '</a>');
      if (r.ulive !== undefined) html += row('Live', r.ulive && r.ulive !== 'False' ? '<span class="live">● Yes</span>' : '<span class="dead">○ No</span>');
      if (r.hstat) html += row('HTTP status', fmtStatus(r.hstat));
      if (r.srv) html += row('Server', esc(r.srv));
      if (r.ctype) html += row('Content type', esc(r.ctype));
      if (r.clen) html += row('Content length', fmtBytes(r.clen));
      if (r.lmod) html += row('Last modified', esc(r.lmod));
      if (r.redir) html += row('Redirects', esc(r.redir));
      if (r.cerr) html += row('Check error', '<span class="dead">' + esc(r.cerr) + '</span>');
      if (r.cat) html += row('Checked at', esc(r.cat));
    }

    // ---- Reviews ----
    if (r.rating) html += section('Reviews') + row('Rating', '★ ' + esc(r.rating) + (r.rcount ? ' (' + esc(r.rcount) + ' reviews)' : '') + (r.rsrc ? ' <span class="rsrc">via ' + esc(r.rsrc) + '</span>' : ''));

    // ---- Hours & services ----
    var hrs = hoursMap[r.id];
    var svc = servicesMap[r.id];
    if ((hrs && hrs.raw) || svc) {
      html += section('Hours & services');
      if (hrs && hrs.raw) html += row('Hours', esc(hrs.raw) + (hrs.structured ? '<br><code>' + esc(hrs.structured) + '</code>' : ''));
      if (svc) html += row('Services', esc(svc));
    }

    // ---- Demographics ----
    if (r.pop || r.income || r.pov || r.age || r.edu || r.comp || r.inet || r.lang) {
      html += section('Community demographics');
      if (r.pop) html += row('Area population', esc(r.pop));
      if (r.income) html += row('Median household income', fmtMoney(r.income));
      if (r.pov) html += row('Poverty rate', esc(r.pov) + '%');
      if (r.age) html += row('Median age', esc(r.age) + ' years');
      if (r.edu) html += row('Bachelor\'s degree or higher', esc(r.edu) + '%');
      if (r.comp) html += row('Households with a computer', esc(r.comp) + '%');
      if (r.inet) html += row('Households with internet', esc(r.inet) + '%');
      if (r.lang) html += row('Non-English spoken at home', esc(r.lang) + '%');
    }

    // ---- Broadband access ----
    if (r.bbs || r.fixb || r.cellb || r.noint || r.nocomp || r.dlup || r.linoint || r.ddiv) {
      html += section('Community broadband access');
      if (r.bbs) html += row('Broadband subscription', esc(r.bbs) + '%');
      if (r.fixb) html += row('Fixed broadband', esc(r.fixb) + '%');
      if (r.cellb) html += row('Cellular data plan', esc(r.cellb) + '%');
      if (r.dlup) html += row('Dial-up only', esc(r.dlup) + '%');
      if (r.noint) html += row('No internet at home', esc(r.noint) + '%');
      if (r.nocomp) html += row('No computer at home', esc(r.nocomp) + '%');
      if (r.linoint) html += row('Low-income no internet', esc(r.linoint) + '%');
      if (r.ddiv) html += row('Digital divide ratio', esc(r.ddiv) + '× (low-income vs overall)');
    }

    // ---- Facility & funding ----
    if (r.sqft || r.coll || r.psrv || r.ft || r.fsrc) {
      html += section('Facility & funding');
      if (r.sqft) html += row('Building size', esc(r.sqft) + ' sqft');
      if (r.coll) html += row('Collection size', esc(r.coll) + ' items');
      if (r.psrv) html += row('Population served', esc(r.psrv));
      if (r.ft) html += row('Funding total', fmtMoney(r.ft));
      if (r.fsrc) html += row('Funding source', esc(r.fsrc));
    }

    // ---- Annual operations (PLS FY2024) ----
    if (r.vis || r.cir || r.ecir || r.pcir || r.prog || r.patt || r.cprog || r.yprog || r.aprog ||
        r.iterm || r.wifi || r.rbor || r.illto || r.illfm || r.staff || r.lstaff ||
        r.salx || r.pmex || r.emex || r.capex || r.cbr || r.nbr || r.bkm) {
      html += section('Annual operations (PLS FY2024)');
      if (r.vis) html += row('Annual visits', fmtNum(r.vis));
      if (r.cir) html += row('Total circulation', fmtNum(r.cir));
      if (r.ecir) html += row('E-material circulation', fmtNum(r.ecir));
      if (r.pcir) html += row('Physical circulation', fmtNum(r.pcir));
      if (r.prog) html += row('Programs offered', fmtNum(r.prog));
      if (r.patt) html += row('Program attendance', fmtNum(r.patt));
      if (r.cprog) html += row('Children\'s programs', fmtNum(r.cprog));
      if (r.yprog) html += row('Young adult programs', fmtNum(r.yprog));
      if (r.aprog) html += row('Adult programs', fmtNum(r.aprog));
      if (r.iterm) html += row('Internet terminal users', fmtNum(r.iterm));
      if (r.wifi) html += row('WiFi sessions', fmtNum(r.wifi));
      if (r.rbor) html += row('Registered borrowers', fmtNum(r.rbor));
      if (r.illto) html += row('ILL — loaned to other systems', fmtNum(r.illto));
      if (r.illfm) html += row('ILL — borrowed from other systems', fmtNum(r.illfm));
      if (r.staff) html += row('Total staff (FTE)', esc(r.staff));
      if (r.lstaff) html += row('Librarians with MLS (FTE)', esc(r.lstaff));
      if (r.salx) html += row('Salary expenditures', fmtMoney(r.salx));
      if (r.pmex) html += row('Print material expenditures', fmtMoney(r.pmex));
      if (r.emex) html += row('Electronic material expenditures', fmtMoney(r.emex));
      if (r.capex) html += row('Capital expenditures', fmtMoney(r.capex));
      if (r.cbr) html += row('Central libraries', esc(r.cbr));
      if (r.nbr) html += row('Branch libraries', esc(r.nbr));
      if (r.bkm) html += row('Bookmobiles', esc(r.bkm));
    }

    // ---- Location ----
    if (r.lat && r.lng) {
      html += section('Location');
      var mapUrl = 'https://www.google.com/maps?q=' + encodeURIComponent(r.lat + ',' + r.lng);
      html += row('Coordinates', esc(r.lat) + ', ' + esc(r.lng) + ' · <a href="' + mapUrl + '" target="_blank" rel="noopener">View on Google Maps →</a>');
    }

    // ---- Source metadata ----
    if (r.nt) html += section('Source metadata') + row('Notes', esc(r.nt));

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
