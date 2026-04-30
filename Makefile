.PHONY: help backend backend-log backend-stop streamlit streamlit-8502 phone dev-phone

BACKEND_DIR := HealthCoachBackend
BACKEND_PORT ?= 8000
STREAMLIT_PORT ?= 8501
STREAMLIT_ALT_PORT ?= 8502
BACKEND_LOG := $(BACKEND_DIR)/.dev_backend.log
BACKEND_PID_FILE := $(BACKEND_DIR)/.dev_backend.pid

help:
	@echo "Targets disponibles:"
	@echo "  make backend         - lance le backend FastAPI en local"
	@echo "  make backend-log     - suit les logs du backend"
	@echo "  make backend-stop    - arrete le backend local"
	@echo "  make streamlit       - lance Streamlit sur le port $(STREAMLIT_PORT)"
	@echo "  make streamlit-8502  - lance Streamlit sur le port $(STREAMLIT_ALT_PORT)"
	@echo "  make phone           - backend + build + install + lancement iPhone"
	@echo "  make dev-phone       - alias de phone"

backend:
	cd $(BACKEND_DIR) && venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $(BACKEND_PORT)

backend-log:
	tail -f "$(BACKEND_LOG)"

backend-stop:
	@if [ -f "$(BACKEND_PID_FILE)" ]; then \
		PID=$$(cat "$(BACKEND_PID_FILE)"); \
		echo "Arret backend PID $$PID"; \
		kill $$PID || true; \
	else \
		echo "Aucun fichier PID backend trouve."; \
	fi

streamlit:
	cd $(BACKEND_DIR) && venv/bin/streamlit run streamlit_app/app.py --server.port $(STREAMLIT_PORT) --server.address 0.0.0.0

streamlit-8502:
	cd $(BACKEND_DIR) && venv/bin/streamlit run streamlit_app/app.py --server.port $(STREAMLIT_ALT_PORT) --server.address 0.0.0.0

phone:
	./scripts/dev_phone.sh

dev-phone: phone
