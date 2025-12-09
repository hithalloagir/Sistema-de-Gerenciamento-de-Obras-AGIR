document.addEventListener('DOMContentLoaded', function () {
  const mapElement = document.getElementById('map');
  if (!mapElement || typeof L === 'undefined') return;

  const dataElement = document.getElementById('markers-data');
  const markersData = dataElement ? JSON.parse(dataElement.textContent) : [];

  let initialLat = -15.77972;
  let initialLng = -47.92972;
  let initialZoom = 5;

  if (markersData.length > 0) {
    initialLat = markersData[0].lat;
    initialLng = markersData[0].lng;
    initialZoom = 15;
  }

  const map = L.map('map').setView([initialLat, initialLng], initialZoom);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  const bounds = [];
  markersData.forEach(function (item) {
    const marker = L.marker([item.lat, item.lng]).addTo(map);
    marker.bindPopup(item.popup);
    bounds.push([item.lat, item.lng]);
  });

  if (bounds.length > 1) {
    map.fitBounds(bounds, {padding: [50, 50]});
  }
});
