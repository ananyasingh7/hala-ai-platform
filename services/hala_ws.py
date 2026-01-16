import json
import os

import websockets

DEFAULT_WS_URL = "ws://localhost:8000/ws/chat/v2"


async def query_hala(
    prompt,
    session_id,
    max_tokens=512,
    system_prompt=None,
    start_session=False,
    include_history=False,
    history_window=1,
    ws_url=None,
):
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "session_id": session_id,
        "include_history": include_history,
        "history_window": history_window,
    }
    if system_prompt:
        payload["system_prompt"] = system_prompt

    endpoint = ws_url or os.getenv("HALA_WS_URL", DEFAULT_WS_URL)
    async with websockets.connect(endpoint) as ws:
        if start_session:
            await ws.send(json.dumps({"type": "session_start", "session_id": session_id}))
        await ws.send(json.dumps(payload))

        tokens = []
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            if msg_type == "token":
                tokens.append(data.get("content", ""))
            elif msg_type == "end":
                break
            elif msg_type == "error":
                raise RuntimeError(data.get("detail", "Unknown error from HalaAI"))

    return "".join(tokens).strip()
