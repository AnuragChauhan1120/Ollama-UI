from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx
import json

BASE_DIR = Path(__file__).resolve().parent
OLLAMA = "http://127.0.0.1:11434"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ollama = httpx.AsyncClient(
        timeout=httpx.Timeout(None, connect=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    yield
    await app.state.ollama.aclose()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
async def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/models")
async def models():
    try:
        r = await app.state.ollama.get(f"{OLLAMA}/api/tags")
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail="Could not reach Ollama") from error


@app.post("/chat")
async def chat(data: dict):
    if not data.get("model") or not isinstance(data.get("messages"), list):
        raise HTTPException(status_code=400, detail="A model and message list are required")

    try:
        request = app.state.ollama.build_request(
            "POST",
            f"{OLLAMA}/api/chat",
            json={
                "model": data["model"],
                "messages": data["messages"],
                "stream": True,
                "think": False,
            },
        )
        upstream = await app.state.ollama.send(request, stream=True)
        if upstream.is_error:
            detail = (await upstream.aread()).decode("utf-8", errors="replace")
            await upstream.aclose()
            raise HTTPException(status_code=upstream.status_code, detail=detail)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Could not reach Ollama: {error}") from error

    async def generate():
        sent_content = False
        saw_thinking = False
        try:
            async for line in upstream.aiter_lines():
                if not line:
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    yield f"event: error\ndata: {json.dumps({'message': 'Ollama sent an invalid stream chunk.'})}\n\n"
                    return

                if chunk.get("error"):
                    yield f"event: error\ndata: {json.dumps({'message': chunk['error']}, ensure_ascii=False)}\n\n"
                    return

                message = chunk.get("message") or {}
                saw_thinking = saw_thinking or bool(message.get("thinking"))
                content = message.get("content", "")
                if content:
                    sent_content = True
                    yield f"event: token\ndata: {json.dumps(content, ensure_ascii=False)}\n\n"
        except httpx.HTTPError as error:
            yield f"event: error\ndata: {json.dumps({'message': f'Ollama connection interrupted: {error}'})}\n\n"
        finally:
            await upstream.aclose()
        if not sent_content:
            detail = (
                "Ollama returned thinking but no answer text. The model may not honor think=false."
                if saw_thinking
                else "Ollama completed without returning message.content tokens. Check the selected model and Ollama output."
            )
            yield f"event: error\ndata: {json.dumps({'message': detail})}\n\n"
            return
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
