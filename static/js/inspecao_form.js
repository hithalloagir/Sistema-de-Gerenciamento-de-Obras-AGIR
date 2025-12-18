document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('inspecao-form');
  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');

  const errCodeInput = document.getElementById('id_location_error_code');
  const errMessageInput = document.getElementById('id_location_error_message');
  const errReasonInput = document.getElementById('id_location_error_reason');

  const locationAlert = document.getElementById('location-alert');
  const statusEl = document.getElementById('location-status');
  const coordsEl = document.getElementById('location-coords');
  const captureBtn = document.getElementById('btn-capture-location');
  const clearBtn = document.getElementById('btn-clear-location');
  const spinnerEl = document.getElementById('location-spinner');
  const captureBtnText = document.getElementById('location-btn-text');

  if (!form || !latInput || !lngInput) return;

  let requestInFlight = false;
  let allowSubmitWithoutGeo = false;

  const clearErrorMeta = () => {
    if (errCodeInput) errCodeInput.value = '';
    if (errMessageInput) errMessageInput.value = '';
    if (errReasonInput) errReasonInput.value = '';
  };

  const setBusy = (busy) => {
    if (spinnerEl) spinnerEl.classList.toggle('d-none', !busy);
    if (captureBtn) captureBtn.disabled = !!busy;
    if (captureBtnText) captureBtnText.textContent = busy ? 'Capturando…' : 'Capturar';
  };

  const setStatus = (message) => {
    if (!statusEl) return;
    statusEl.textContent = message || '';
  };

  const showAlert = (message, type = 'warning') => {
    if (!locationAlert) {
      if (message) alert(message);
      return;
    }
    locationAlert.textContent = message || '';
    locationAlert.classList.remove(
      'd-none',
      'alert-warning',
      'alert-success',
      'alert-danger'
    );
    locationAlert.classList.add(`alert-${type}`);
  };

  const hideAlert = () => {
    if (locationAlert) locationAlert.classList.add('d-none');
  };

  const isLikelySecureForGeolocation = () => {
    const host = window.location.hostname;
    const isLocalhost = host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
    return window.isSecureContext || isLocalhost;
  };

  const getHighAccuracy = () => {
    const raw = (form.dataset.geoHighAccuracy || '').toLowerCase().trim();
    return raw === '1' || raw === 'true' || raw === 'yes';
  };

  const hasCoords = () => !!(latInput.value && lngInput.value);

  const writeCoords = (lat, lng, accuracy) => {
    const latNum = typeof lat === 'number' ? lat : Number(lat);
    const lngNum = typeof lng === 'number' ? lng : Number(lng);
    if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return false;

    latInput.value = latNum.toFixed(6);
    lngInput.value = lngNum.toFixed(6);

    if (coordsEl) {
      const parts = [`Lat: ${latNum.toFixed(6)}`, `Lng: ${lngNum.toFixed(6)}`];
      const accNum = typeof accuracy === 'number' ? accuracy : Number(accuracy);
      if (Number.isFinite(accNum) && accNum > 0) parts.push(`±${Math.round(accNum)}m`);
      coordsEl.textContent = parts.join(' • ');
      coordsEl.classList.remove('d-none');
    }

    if (clearBtn) clearBtn.classList.remove('d-none');
    setStatus('Coordenadas registradas.');
    return true;
  };

  const clearCoords = () => {
    latInput.value = '';
    lngInput.value = '';
    if (coordsEl) {
      coordsEl.textContent = '';
      coordsEl.classList.add('d-none');
    }
    if (clearBtn) clearBtn.classList.add('d-none');
    setStatus('Ao salvar, tentaremos registrar as coordenadas desta inspeção.');
  };

  const buildErrorReason = (error) => {
    const code = error && typeof error.code === 'number' ? error.code : null;
    const message = error && error.message ? String(error.message) : '';

    if (code === 1) return 'Permissão negada';
    if (code === 2) return 'Localização indisponível';
    if (code === 3) return 'Tempo excedido';
    if (message) return message;
    return 'Erro ao obter localização';
  };

  const requestLocation = () => {
    clearErrorMeta();

    if (!navigator.geolocation) {
      const reason = 'Geolocalização não suportada pelo navegador';
      if (errReasonInput) errReasonInput.value = reason;
      return Promise.reject(new Error(reason));
    }

    if (!isLikelySecureForGeolocation()) {
      setStatus('Dica: use HTTPS ou http://localhost para permitir geolocalização.');
    }

    const geoOptions = {
      enableHighAccuracy: getHighAccuracy(),
      timeout: 15000,
      maximumAge: 60000,
    };

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, geoOptions);
    });
  };

  const captureLocation = async ({ submitAfter } = { submitAfter: false }) => {
    if (requestInFlight) return;
    requestInFlight = true;

    setBusy(true);
    hideAlert();
    setStatus('Solicitando localização…');

    try {
      const position = await requestLocation();
      const ok = writeCoords(
        position.coords.latitude,
        position.coords.longitude,
        position.coords.accuracy
      );
      if (!ok) throw new Error('Coordenadas inválidas');

      hideAlert();
      if (submitAfter) {
        allowSubmitWithoutGeo = true;
        form.submit();
      }
    } catch (error) {
      const reason = buildErrorReason(error);

      if (errCodeInput && error && typeof error.code === 'number') {
        errCodeInput.value = String(error.code);
      }
      if (errMessageInput && error && error.message) {
        errMessageInput.value = String(error.message);
      }
      if (errReasonInput) errReasonInput.value = reason;

      clearCoords();
      showAlert(reason, 'warning');
      setStatus('Salvamento seguirá sem coordenadas.');

      if (submitAfter) {
        allowSubmitWithoutGeo = true;
        form.submit();
      }
    } finally {
      requestInFlight = false;
      setBusy(false);
    }
  };

  form.addEventListener('submit', function (event) {
    if (allowSubmitWithoutGeo) return;
    if (hasCoords()) {
      hideAlert();
      return;
    }

    event.preventDefault();
    captureLocation({ submitAfter: true });
  });

  if (captureBtn) {
    captureBtn.addEventListener('click', function () {
      captureLocation({ submitAfter: false });
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      clearErrorMeta();
      hideAlert();
      clearCoords();
    });
  }

  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions
      .query({ name: 'geolocation' })
      .then((status) => {
        if (status.state === 'denied') {
          setStatus('Permissão de localização bloqueada no navegador.');
        }
      })
      .catch(() => {});
  }

  if (hasCoords()) {
    writeCoords(Number(latInput.value), Number(lngInput.value));
  } else {
    clearCoords();
  }
});

