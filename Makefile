.PHONY: streamlit phone dev-phone

streamlit:
	cd HealthCoachBackend && venv/bin/streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0

phone:
	./scripts/dev_phone.sh

dev-phone: phone
