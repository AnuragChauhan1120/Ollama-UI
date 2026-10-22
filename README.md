# Lightweight Ollama Web UI

A minimal, local-first web UI for [Ollama](https://ollama.com/) models. A small FastAPI backend talks directly to your local Ollama instance and streams responses to a plain HTML/CSS/JavaScript frontend.

It supports model selection, streaming responses, conversation history, image input, queued messages, stopping generation, and starting new chats.

<!-- Add a screenshot or GIF here: ![Ollama UI](docs/screenshot.png) -->

## Why this exists

I built this because heavier Ollama web interfaces felt slow for everyday use. The goal is a simple interface that stays close to using Ollama from the terminal: no framework, no build step, no extra services.

It is intentionally **not deployed**. The app has to talk to an Ollama instance running on your own machine, so hosting it in the cloud would only add a network hop and send your prompts off-device. Keeping everything local is the point.

---

## Features

- **Model selection**: automatically lists the models installed in Ollama
- **Streaming responses**: tokens appear as they are generated
- **Conversation history**: context is kept throughout a chat
- **Image input**: attach up to four local images to a message (vision-capable models only)
- **Stop generation**: cancel an ongoing response
- **Message queue**: multiple submitted messages are processed one at a time
- **New chat**: clear the conversation and start fresh
- **Persistent HTTP connection**: reuses a single `httpx.AsyncClient`
- **Runs locally**: prompts and inference stay on your machine
- **Lightweight**: FastAPI + vanilla HTML/CSS/JavaScript

---

## Architecture

```
┌─────────────────────────┐
│       Web Browser       │
│                         │
│  Chat UI                │
│  Model Selection        │
│  Message Queue          │
│  Stop / New Chat        │
└────────────┬────────────┘
             │
             │ HTTP / SSE
             ▼
┌─────────────────────────┐
│         FastAPI         │
│                         │
│  GET  /                 │
│  GET  /models           │
│  POST /chat             │
│                         │
│  Persistent HTTPX       │
│  Client                 │
└────────────┬────────────┘
             │
             │ HTTP Streaming
             ▼
┌─────────────────────────┐
│         Ollama          │
│    localhost:11434      │
│                         │
│  Qwen / Gemma / Llama   │
│  etc.                   │
└─────────────────────────┘
```

---

## Quick start

### Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- At least one locally installed Ollama model

### 1. Clone and install

```bash
git clone https://github.com/AnuragChauhan1120/Ollama-UI.git
cd Ollama-UI
pip install -r requirements.txt
```

### 2. Make sure Ollama has a model

```bash
ollama --version
ollama list
```

If you don't have a model yet, pull one:

```bash
ollama pull qwen3.5:4b
```

Any model supported by your Ollama installation works. For image input, pick a vision-capable model. In the Gemma 3 family, `gemma3:4b` and larger support images; `gemma3:270m` and `gemma3:1b` are text-only.

### 3. Run

Start Ollama (skip this if it is already running):

```bash
ollama serve
```

Then, from the project directory:

```bash
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> in your browser.

---

## Project structure

```
Ollama-UI/
├── main.py              # FastAPI backend
├── requirements.txt
├── static/
│   └── index.html       # Frontend (HTML, CSS, JavaScript)
└── README.md
```

---

## How it works

### Model discovery

The frontend requests `GET /models`. FastAPI forwards this to Ollama's `GET http://127.0.0.1:11434/api/tags`, and the returned models populate the model selector.

### Chat

The frontend sends `POST /chat`:

```json
{
  "model": "qwen3.5:4b",
  "messages": [
    {
      "role": "user",
      "content": "What is in this picture?",
      "images": ["base64-encoded-image"]
    }
  ]
}
```

Use the paperclip button in the composer to attach images. Only files you explicitly attach are sent, base64-encoded in the user message for Ollama's vision API.

FastAPI forwards the request to `http://127.0.0.1:11434/api/chat` with streaming enabled:

```json
{
  "model": "qwen3.5:4b",
  "messages": [],
  "stream": true,
  "think": false
}
```

### Streaming

Instead of waiting for the full response, the backend relays Ollama's streamed output as SSE-style events:

```
event: token
data: "Hello"

event: token
data: " there"

event: done
data: {}
```

The frontend reads these events and updates the assistant message incrementally.

### Message queue

The frontend keeps a queue of submitted messages and processes them sequentially rather than starting several generations at once. This avoids multiple local generations competing for the same GPU.

### Stopping generation

Each active request uses an `AbortController`. Pressing **Stop** aborts the current request in the browser.

### New chat

The **New Chat** button stops the current generation, clears queued messages and conversation history, and resets the interface.

### Conversation context

Conversation history is maintained by the frontend as a list of messages (`role` and `content`) and sent to Ollama with each request so the model keeps context.

---

## Design decisions

- **Local-first, not deployed.** The backend must reach Ollama on the same machine, so deployment would add latency and move prompts off-device without any benefit.
- **Vanilla frontend.** No framework or build step keeps startup instant and the code easy to read.
- **One pooled HTTP client.** A persistent `httpx.AsyncClient` with connection pooling avoids creating a new client per request.
- **Stream straight through.** Ollama's output is relayed to the browser as it arrives instead of being buffered.
- **Sequential queue.** One generation at a time is the right default for a single local GPU.

---

## Privacy

```
Browser → your FastAPI server → your local Ollama → your local model
```

No external LLM API is required. Prompts and responses stay on your machine unless you deliberately expose the app or connect it to an external service.

---

## Troubleshooting

**Ollama is not running.** Start it with `ollama serve`, then check with `ollama list`.

**No models appear.** Run `ollama list`. If it is empty, pull a model (for example `ollama pull qwen3.5:4b`) and refresh the page.

**FastAPI cannot connect to Ollama.** The app expects Ollama at `http://127.0.0.1:11434`. Make sure it is running on the same machine.

**Responses are slow.** Speed depends mainly on the model, quantization, available GPU/VRAM, and context length. Try a smaller model if your hardware struggles.

---

## Contributing

Bug fixes, improvements, and UI enhancements are welcome. Fork the repository, make your changes, and open a pull request.
