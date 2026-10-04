.DEFAULT_GOAL := help
.PHONY: help update test build build-deb build-pkg run run-backend run-frontend stop

help:
	@printf '%s\n' \
		'Available commands:' \
		'  make help          Show this command list' \
		'  make update        Install backend and frontend dependencies' \
		'  make test          Run backend and frontend tests' \
		'  make build         Build backend wheel and frontend bundle' \
		'  make build-deb     Build the dug Debian package in dist/' \
		'  make build-pkg     Build the dug macOS Installer package in dist/' \
		'  make run           Start both development servers' \
		'  make run-backend   Start only the API server' \
		'  make run-frontend  Start only the frontend server' \
		'  make stop          Stop local development servers'

update:
	cd backend && if [ -f uv.lock ]; then uv sync --extra test --locked; else uv sync --extra test; fi
	cd frontend && npm ci

test:
	cd backend && uv run --extra test pytest -q
	cd frontend && npm test

build:
	cd backend && uv build --wheel
	cd frontend && npm run build

build-deb:
	python3 scripts/build-dug-deb.py

build-pkg:
	python3 scripts/build-dug-pkg.py

run:
	$(MAKE) --no-print-directory -j2 run-backend run-frontend

run-backend:
	cd backend && uv run uvicorn app.main:app --reload

run-frontend:
	cd frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort

stop:
	@stopped=0; failed=0; \
	for port in 8000 5173; do \
		pids=$$(lsof -nP -tiTCP:$$port -sTCP:LISTEN 2>/dev/null || :); \
		for pid in $$pids; do \
			cwd=$$(lsof -a -p $$pid -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'); \
			case "$$port:$$cwd" in \
				"8000:$(CURDIR)"|"8000:$(CURDIR)/backend"|"5173:$(CURDIR)/frontend") \
					if kill $$pid; then \
						printf 'Stopped %s server (PID %s)\n' "$$port" "$$pid"; stopped=1; \
					else \
						printf 'Could not stop %s server (PID %s)\n' "$$port" "$$pid" >&2; failed=1; \
					fi ;; \
				*) printf 'Left unrelated process on port %s (PID %s) running\n' "$$port" "$$pid" ;; \
			esac; \
		done; \
	done; \
	if [ "$$stopped" -eq 0 ] && [ "$$failed" -eq 0 ]; then printf 'No project development servers found\n'; fi; \
	[ "$$failed" -eq 0 ]
