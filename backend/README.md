# ActionEngine Backend

This repository contains the backend for the ActionEngine project.

This is originally built off of [browser-use/web-ui](https://github.com/browser-use/web-ui), but modified to fit our usecase.

## Getting Started

Pre-requisites:

- uv

venv

```bash
uv venv --python 3.11
source .venv/bin/activate
```

Set up vscode by hitting CTRL+P and typing `>Python: Select Interpreter` and selecting the venv python.

Install dependencies

```bash
uv pip install -r requirements.txt
```

Run the noVNC server and other services with docker-compose

```bash
CHROME_PERSISTENT_SESSION=True && docker compose up --build
```

In another tab, run the API server

```bash
CHROME_PERSISTENT_SESSION=True && uvicorn backend.main:app --host 127.0.0.1 --port 7788 --reload
```
