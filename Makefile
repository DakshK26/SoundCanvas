# Root Makefile for SoundCanvas

.PHONY: help init format lint test build run-local

help:
\t@echo "Useful targets:"
\t@echo "  make init       # initial setup (dependencies, etc.)"
\t@echo "  make test       # run all tests"
\t@echo "  make build      # build all services"
\t@echo "  make run-local  # run local docker-compose stack"

init:
\t@echo "Phase 0: nothing to init yet. Fill this in later."

test:
\t@echo "Phase 0: no tests yet."

build:
\t@echo "Phase 0: nothing to build yet."

run-local:
\tdocker compose -f infra/docker-compose.yml up --build
