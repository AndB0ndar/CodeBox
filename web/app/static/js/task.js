const taskId = window.location.pathname.split('/').pop();
const statusSpan = document.getElementById('status');
const languageSpan = document.getElementById('language');
const limitsGrid = document.getElementById('limits-grid');
const codePre = document.getElementById('code-content');
const logsPre = document.getElementById('logs-content');
const exitCodeSpan = document.getElementById('exit_code');
const metricsDiv = document.getElementById('metrics');


function setStatusClass(status) {
    statusSpan.className = statusSpan.className.split(' ').filter(c => !c.startsWith('status--')).join(' ');
    statusSpan.classList.add('status');
    statusSpan.classList.add(`status--${status}`);
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
            console.error('Load logs error:', error);
            logsPre.textContent = 'Не удалось загрузить логи.';
        });
}

function fetchMetrics() {
    fetch(`/api/tasks/${taskId}/metrics`)
        .then(response => response.json())
        .then(metrics => {
            let html = '';
            if (metrics.max_cpu !== undefined) {
                html += `<div class="metrics__item">
                    <div class="metrics__label">Макс. CPU</div>
                    <div class="metrics__value">${metrics.max_cpu.toFixed(2)}<span class="metrics__unit">%</span></div>
                </div>`;
            }
            if (metrics.avg_cpu !== undefined) {
                html += `<div class="metrics__item">
                    <div class="metrics__label">Средн. CPU</div>
                    <div class="metrics__value">${metrics.avg_cpu.toFixed(2)}<span class="metrics__unit">%</span></div>
                </div>`;
            }
            if (metrics.max_memory !== undefined) {
                html += `<div class="metrics__item">
                    <div class="metrics__label">Макс. память</div>
                    <div class="metrics__value">${(metrics.max_memory / 1024 / 1024).toFixed(2)}<span class="metrics__unit">MB</span></div>
                </div>`;
            }
            if (metrics.avg_memory !== undefined) {
                html += `<div class="metrics__item">
                    <div class="metrics__label">Средн. память</div>
                    <div class="metrics__value">${(metrics.avg_memory / 1024 / 1024).toFixed(2)}<span class="metrics__unit">MB</span></div>
                </div>`;
            }
            metricsDiv.innerHTML = html;
        })
        .catch(error => {
            console.error('Ошибка загрузки метрик:', error);
            metricsDiv.innerHTML = '<p class="metrics__item">Метрики недоступны.</p>';
        });
}

function connectSSE() {
    const source = new EventSource(`/api/tasks/${taskId}/stream`);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setStatusClass(data.status);
        exitCodeSpan.textContent = data.exit_code !== null ? data.exit_code : '—';
    };

    source.addEventListener('done', (event) => {
        source.close();

        fetchLogs();
        fetchMetrics();
    });

    source.addEventListener('error', (event) => {
        console.error('SSE error', event);
        if (event.data) {
            alert('Server error: ' + event.data);
        }
        statusSpan.textContent = 'SSE error';
    });

    source.onerror = (error) => {
        console.error('Connection close or error:', error);
    };
}

function setLimitsGrid(task) {
    if (limitsGrid) {
        limitsGrid.innerHTML = `
            <div class="limit-badge">
                <span class="limit-badge__icon">🧠</span>
                <span class="limit-badge__label">CPU:</span>
                <span class="limit-badge__value">${task.cpu_limit}</span>
                <span>ядер</span>
            </div>
            <div class="limit-badge">
                <span class="limit-badge__icon">💾</span>
                <span class="limit-badge__label">Память:</span>
                <span class="limit-badge__value">${task.memory_limit}</span>
            </div>
            <div class="limit-badge">
                <span class="limit-badge__icon">⏱️</span>
                <span class="limit-badge__label">Таймаут:</span>
                <span class="limit-badge__value">${task.timeout}</span>
                <span>с</span>
            </div>
        `;
    }
}

function fetchInitialTask() {
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            languageSpan.textContent = task.language;
            setLimitsGrid(task);
            codePre.textContent = task.code;
            hljs.highlightElement(codePre);
        })
        .catch(error => console.error('Ошибка загрузки задачи:', error));
}


function setupCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const targetId = btn.getAttribute('data-clipboard-target');
            const target = document.querySelector(targetId);
            if (target) {
                try {
                    await navigator.clipboard.writeText(target.textContent);
                    btn.textContent = 'Скопировано!';
                    btn.classList.add('copied');
                    setTimeout(() => {
                        btn.textContent = 'Копировать';
                        btn.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    console.error('Ошибка копирования:', err);
                    btn.textContent = 'Ошибка';
                    setTimeout(() => btn.textContent = 'Копировать', 1500);
                }
            }
        });
    });
}


document.addEventListener('DOMContentLoaded', () => {
    fetchInitialTask();
    connectSSE();
    setupCopyButtons();
});
