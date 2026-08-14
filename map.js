/* map.js — Interactive MapLibre GL JS map for the US Library Census Wiki.
 *
 * Uses WebGL rendering with per-type cluster sources (public/private/gov).
 * Each type has its own GeoJSON source + cluster + unclustered layers,
 * so toggling visibility is instant and clustering works correctly.
 */
(function () {
  'use strict';

  var COLORS = { public: '#2b7fff', private: '#e23b3b', gov: '#8e44ff' };
  var LABELS = { public: 'Public', private: 'Private', gov: 'Gov' };
  var TYPES = ['public', 'private', 'gov'];

  var LIGHT_TILES = [
    'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
  ];
  var DARK_TILES = [
    'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
  ];

  var map;
  var allFeatures = [];
  var featuresByType = { public: [], private: [], gov: [] };
  var loaded = false;
  var layersVisible = { public: true, private: true, gov: true };
  var votingOverlayVisible = false;
  var stateVotes = {};

  var STATE_CENTERS = {
    AL:[32.8,-86.8],AK:[64.2,-149.5],AZ:[34.2,-111.6],AR:[34.8,-92.4],CA:[36.8,-119.4],
    CO:[39.0,-105.4],CT:[41.6,-72.7],DE:[39.0,-75.5],FL:[28.7,-82.2],GA:[32.7,-83.5],
    HI:[20.6,-157.0],ID:[44.4,-114.6],IL:[40.0,-89.2],IN:[39.9,-86.3],IA:[42.1,-93.4],
    KS:[38.5,-98.0],KY:[37.5,-85.3],LA:[31.0,-92.0],ME:[45.4,-69.3],MD:[39.1,-77.0],
    MA:[42.3,-71.8],MI:[44.5,-85.4],MN:[46.3,-94.7],MS:[32.8,-89.7],MO:[38.4,-92.5],
    MT:[46.9,-109.5],NE:[41.5,-99.8],NV:[39.5,-116.8],NH:[43.8,-71.6],NJ:[40.1,-74.4],
    NM:[34.3,-106.1],NY:[42.9,-75.5],NC:[35.5,-79.2],ND:[47.5,-100.5],OH:[40.2,-82.8],
    OK:[35.4,-97.3],OR:[43.9,-120.6],PA:[40.9,-77.6],RI:[41.7,-71.6],SC:[33.9,-80.9],
    SD:[44.4,-100.3],TN:[35.8,-86.3],TX:[31.0,-99.3],UT:[39.3,-111.7],VT:[44.0,-72.7],
    VA:[37.8,-79.0],WA:[47.4,-120.8],WV:[38.6,-80.5],WI:[44.6,-89.8],WY:[43.0,-107.3],
    DC:[38.9,-77.0],PR:[18.2,-66.4]
  };

  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function truncate(s, n) {
    if (!s) return '';
    s = String(s);
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function popupHTML(p) {
    var h = '<h3>' + esc(p.n || 'Unknown') + '</h3>';
    var loc = [];
    if (p.c) loc.push(esc(p.c));
    if (p.s) loc.push(esc(p.s));
    if (loc.length) h += '<p>' + loc.join(', ') + '</p>';
    if (p.r) h += '<p>&#9733; ' + esc(p.r) + '</p>';
    if (p.tier) h += '<p><b>Tier:</b> ' + esc(p.tier) + '</p>';
    if (p.w) h += '<p><a href="' + esc(p.w) + '" target="_blank" rel="noopener">' + esc(truncate(p.w, 50)) + '</a></p>';
    h += '<p><span class="type-badge type-' + esc(p.t) + '">' + esc(LABELS[p.t] || p.t) + '</span></p>';
    return h;
  }

  function getMapStyle(theme) {
    var tiles = (theme === 'dark') ? DARK_TILES : LIGHT_TILES;
    return {
      version: 8,
      sources: {
        'raster-tiles': {
          type: 'raster',
          tiles: tiles,
          tileSize: 256,
          attribution: '&copy; OpenStreetMap &copy; CARTO'
        }
      },
      layers: [{
        id: 'background-tiles',
        type: 'raster',
        source: 'raster-tiles',
        minzoom: 0,
        maxzoom: 20
      }]
    };
  }

  /* Swap the raster tile source for light/dark without touching the data
   * sources/layers — keeps clustering, popups and toggles intact. */
  function applyTheme(theme) {
    if (!map) return;
    var tiles = (theme === 'dark') ? DARK_TILES : LIGHT_TILES;
    if (map.getLayer('background-tiles')) map.removeLayer('background-tiles');
    if (map.getSource('raster-tiles')) map.removeSource('raster-tiles');
    map.addSource('raster-tiles', {
      type: 'raster',
      tiles: tiles,
      tileSize: 256,
      attribution: '&copy; OpenStreetMap &copy; CARTO'
    });
    var layerDef = { id: 'background-tiles', type: 'raster', source: 'raster-tiles', minzoom: 0, maxzoom: 20 };
    // Re-insert at the bottom (before the first data layer) so points render on top
    if (map.getLayer('clusters-public')) map.addLayer(layerDef, 'clusters-public');
    else map.addLayer(layerDef);
  }

  function initMap() {
    var initialTheme = document.documentElement.getAttribute('data-theme') || 'light';
    map = new maplibregl.Map({
      container: 'map',
      style: getMapStyle(initialTheme),
      center: [-97.0, 39.0],
      zoom: 4,
      minZoom: 3,
      maxZoom: 18
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'imperial' }), 'bottom-left');

    map.on('load', function () {
      loadData();
    });
  }

  function loadData() {
    // Load map points, state boundaries, and voting data in parallel
    Promise.all([
      fetch('data/map_points.geojson').then(function (r) { return r.json(); }),
      fetch('data/us_states.geojson').then(function (r) { return r.json(); }).catch(function () { return null; }),
      fetch('data/state_votes.json').then(function (r) { return r.json(); }).catch(function () { return null; }),
    ]).then(function (results) {
        var data = results[0];
        var statesGeo = results[1];
        stateVotes = results[2] || {};

        allFeatures = data.features || [];

        // Split features by type for per-type sources
        for (var i = 0; i < TYPES.length; i++) featuresByType[TYPES[i]] = [];
        for (var j = 0; j < allFeatures.length; j++) {
          var t = allFeatures[j].properties.t;
          if (featuresByType[t]) featuresByType[t].push(allFeatures[j]);
        }

        addSourcesAndLayers();
        if (statesGeo) addStatesLayer(statesGeo);
        populateStateFilter();
        updateStats();
        hideLoading();
        loaded = true;
      })
      .catch(function (err) {
        var el = document.getElementById('mapLoading');
        if (el) el.innerHTML = '<p class="text-danger">Error: ' + esc(err.message) + '</p>';
      });
  }

  /* Add US state boundary fill + outline layers for the voting choropleth.
   * Uses a match expression on the state code to color by party.
   * The fill layer is hidden by default; toggle via window.toggleVotingOverlay(). */
  function addStatesLayer(statesGeo) {
    if (map.getSource('states-src')) return;  // already added
    map.addSource('states-src', { type: 'geojson', data: statesGeo });

    // Build match expression: [match, ['get','code'], 'AL', color, ..., fallback]
    // Stronger color = bigger margin; weaker = closer swing state
    var matchExpr = ['match', ['get', 'code']];
    var redStates = [];
    var blueStates = [];
    for (var code in stateVotes) {
      if (stateVotes[code].party === 'R') redStates.push(code);
      else blueStates.push(code);
    }
    for (var i = 0; i < redStates.length; i++) matchExpr.push(redStates[i]);
    matchExpr.push('rgba(226,59,59,0.18)');   // red, semi-transparent
    for (var j = 0; j < blueStates.length; j++) matchExpr.push(blueStates[j]);
    matchExpr.push('rgba(51,102,204,0.18)');   // blue, semi-transparent
    matchExpr.push('rgba(128,128,128,0.10)');   // fallback (no data)

    // State fill — colored by voting block (hidden by default)
    map.addLayer({
      id: 'states-fill',
      type: 'fill',
      source: 'states-src',
      layout: { visibility: 'none' },
      paint: {
        'fill-color': matchExpr,
        'fill-opacity': 1,
      }
    }, 'clusters-public');  // insert below point layers

    // State outlines — always visible for cleaner geography
    map.addLayer({
      id: 'states-outline',
      type: 'line',
      source: 'states-src',
      paint: {
        'line-color': '#ffffff',
        'line-width': 0.6,
        'line-opacity': 0.7
      }
    }, 'clusters-public');

    // Hover effect on states — show name + party
    map.on('mousemove', 'states-fill', function (e) {
      if (!e.features.length) return;
      var p = e.features[0].properties;
      var code = p.code;
      var v = stateVotes[code];
      var partyText = v ? (v.party === 'R' ? 'Republican' : 'Democratic') : 'Unknown';
      var marginText = v ? ' (+' + v.margin + '%)' : '';
      map.getCanvas().style.cursor = 'pointer';
      var popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 5 })
        .setLngLat(e.lngLat)
        .setHTML('<strong>' + esc(p.name) + '</strong><br>' + partyText + marginText)
        .addTo(map);
      statesPopup = popup;
    });
    map.on('mouseleave', 'states-fill', function () {
      map.getCanvas().style.cursor = '';
      if (statesPopup) { statesPopup.remove(); statesPopup = null; }
    });
  }

  var statesPopup = null;

  function addSourcesAndLayers() {
    for (var i = 0; i < TYPES.length; i++) {
      (function (type) {
        var color = COLORS[type];
        var data = {
          type: 'FeatureCollection',
          features: featuresByType[type]
        };

        // Add source with clustering for this type
        map.addSource('src-' + type, {
          type: 'geojson',
          data: data,
          cluster: true,
          clusterRadius: 40,
          clusterMaxZoom: 14
        });

        // Cluster circles
        map.addLayer({
          id: 'clusters-' + type,
          type: 'circle',
          source: 'src-' + type,
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': color,
            'circle-radius': [
              'step', ['get', 'point_count'],
              8, 10, 12, 50, 18, 200, 24
            ],
            'circle-opacity': 0.6,
            'circle-stroke-color': '#fff',
            'circle-stroke-width': 1
          }
        });

        // Cluster count labels
        map.addLayer({
          id: 'cluster-count-' + type,
          type: 'symbol',
          source: 'src-' + type,
          filter: ['has', 'point_count'],
          layout: {
            'text-field': '{point_count_abbreviated}',
            'text-size': 11
          },
          paint: { 'text-color': '#fff' }
        });

        // Unclustered individual points
        map.addLayer({
          id: 'points-' + type,
          type: 'circle',
          source: 'src-' + type,
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-color': color,
            'circle-radius': [
              'interpolate', ['linear'], ['zoom'],
              3, 3, 10, 5, 15, 7
            ],
            'circle-opacity': 0.8,
            'circle-stroke-color': '#fff',
            'circle-stroke-width': 0.5
          }
        });

        // Click unclustered point → popup
        map.on('click', 'points-' + type, function (e) {
          var feat = e.features[0];
          new maplibregl.Popup({ maxWidth: 300, offset: 10 })
            .setLngLat(feat.geometry.coordinates.slice())
            .setHTML(popupHTML(feat.properties))
            .addTo(map);
        });

        // Click cluster → zoom into it
        map.on('click', 'clusters-' + type, function (e) {
          var clusterId = e.features[0].properties.cluster_id;
          map.getSource('src-' + type).getClusterExpansionZoom(clusterId, function (err, zoom) {
            if (err) return;
            map.easeTo({ center: e.features[0].geometry.coordinates, zoom: zoom });
          });
        });

        // Cursor
        map.on('mouseenter', 'points-' + type, function () { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'points-' + type, function () { map.getCanvas().style.cursor = ''; });
        map.on('mouseenter', 'clusters-' + type, function () { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'clusters-' + type, function () { map.getCanvas().style.cursor = ''; });
      })(TYPES[i]);
    }
  }

  function updateStats() {
    var counts = { public: 0, private: 0, gov: 0 };
    for (var i = 0; i < TYPES.length; i++) counts[TYPES[i]] = featuresByType[TYPES[i]].length;
    var el = document.getElementById('mapStats');
    if (el) {
      el.innerHTML =
        '<div><span class="legend-dot" style="background:' + COLORS.public + '"></span> ' + counts.public.toLocaleString() + ' public</div>' +
        '<div><span class="legend-dot" style="background:' + COLORS.private + '"></span> ' + counts.private.toLocaleString() + ' private</div>' +
        '<div><span class="legend-dot" style="background:' + COLORS.gov + '"></span> ' + counts.gov.toLocaleString() + ' gov</div>' +
        '<div class="mt-1 fw-bold">' + (counts.public + counts.private + counts.gov).toLocaleString() + ' total</div>';
    }
  }

  function hideLoading() {
    var el = document.getElementById('mapLoading');
    if (el) {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.4s ease';
      setTimeout(function () { el.style.display = 'none'; }, 400);
    }
  }

  function populateStateFilter() {
    var sel = document.getElementById('mapStateFilter');
    if (!sel) return;
    var states = {};
    for (var i = 0; i < allFeatures.length; i++) {
      var s = allFeatures[i].properties.s;
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

  function setLayerVisibility(type, visible) {
    if (!loaded) return;
    var layers = ['clusters-' + type, 'cluster-count-' + type, 'points-' + type];
    for (var i = 0; i < layers.length; i++) {
      if (map.getLayer(layers[i])) {
        map.setLayoutProperty(layers[i], 'visibility', visible ? 'visible' : 'none');
      }
    }
  }

  // ---- Public API (called from HTML) ----
  window.getMapStyle = getMapStyle;
  window.applyTheme = applyTheme;

  window.toggleVotingOverlay = function () {
    if (!loaded || !map.getLayer('states-fill')) return;
    votingOverlayVisible = !votingOverlayVisible;
    map.setLayoutProperty('states-fill', 'visibility', votingOverlayVisible ? 'visible' : 'none');
    var label = document.getElementById('votingLabel');
    if (label) label.textContent = votingOverlayVisible ? 'ON' : 'OFF';
  };

  window.toggleLayer = function (type) {
    var chk = type === 'public' ? 'chkPublic' : type === 'private' ? 'chkPrivate' : 'chkGov';
    var cb = document.getElementById(chk);
    layersVisible[type] = cb.checked;
    setLayerVisibility(type, cb.checked);
  };

  window.mapSearch = function () {
    var q = (document.getElementById('mapSearchInput').value || '').toLowerCase().trim();
    var stateF = document.getElementById('mapStateFilter').value;
    if (!q || !loaded) return;
    for (var i = 0; i < allFeatures.length; i++) {
      var p = allFeatures[i].properties;
      var name = (p.n || '').toLowerCase();
      var city = (p.c || '').toLowerCase();
      if (name.indexOf(q) !== -1 || city.indexOf(q) !== -1) {
        if (stateF && p.s !== stateF) continue;
        var coords = allFeatures[i].geometry.coordinates;
        // Make sure the type layer is visible
        if (!layersVisible[p.t]) {
          var chkId = p.t === 'public' ? 'chkPublic' : p.t === 'private' ? 'chkPrivate' : 'chkGov';
          var cb = document.getElementById(chkId);
          if (cb) { cb.checked = true; layersVisible[p.t] = true; setLayerVisibility(p.t, true); }
        }
        map.flyTo({ center: coords, zoom: 14, duration: 1500 });
        setTimeout(function () {
          new maplibregl.Popup({ maxWidth: 300, offset: 10 })
            .setLngLat(coords)
            .setHTML(popupHTML(p))
            .addTo(map);
        }, 1600);
        return;
      }
    }
    alert('No location found for "' + q + '"' + (stateF ? ' in ' + stateF : ''));
  };

  window.zoomToState = function (sel) {
    var st = sel.value;
    if (!st) {
      map.flyTo({ center: [-97, 39], zoom: 4, duration: 1200 });
      return;
    }
    var c = STATE_CENTERS[st];
    if (c) map.flyTo({ center: [c[1], c[0]], zoom: 7, duration: 1200 });
  };

  // ---- Boot ----
  document.addEventListener('DOMContentLoaded', function () {
    if (typeof maplibregl === 'undefined') {
      var el = document.getElementById('mapLoading');
      if (el) el.innerHTML = '<p class="text-danger">Failed to load MapLibre GL JS. Check your internet connection.</p>';
      return;
    }
    initMap();
  });

  // Listen for theme changes from the parent page (when embedded as an iframe)
  window.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'wiki-theme' && e.data.theme) {
      document.documentElement.setAttribute('data-theme', e.data.theme);
      if (loaded) applyTheme(e.data.theme);
    }
  });
})();
