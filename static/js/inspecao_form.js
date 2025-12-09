document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('btn-capturar-localizacao');
  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');

  if (!btn || !latInput || !lngInput) return;

  btn.addEventListener('click', function () {
    if (!navigator.geolocation) {
      alert("Geolocalização não é suportada neste navegador.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      function (position) {
        latInput.value = position.coords.latitude;
        lngInput.value = position.coords.longitude;
        alert("Localização capturada com sucesso!");
      },
      function () {
        alert("Não foi possível obter a localização. Verifique as permissões do navegador.");
      }
    );
  });
});
