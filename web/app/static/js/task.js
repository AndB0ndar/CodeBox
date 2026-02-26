const taskId = window.location.pathname.split('/').pop();
const statusSpan = document.getElementById('status');
const languageSpan = document.getElementById('language');
const limitsSpan = document.getElementById('limits');
const codePre = document.getElementById('code');
const logsPre = document.getElementById('logs');
const exitCodeSpan = document.getElementById('exit_code');
const metricsDiv = document.getElementById('metrics');

let eventSource = null;


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

function fetchMetrics() {
    fetch(`/api/tasks/${taskId}/metrics`)
        .then(response => response.json())
        .then(metrics => {
            let html = '<ul>';
            if (metrics.max_cpu !== undefined) {
                html += `<li>Макс. CPU: ${metrics.max_cpu.toFixed(2)}%</li>`;
            }
            if (metrics.avg_cpu !== undefined) {
                html += `<li>Средн. CPU: ${metrics.avg_cpu.toFixed(2)}%</li>`;
            }
            if (metrics.max_memory !== undefined) {
                html += `<li>Макс. память: ${(metrics.max_memory / 1024 / 1024).toFixed(2)} MB</li>`;
            }
            if (metrics.avg_memory !== undefined) {
                html += `<li>Средн. память: ${(metrics.avg_memory / 1024 / 1024).toFixed(2)} MB</li>`;
            }
            html += '</ul>';
            metricsDiv.innerHTML = html;
        })
        .catch(error => {
            console.error('Ошибка загрузки метрик:', error);
            metricsDiv.innerHTML = '<p>Метрики недоступны.</p>';
        });
}

function fetchInitialTask() {
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            languageSpan.textContent = task.language;
            limitsSpan.textContent = `CPU: ${task.cpu_limit} ядер, Память: ${task.memory_limit}, Таймаут: ${task.timeout}с`;
            codePre.textContent = task.code;
        })
        .catch(error => console.error('Ошибка загрузки задачи:', error));
}

function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource(`/api/tasks/${taskId}/stream`);

    eventSource.addEventListener('status_update', function(event) {
        const data = JSON.parse(event.data);
        statusSpan.textContent = data.status;
        if (data.exit_code !== undefined) {
            exitCodeSpan.textContent = data.exit_code;
        }
        if (task.status === 'completed' || task.status === 'failed' || task.status === 'timeout') {
            eventSource.close();
            fetchLogs();
            fetchMetrics();
        }
    });

    eventSource.onerror = function() {
        console.error('SSE connection error, falling back to polling');
        eventSource.close();
        fallbackPolling();
    };
}

function fallbackPolling() {
    function poll() {
        fetch(`/api/tasks/${taskId}`)
            .then(response => response.json())
            .then(task => {
                statusSpan.textContent = task.status;
                if (task.status === 'completed' || task.status === 'failed' || task.status === 'timeout') {
                    fetchLogs();
                    fetchMetrics();
                } else {
                    setTimeout(poll, 2000);
                }
            })
            .catch(error => console.error('Polling error:', error));
    }
    poll();
}


fetchInitialTask();
connectSSE();

