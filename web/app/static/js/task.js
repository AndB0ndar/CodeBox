const taskId = window.location.pathname.split('/').pop();
const statusSpan = document.getElementById('status');
const languageSpan = document.getElementById('language');
const codePre = document.getElementById('code');
const logsPre = document.getElementById('logs');
const exitCodeSpan = document.getElementById('exit_code');


function fetchTask() {
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            statusSpan.textContent = task.status;
            languageSpan.textContent = task.language;
            codePre.textContent = task.code;
            exitCodeSpan.textContent = task.exit_code !== null ? task.exit_code : '—';

            if (task.status === 'completed' || task.status === 'failed') {
                fetchLogs();
            } else {
                logsPre.textContent = 'Логи появятся после завершения...';
                setTimeout(fetchTask, 2000);
            }
        })
        .catch(error => {
            console.error('Ошибка:', error);
            statusSpan.textContent = 'ошибка загрузки';
        });
}

function fetchLogs() {
    fetch(`/api/tasks/${taskId}/logs`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load logs');
            }
            return response.text();
        })
        .then(logText => {
            logsPre.textContent = logText;
        })
        .catch(error => {
            console.error('Ошибка загрузки логов:', error);
            logsPre.textContent = 'Не удалось загрузить логи.';
        });
}

fetchTask();

