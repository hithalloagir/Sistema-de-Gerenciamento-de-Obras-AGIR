document.addEventListener('DOMContentLoaded', function () {
  console.log('[inspecao_form] script carregado');
  console.log('[inspecao_form] origin:', window.location.origin);

  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');
  const errCodeInput = document.getElementById('id_location_error_code');
  const errMessageInput = document.getElementById('id_location_error_message');
  const errReasonInput = document.getElementById('id_location_error_reason');
  const locationAlert = document.getElementById('location-alert');
  const form = document.getElementById('inspecao-form');

  if (!form || !latInput || !lngInput) {
    console.log('[inspecao_form] form/inputs não encontrados; abortando', {
      hasForm: !!form,
      hasLat: !!latInput,
      hasLng: !!lngInput,
    });
    return;
  }

  const clearErrorMeta = () => {
    if (errCodeInput) errCodeInput.value = '';
    if (errMessageInput) errMessageInput.value = '';
    if (errReasonInput) errReasonInput.value = '';
  };

  const showLocationMessage = (message, type = 'warning') => {
    if (!locationAlert) {
      alert(message);
      return;
    }
    locationAlert.textContent = message;
    locationAlert.classList.remove(
      'd-none',
      'alert-warning',
      'alert-success',
      'alert-danger'
    );
    locationAlert.classList.add(`alert-${type}`);
  };

  const hideLocationMessage = () => {
    if (locationAlert) {
      locationAlert.classList.add('d-none');
    }
  };

  const isLikelySecureForGeolocation = () => {
    const host = window.location.hostname;
    const isLocalhost =
      host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
    return window.isSecureContext || isLocalhost;
  };

  const getHighAccuracy = () => {
    const raw = (form.dataset.geoHighAccuracy || '').toLowerCase().trim();
    return raw === '1' || raw === 'true' || raw === 'yes';
  };

  const buildErrorReason = (error) => {
    const code = error && typeof error.code === 'number' ? error.code : null;
    const message = error && error.message ? String(error.message) : '';

    if (code === 1) return 'Permissão negada';
    if (code === 2) return 'Localização indisponível';
    if (code === 3) return 'Tempo excedido';
    if (message) return message;
    return 'Erro desconhecido';
  };

  const logDebugState = (eventName, extra = {}) => {
    const state = {
      origin: window.location.origin,
      hostname: window.location.hostname,
      isSecureContext: window.isSecureContext,
      geolocationExists: !!navigator.geolocation,
      likelySecure: isLikelySecureForGeolocation(),
      ...extra,
    };
    console.log(`[inspecao_form] ${eventName}`, state);
  };

  const requestLocationThenSubmit = (targetForm, trigger = 'unknown') => {
    clearErrorMeta();
    logDebugState('requestLocationThenSubmit()', { trigger });

    if (!navigator.geolocation) {
      const reason = 'Geolocation não suportado';
      if (errReasonInput) errReasonInput.value = reason;
      showLocationMessage(`${reason}. A inspeção será salva sem coordenadas.`, 'warning');
      targetForm.submit();
      return;
    }

    if (!isLikelySecureForGeolocation()) {
      showLocationMessage(
        'Seu navegador pode bloquear geolocalização em HTTP. Se não aparecer o popup, teste http://localhost:8000 (em vez de 127.0.0.1) ou use HTTPS. Vou tentar solicitar mesmo assim; se falhar, a inspeção será salva sem coordenadas.',
        'warning'
      );
    }

    const geoOptions = {
      enableHighAccuracy: getHighAccuracy(), // default false
      timeout: 15000,
      maximumAge: 60000,
    };

    showLocationMessage('Solicitando permissão de localização...', 'warning');
    logDebugState('antes getCurrentPosition', { geoOptions });

    try {
      navigator.geolocation.getCurrentPosition(
        function (position) {
          logDebugState('sucesso getCurrentPosition', {
            latitude: position?.coords?.latitude,
            longitude: position?.coords?.longitude,
            accuracy: position?.coords?.accuracy,
          });
          latInput.value = position.coords.latitude;
          lngInput.value = position.coords.longitude;
          hideLocationMessage();
          targetForm.submit();
        },
        function (error) {
          const reason = buildErrorReason(error);
          logDebugState('erro getCurrentPosition', {
            errorCode: error && typeof error.code === 'number' ? error.code : null,
            errorMessage: error && error.message ? String(error.message) : null,
            reason,
          });

          latInput.value = '';
          lngInput.value = '';
          if (errCodeInput && error && typeof error.code === 'number') {
            errCodeInput.value = String(error.code);
          }
          if (errMessageInput && error && error.message) {
            errMessageInput.value = String(error.message);
          }
          if (errReasonInput) {
            errReasonInput.value = reason;
          }

          showLocationMessage(
            `${reason}. A inspeção será salva sem coordenadas.`,
            'warning'
          );

          setTimeout(() => targetForm.submit(), 50);
        },
        geoOptions
      );
    } catch (err) {
      logDebugState('exceção getCurrentPosition', { err: String(err) });
      if (errReasonInput) errReasonInput.value = 'Erro ao solicitar geolocalização';
      showLocationMessage(
        'Erro ao solicitar geolocalização. A inspeção será salva sem coordenadas.',
        'warning'
      );
      targetForm.submit();
    }
  };

  form.addEventListener('submit', function (event) {
    logDebugState('submit interceptado', {
      trigger: 'submit',
      latPreenchida: !!latInput.value,
      lngPreenchida: !!lngInput.value,
    });

    if (latInput.value && lngInput.value) {
      hideLocationMessage();
      return;
    }

    event.preventDefault();
    requestLocationThenSubmit(form, 'submit');
  });
});
