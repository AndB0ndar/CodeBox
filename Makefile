.PHONY: help build up down logs clean install-deps dev-backend dev-worker dev-web venv install clean-venv


COMPOSE_FILE := docker/docker-compose.yml
#COMPOSE_MONITORING := docker/docker-compose.monitoring.yml
VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

GREEN := \033[0;32m
NC := \033[0m


help:
	@echo "$(GREEN)Доступные команды:$(NC)"
	@echo "  make venv           - Создать виртуальное окружение в $(VENV_DIR)"
	@echo "  make install        - Установить зависимости (основные + dev) в виртуальное окружение"
	@echo "  make clean-venv     - Удалить виртуальное окружение"
	@echo "  make build          - Сборка Docker образов"
	@echo "  make up             - Запуск всех сервисов в фоне (использует $(COMPOSE_FILE))"
	#@echo "  make up-monitoring  - Запуск сервисов мониторинга (Prometheus, Grafana, Loki)"
	@echo "  make down           - Остановка и удаление контейнеров"
	@echo "  make logs           - Просмотр логов всех сервисов"
	#@echo "  make test           - Запуск тестов (pytest) в виртуальном окружении"
	@echo "  make clean          - Полная очистка Docker (остановка, удаление томов, образов)"
	@echo "  make dev-backend    - Запуск backend в режиме разработки (локально, из виртуального окружения)"
	@echo "  make dev-worker     - Запуск worker в режиме разработки (локально, из виртуального окружения)"
	@echo "  make dev-web        - Запуск web в режиме разработки (локально, из виртуального окружения)"


venv: $(VENV_DIR)
	python3 -m venv $(VENV_DIR)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

clean-venv:
	rm -rf $(VENV_DIR)


# Docker
build:
	docker-compose -f $(COMPOSE_FILE) build

up:
	docker-compose -f $(COMPOSE_FILE) up -d

#up-monitoring:
	#docker-compose -f $(COMPOSE_MONITORING) up -d

down:
	docker-compose -f $(COMPOSE_FILE) down

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

clean:
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all


# Tests
#test: venv
	#$(PYTHON) -m pytest tests/ -v --cov=backend --cov=worker --cov=web --cov-report=term-missing


dev-backend: venv
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: venv
	cd worker && $(PYTHON) -m app.worker

dev-web: venv
	cd web && $(PYTHON) -m flask run --host 0.0.0.0 --port 5000 --debug

