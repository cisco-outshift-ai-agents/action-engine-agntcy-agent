import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.utils.default_config_settings import default_config
from webui import run_with_stream

app = FastAPI(title="ActionEngine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default configuration
DEFAULT_CONFIG = default_config()

@app.get("/status")
async def status():
    return {"status": "ok"}

# WebSocker endpoint for chat interactions
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket): 
    await websocket.accept()
    try: 
        while True: 
            data = await websocket.receive_text()
            print(f"Received data: {data}")

            client_payload = json.loads(data)
            task = client_payload.get("task", DEFAULT_CONFIG["task"])

            # Merge with default configuration
            config = DEFAULT_CONFIG.copy()
            config["task"] = task

            async for update in run_with_stream(
                llm_provider=config["llm_provider"],
                llm_model_name=config["llm_model_name"],  
                llm_temperature=config["llm_temperature"],
                llm_base_url=config["llm_base_url"],
                llm_api_key=config["llm_api_key"],
                use_own_browser=config["use_own_browser"],
                keep_browser_open=config["keep_browser_open"],
                headless=config["headless"],
                disable_security=config["disable_security"],
                window_w=config["window_w"],
                window_h=config["window_h"],
                save_recording_path=config["save_recording_path"],
                save_agent_history_path=config["save_agent_history_path"],
                save_trace_path=config["save_trace_path"],
                enable_recording=config["enable_recording"],
                task=config["task"],
                add_infos="", 
                max_steps=config["max_steps"],
                use_vision=config["use_vision"],
                max_actions_per_step=config["max_actions_per_step"],
                tool_calling_method=config["tool_calling_method"],
            ): 
                await websocket.send_text(json.dumps(update))
    except WebSocketDisconnect:
        print("Chat WebSocket disconnected")
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        await websocket.close()