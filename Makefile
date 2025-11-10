.PHONY: help run-local test-http stop clean

help:
	@echo "SoundCanvas - Available targets:"
	@echo "  run-local   - Start cpp-core and tf-serving services via Docker"
	@echo "  test-http   - Test the HTTP /generate endpoint"
	@echo "  stop        - Stop all Docker services"
	@echo "  clean       - Stop services and remove volumes"

run-local:
	cd infra && docker compose up --build cpp-core tf-serving

test-http:
	python3 scripts/test_http_generate.py cpp-core/examples/test_image.png

stop:
	cd infra && docker compose down

clean:
	cd infra && docker compose down -v