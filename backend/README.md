# ActionEngine Backend

This repository contains the backend for the ActionEngine project.

This is originally built off of [browser-use/web-ui](https://github.com/browser-use/web-ui), but modified to fit our usecase.

## Getting Started

Pre-requisites:

```
brew install uv
```

Set up venv

```bash
uv venv --python 3.11
source .venv/bin/activate
```

Set up vscode by hitting CTRL+P and typing `>Python: Select Interpreter` and selecting the venv python.

Install dependencies

```bash
uv pip install -r requirements.txt
```

Copy .env

```bash
cp .env.example .env
```

Add your AI credentials to the .env file

Run the noVNC server and other services with docker-compose

```bash
source .env && docker compose up --build
```

In another tab, run the API server

```bash
CHROME_PERSISTENT_SESSION=True && uvicorn main:app --host 127.0.0.1 --port 7788 --reload
```

## Using Qwen2.5-VL as the backend model

Qwen2.5-VL is the new flagship vision-language model of Qwen and also a significant leap from the previous Qwen2-VL. It supports computer/phone use out of the box, understands visual localization and generates structured outputs.

### Please use the following fields in the .env file

```env
LLM_PROVIDER="openai"
LLM_MODEL_NAME="Qwen/Qwen2.5-VL-7B-Instruct"
LLM_TEMPERATURE=0.0
LLM_BASE_URL="http://host.docker.internal:8000/v1"
LLM_API_KEY="action_engine"
```

### Launch the vLLM server with local model backend

1. `ssh sreadmin@172.18.62.180` [Please contact julvalen@cisco.com or aditrame@cisco.com for access to the machine]
2. `cd` to our action_engine directory

```bash
cd /home/sreadmin/action_engine
```

2. Activate the venv or install the vllm runtime

```
source ae_env/bin/activate
```

or

```
pip install vllm
```

3. Start the server (Note that the model weights are currently stored in `/home/sreadmin/action_engine/qwen_vision/qwen2.5-vl-7b-instruct`)

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct --download-dir ./qwen_vision/qwen2.5-vl-7b-instruct --trust-remote-code --max-model-len 32768 --port 8000 --host 0.0.0.0 --dtype bfloat16 --limit-mm-per-prompt image=5,video=5 --api-key action_engine --enable-auto-tool-choice --tool-call-parser hermes
```

4. To use the quantized version of the model (the model weights are stored in `/home/sreadmin/action_engine/qwen_vision/qwen2.5-vl-7b-instruct-awq`)

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ --download-dir ./qwen_vision/qwen2.5-vl-7b-instruct-awq --quantization awq_marlin --trust-remote-code --max-model-len 128000 --port 8000 --host 0.0.0.0 --dtype float16 --limit-mm-per-prompt image=5,video=5 --api-key action_engine --enable-auto-tool-choice --tool-call-parser hermes
```

This uses Activation-aware Weight Quantization (AWQ) to provide inference speedup. It also uses the Marlin kernel for speedup on top of AWQ!
As with most quantization methods this comes at the cost of performance.

5. In order to extend the context length from the original 32k to 128k we use YaRN. In order to enable YaRN please use the following command (this can be used with the non quantized model as well)

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ --download-dir ./qwen_vision/qwen2.5-vl-7b-instruct-awq --quantization awq_marlin --trust-remote-code --max-model-len 128000 --port 8000 --host 0.0.0.0 --dtype float16 --limit-mm-per-prompt image=5,video=5 --api-key action_engine --rope-scaling '{"rope_type":"yarn","mrope_section": [ 16, 24, 24 ], "factor":4.0, "original_max_position_embeddings":32768}' --enable-auto-tool-choice --tool-call-parser hermes
```

Note: This has a significant impact on the performance of temporal and spatial localization tasks, and is therefore not recommended for use. It also impacts shorter context text performance since it uses static YaRN.

6. Now the server is running. Tunnel your local machine to the server in a separate terminal window.

```bash
ssh -L 8000:localhost:8000 sreadmin@172.18.62.180
```

Now you can make a request with the normal OpenAI-compatible API requests:

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer action_engine" \
-d '{
  "model": "Qwen/Qwen2.5-VL-7B-Instruct",
  "messages": [{"role": "user", "content": "What is the capital of France?"}],
  "temperature": 0.7,
  "max_tokens": 100
}'
```
