document.addEventListener('DOMContentLoaded', function () {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrftoken = getCookie('csrftoken');
  const currentUserLevel = document.body?.dataset?.userLevel || '';
  const progressSpans = document.querySelectorAll('.task-progress');

  progressSpans.forEach(span => {
    if (span.dataset.canEdit !== 'true') {
      return;
    }
    span.addEventListener('click', function () {
      const taskId = this.dataset.taskId;
      const categoryId = this.dataset.categoryId;
      const isLockedForLevel1 = this.dataset.lockLevel1 === 'true';
      const lockMessage = this.dataset.lockMessage || 'Tarefa bloqueada. Solicite apoio de um usuário Nível 2.';

      if (currentUserLevel === 'nivel1' && isLockedForLevel1) {
        alert(lockMessage);
        return;
      }

      const currentProgress = this.textContent.replace('%', '');
      const input = document.createElement('input');
      input.type = 'range';
      input.min = 0;
      input.max = 100;
      input.value = currentProgress;
      input.classList.add('form-range');
      input.style.width = '120px';

      this.style.display = 'none';
      this.parentNode.insertBefore(input, this.nextSibling);
      input.focus();

      const cleanup = () => {
        if (input.parentNode) {
          input.parentNode.removeChild(input);
        }
        span.style.display = 'inline-block';
      };

      const handleUpdate = function() {
        input.removeEventListener('change', handleUpdate);
        input.removeEventListener('blur', handleUpdate);

        const newProgress = input.value;
        if (newProgress == 100) {
          if (!confirm('Confirma a finalização desta tarefa? A data de conclusão será registrada.')) {
            cleanup();
            return;
          }
        }

        fetch(window.updateTaskProgressUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
          },
          body: JSON.stringify({ task_id: taskId, progress: newProgress })
        })
        .then(response => response.json())
        .then(data => {
          if (data.status === 'success') {
            span.textContent = `${newProgress}%`;
            if (currentUserLevel === 'nivel1') {
              span.dataset.lockLevel1 = data.task_completed ? 'true' : 'false';
            }

            const categoryProgressDiv = document.querySelector(`.category-progress[data-category-id="${categoryId}"] .progress-bar`);
            if (categoryProgressDiv) {
              categoryProgressDiv.style.width = data.new_category_progress + '%';
              const label = categoryProgressDiv.querySelector('.progress-label');
              if (label) { label.textContent = data.new_category_progress + '%'; }
            }

            const statusWrapper = document.getElementById(`task-status-wrapper-${taskId}`);
            if (statusWrapper) {
              const statusBadge = statusWrapper.querySelector('.badge');
              if (statusBadge) {
                statusBadge.textContent = data.task_status_display;
                statusBadge.classList.remove('bg-success', 'bg-primary', 'bg-warning', 'bg-secondary', 'text-dark');
                if (data.task_status === 'concluida') {
                  statusBadge.classList.add('bg-success');
                } else if (data.task_status === 'andamento') {
                  statusBadge.classList.add('bg-primary');
                } else if (data.task_status === 'bloqueada') {
                  statusBadge.classList.add('bg-warning', 'text-dark');
                } else {
                  statusBadge.classList.add('bg-secondary');
                }
              }
              const dateWrapper = document.getElementById(`task-date-wrapper-${taskId}`);
              if (dateWrapper && data.task_real_end_date) {
                dateWrapper.innerHTML = `<strong>Concluído em: ${data.task_real_end_date}</strong>`;
              }
            }
          } else if (data.message) {
            alert(data.message);
          }
        })
        .catch(() => {
          alert('Não foi possível atualizar a tarefa.');
        })
        .finally(() => {
          cleanup();
        });
      };

      input.addEventListener('change', handleUpdate);
      input.addEventListener('blur', handleUpdate);
    });
  });
});
