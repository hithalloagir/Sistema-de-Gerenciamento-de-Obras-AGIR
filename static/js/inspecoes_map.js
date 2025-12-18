document.addEventListener('DOMContentLoaded', function () {
  const mapElement = document.getElementById('map');
  if (!mapElement || typeof L === 'undefined') return;

  const dataElement = document.getElementById('markers-data');
  const rawMarkers = dataElement ? JSON.parse(dataElement.textContent) : [];
  const markersData = Array.isArray(rawMarkers)
    ? rawMarkers.filter(function (m) {
        return m && Number.isFinite(m.lat) && Number.isFinite(m.lng);
      })
    : [];

  let initialLat = -15.77972;
  let initialLng = -47.92972;
  let initialZoom = 5;

  if (markersData.length > 0) {
    initialLat = markersData[0].lat;
    initialLng = markersData[0].lng;
    initialZoom = 16;
  }

  const map = L.map('map', { scrollWheelZoom: false }).setView(
    [initialLat, initialLng],
    initialZoom
  );

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  L.control.scale({ imperial: false }).addTo(map);

  map.on('click', function () {
    map.scrollWheelZoom.enable();
  });

  const bounds = [];
  markersData.forEach(function (item) {
    const marker = L.marker([item.lat, item.lng]).addTo(map);
    marker.bindPopup(item.popup);
    bounds.push([item.lat, item.lng]);
  });

  if (bounds.length > 1) {
    map.fitBounds(bounds, {padding: [50, 50]});
  } else if (bounds.length === 1) {
    map.setView(bounds[0], 16);
  }
});
