# Lightweight Ollama Web UI

A minimal, fast, locally hosted web UI for [Ollama](https://ollama.com/) models.

The application uses **FastAPI** as a lightweight backend and communicates directly with a locally running Ollama instance. It supports model selection, streaming responses, conversation history, queued messages, stopping generation, and starting new chats.

The goal is to provide a simple alternative to heavier Ollama web interfaces while keeping the experience close to using Ollama directly from the terminal.

---

## Features

* 🧠 **Model selection** — automatically loads models installed in Ollama
* ⚡ **Streaming responses** — responses appear as they are generated
* 💬 **Conversation history** — maintains context throughout a chat
* 🖼️ **Image input** — attach up to four local images to a message
* 🛑 **Stop generation** — cancel an ongoing response
* 📋 **Message queue** — multiple submitted messages are processed sequentially
* 🆕 **New chat** — clear the current conversation and start fresh
* 🔌 **Persistent HTTP connection** — reuses an `httpx.AsyncClient`
* 🔒 **Runs locally** — your prompts and model inference stay on your machine
* 🪶 **Lightweight** — FastAPI + vanilla HTML/CSS/JavaScript

---

## Architecture

```text
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
│  /                     │
│  /models               │
│  /chat                 │
│                         │
│  Persistent HTTPX       │
│  Client                │
└────────────┬────────────┘
             │
             │ HTTP Streaming
             ▼
┌─────────────────────────┐
│         Ollama          │
│    localhost:11434      │
│                         │
│  Qwen / Gemma / Llama  │
│  etc.                  │
└─────────────────────────┘
```

---

## Requirements

* Python 3.10+
* [Ollama](https://ollama.com/)
* A locally installed Ollama model

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn httpx
```

Or, if a `requirements.txt` file is provided:

```bash
pip install -r requirements.txt
```

---

## Install Ollama

Install Ollama from:

https://ollama.com/

Verify the installation:

```bash
ollama --version
```

Check your installed models:

```bash
ollama list
```

If you don't have a model yet, pull one:

```bash
ollama pull qwen3.5:4b
```

You can use any model supported by your Ollama installation.

For image descriptions, choose a vision-capable model. In the Gemma 3 family, `gemma3:4b` and larger support images; `gemma3:270m` and `gemma3:1b` are text-only.

---

## Run the Application

Start Ollama:

```bash
ollama serve
```

Then, from the project directory, start FastAPI:

```bash
uvicorn main:app --reload
```

Open the UI in your browser:

```text
http://127.0.0.1:8000
```

---

## Project Structure

```text
ollama-ui/
│
├── main.py
│
├── static/
│   └── index.html
│
└── README.md
```

---

## How It Works

### Model Discovery

The frontend requests:

```text
GET /models
```

FastAPI forwards this to Ollama:

```text
GET http://127.0.0.1:11434/api/tags
```

The returned models are displayed in the model selector.

---

### Chat

The frontend sends:

```text
POST /chat
```

with:

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

Use the paperclip button in the composer to select images. The browser only sends files you explicitly attach, encoded in the user message for Ollama's vision API.

FastAPI forwards the request to:

```text
http://127.0.0.1:11434/api/chat
```

with streaming enabled:

```json
{
  "model": "qwen3.5:4b",
  "messages": [],
  "stream": true,
  "think": false
}
```

---

## Streaming

Instead of waiting for the complete response, Ollama streams generated content.

```text
Ollama
   │
   ├── token
   ├── token
   ├── token
   ├── token
   ▼
FastAPI
   │
   ▼
Browser
   │
   ▼
Visible response
```

FastAPI converts the streamed response into SSE-style events:

```text
event: token
data: "Hello"

event: token
data: " there"

event: done
data: {}
```

The frontend reads these events and updates the assistant message incrementally.

---

## Message Queue

The frontend maintains a queue for submitted messages.

For example:

```text
Question 1
Question 2
Question 3
```

becomes:

```text
Queue
 ├── Question 1
 ├── Question 2
 └── Question 3
```

They are processed sequentially rather than starting multiple generations simultaneously.

This helps avoid multiple local model generations competing for GPU resources.

---

## Stopping Generation

Each active request uses an `AbortController`.

When **Stop** is pressed, the current request is aborted.

```text
Browser
   │
   │ generation request
   ▼
FastAPI → Ollama
   │
   │
   └── Stop → AbortController
```

---

## Starting a New Chat

The **New Chat** button:

* Stops the current generation
* Clears queued messages
* Clears conversation history
* Resets the interface
* Starts a new conversation

---

## Conversation Context

Conversation history is maintained by the frontend.

Messages are stored as:

```javascript
[
    {
        role: "user",
        content: "Hello"
    },
    {
        role: "assistant",
        content: "Hi!"
    }
]
```

This history is sent to Ollama with subsequent requests so the model can maintain conversational context.

---

## Performance

The application is intentionally lightweight.

The backend uses a persistent `httpx.AsyncClient` with connection pooling rather than creating a new HTTP client for every request.

The Ollama response is streamed directly through FastAPI rather than waiting for the entire response.

The application also avoids unnecessary frontend frameworks and uses plain HTML, CSS, and JavaScript.

---

## Privacy

This application is designed to run locally.

```text
Browser
   ↓
Your FastAPI server
   ↓
Your local Ollama
   ↓
Your local model
```

No external LLM API is required.

Your prompts and model responses remain on your machine unless you deliberately expose the application or connect it to an external service.

---

## Troubleshooting

### Ollama is not running

Start Ollama:

```bash
ollama serve
```

Verify:

```bash
ollama list
```

---

### No models appear

Check:

```bash
ollama list
```

If no models are installed:

```bash
ollama pull qwen3.5:4b
```

Then refresh the UI.

---

### FastAPI cannot connect to Ollama

The application expects Ollama at:

```text
http://127.0.0.1:11434
```

Make sure Ollama is running on the same machine.

---

### Response is slow

Generation speed primarily depends on the selected model, quantization, available GPU/VRAM, context length, and Ollama configuration.

Try a smaller model if your hardware struggles with larger models.


---

## Contributing

Contributions, improvements, bug fixes, and UI enhancements are welcome.

Fork the repository, make your changes, and open a pull request.
