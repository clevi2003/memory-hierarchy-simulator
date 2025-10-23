# Makefile
SHELL := /bin/bash
PY    := python3
APP   := memhier
CONFIG:= trace.config
MAIN  := main.py
TRACE ?= trace.dat

.PHONY: build run clean

build:
	@echo "Generating $(APP) wrapper..."
	@printf '%s\n' '#!/usr/bin/env bash'                                  >  $(APP)
	@printf '%s\n' 'set -euo pipefail'                                    >> $(APP)
	@printf '%s\n' 'SCRIPT_DIR="$$(cd "$$(dirname "$$0")" && pwd)"'       >> $(APP)
	@printf '%s\n' 'exec $(PY) "$${SCRIPT_DIR}/'$(strip $(MAIN))'" -t /dev/stdin "$$@"' >> $(APP)
	@chmod +x $(APP)
	@echo "Done. Run with: ./$(APP) < your_trace.dat"

run: build
	@./$(APP) < $(TRACE)

clean:
	@rm -f $(APP)

