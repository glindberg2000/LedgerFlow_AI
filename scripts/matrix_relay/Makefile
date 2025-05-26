.PHONY: start stop restart status logs shell install relay

# Server control
start:
	docker-compose up -d
	@echo "Matrix server starting at http://localhost:8008"
	@echo "Element web client available at http://localhost:8009"
	@echo "Wait ~30 seconds for initialization to complete"

stop:
	docker-compose down

restart: stop start

status:
	@docker-compose ps

logs:
	docker-compose logs -f

shell:
	docker-compose exec synapse /bin/bash

# Client setup
install:
	pip install -r requirements.txt

# Relay
relay:
	python3 matrix_relay.py

relay-bg:
	nohup python3 matrix_relay.py > relay.log 2>&1 &
	@echo "Relay running in background. Check relay.log for output."
	@echo "To stop: find the PID with 'ps aux | grep matrix_relay' and kill it."

help:
	@echo "Matrix Relay Makefile Commands:"
	@echo "  make start      - Start Matrix server"
	@echo "  make stop       - Stop Matrix server"
	@echo "  make restart    - Restart Matrix server"
	@echo "  make status     - Show container status"
	@echo "  make logs       - Show server logs"
	@echo "  make shell      - Open shell in synapse container"
	@echo "  make install    - Install Python dependencies"
	@echo "  make relay      - Run relay client"
	@echo "  make relay-bg   - Run relay in background"
	@echo "  make help       - Show this help" 