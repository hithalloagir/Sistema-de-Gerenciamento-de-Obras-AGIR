document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('btn-capturar-localizacao');
  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');
  const locationAlert = document.getElementById('location-alert');
  const form = btn ? btn.closest('form') : null;

  if (!btn || !latInput || !lngInput) {
    return;
  }

  const showLocationMessage = (message, type = 'warning') => {
    if (!locationAlert) {
      alert(message);
      return;
    }
    locationAlert.textContent = message;
    locationAlert.classList.remove('d-none', 'alert-warning', 'alert-success');
    locationAlert.classList.add(`alert-${type}`);
  };

  const hideLocationMessage = () => {
    if (locationAlert) {
      locationAlert.classList.add('d-none');
    }
  };

  btn.addEventListener('click', function () {
    if (!navigator.geolocation) {
      showLocationMessage('GeolocalizaÇõÇœo nÇœo Ç¸ suportada neste navegador.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      function (position) {
        latInput.value = position.coords.latitude;
        lngInput.value = position.coords.longitude;
        showLocationMessage('LocalizaÇõÇœo capturada com sucesso. VocÇ¦ jÇ¸ pode salvar a inspeÇõÇœo.', 'success');
      },
      function () {
        showLocationMessage('NÇœo foi possÇðvel obter a localizaÇõÇœo. Verifique as permissÇæes do navegador e tente novamente.');
      }
    );
  });

  if (form) {
    form.addEventListener('submit', function (event) {
      if (!latInput.value || !lngInput.value) {
        event.preventDefault();
        showLocationMessage('Capture a localizaÇõÇœo antes de salvar a inspeÇõÇœo.');
      } else {
        hideLocationMessage();
      }
    });
  }
});
