# Atalhos para o dia a dia. Tudo roda dentro do container.
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help build up down restart logs ps dev shell clean

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Constrói a imagem Docker
	$(COMPOSE) build

up: ## Sobe a aplicação em background (http://localhost:8501)
	$(COMPOSE) up -d --build

down: ## Para e remove os containers
	$(COMPOSE) down

restart: down up ## Reinicia a aplicação

logs: ## Acompanha os logs
	$(COMPOSE) logs -f managerpdf

ps: ## Mostra o status dos containers
	$(COMPOSE) ps

dev: ## Modo desenvolvimento com hot reload (http://localhost:8502)
	$(COMPOSE) --profile dev up --build

shell: ## Abre um shell dentro do container
	$(COMPOSE) run --rm --entrypoint bash managerpdf

clean: ## Remove containers, imagens e volumes do projeto
	$(COMPOSE) --profile dev down -v --rmi local --remove-orphans
