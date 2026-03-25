# WebAI-Agent — Website Assistant

A lightweight web assistant that powers a friendly chat widget on your website. This project shows how to index your website code into a vector store, use a retrieval-augmented generation (RAG) chain with Gemini (Google) embeddings + LLM, and serve a small FastAPI endpoint that your front-end can call.

This README explains what the project does, how to set it up, and provides a ready-to-use "Try it" button you can drop onto slmgx.live.

---

## What this does (short, human-friendly)

This repository powers a small, on-site assistant (Maleesha’s Assistant) that:
- Reads your website source code and text, slices it into chunks, and stores semantic vectors in MongoDB Atlas.
- Uses Google/Gemini embeddings to retrieve relevant code/text based on a visitor’s question.
- Sends those retrieved snippets to a Gemini chat LLM to produce a helpful, context-aware answer.
- Serves an API endpoint (`/chat`) that the website’s chat widget calls to get answers.

It’s designed to be friendly and practical — not just “AI speak”. You control the data indexed, the system prompt, and how answers are shown on your site.

---

## Live demo / Try it on your site

Add this button anywhere on your site (for example, on https://slmgx.live). It opens the chat widget (or links to the chat page). Replace the URL if you host the chat API under a different domain/path.

HTML snippet (Tailwind-styled button — drop into your page markup):
```html
<!-- Try it on slmgx.live -->
<a href="https://slmgx.live" target="_blank" rel="noopener noreferrer"
   class="inline-block bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700 transition">
  Try Maleesha's Assistant
</a>
```

If your chat widget is embedded on the same site and you want a floating button to open it, use this (adjust selector/IDs to match your widget implementation):
```html
<!-- Floating button to open the site chat (adjust to your chat code) -->
<button id="open-site-chat" class="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700">
  Try the Assistant
</button>

<script>
document.getElementById('open-site-chat').addEventListener('click', () => {
  // If your chat widget exposes a global open() function, call it:
  if (window.openSiteChat) { window.openSiteChat(); return; }
  // Otherwise navigate to the chat page:
  window.location.href = "/"; // or "/chat" or "https://slmgx.live"
});
</script>
```

---

## Quick architecture overview

- Front-end: sample__index.html — simple floating chat UI calling the FastAPI endpoint.
- Backend: sample_app.py — FastAPI app that:
  - Loads vectors from MongoDB Atlas via a vector-store wrapper.
  - Uses a retriever to fetch top-k documents.
  - Fills a chat prompt template with retrieved context and the user's question.
  - Sends that prompt to Google Generative AI (Gemini) to generate an answer.
- Ingestion: vectordb_converter.py — walks a code directory, splits files into chunks, vectorizes with Gemini embeddings, and uploads them to MongoDB Atlas.

---

## Prerequisites

- Python 3.10+ (tested with 3.10–3.11)
- A MongoDB Atlas cluster (or another MongoDB instance reachable from your server)
- A Google API key with access to Gemini / Generative AI (or the equivalent configured SDK credentials)
- A server or hosting to run the FastAPI application (local or production). For production: use a process manager or Docker + reverse proxy (nginx).
- Optional: Tailwind CSS is loaded via CDN in the sample front-end.

---

## Setup guide (step-by-step)

1. Clone the repo
   ```bash
   git clone https://github.com/SL-MGx03/WebAI-Agent.git
   cd WebAI-Agent
   ```

2. Create a virtual environment and install dependencies
   (There is no requirements.txt in the repo; below is a minimal example. Adjust versions as needed.)
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip

   # example install; your project may require additional packages
   pip install fastapi uvicorn python-dotenv pymongo
   # The repo uses language-specific connectors — install them if available in PyPI:
   pip install langchain-google-genai langchain-mongodb langchain-community langchain-text-splitters
   ```
   Note: package names for Google/Gemini connectors may vary; follow vendor docs if pip can't find a package.

3. Create a `.env` file at the project root with:
   ```
   MONGODB_URI="your-mongodb-connection-string"
   GOOGLE_API_KEY="your-google-api-key"
   ```
   - Keep `.env` out of version control.
   - Make sure the MongoDB user has write/read permissions on the target database.

4. Index your website code into MongoDB (ingestion)
   - Edit `vectordb_converter.py` — set the path you want to index:
     - Replace `ingest_local_code(r"/yourfilepath")` with the path to your site source files.
     - The script ignores sensitive folders by default: `.git`, `node_modules`, `__pycache__`, `.env`, `venv`, `private_keys`.
   - Run the script:
     ```bash
     python vectordb_converter.py
     ```
   - Wait for all chunks to upload. The script batches uploads and includes delays to help with rate limits.

5. Update the front-end fetch URL (important)
   - Open `sample__index.html` and change the fetch endpoint inside the script:
     ```js
     // from:
     fetch('http://127.0.0.1:8000/chat', { ... })
     // to:
     fetch('https://slmgx.live/chat', { ... })   // or relative path '/chat' if hosted same origin
     ```
   - If you use HTTPS in production, make sure the backend is served over HTTPS and CORS is configured appropriately.

6. Run the backend (development)
   ```bash
   uvicorn sample_app:app --host 0.0.0.0 --port 8000 --reload
   ```
   - For production, run behind nginx with HTTPS and a process manager (systemd, gunicorn with uvicorn workers, or Docker).

7. Try it
   - Open `sample__index.html` in a browser (or deploy it to your site).
   - Type a question; the widget will call `/chat` and display the returned answer.

---

## Configuration tips & security

- Do NOT index secrets or private files. The ingestion script already excludes common sensitive folders, but always double-check the input folder before running.
- Use environment variables for credentials and never commit them.
- If you deploy publicly, enable authentication and rate-limiting on your API, and restrict origins in CORS.
- Monitor token / request usage for your Google/Gemini account — the ingestion step and LLM calls may consume quota.

---

## Troubleshooting

- CORS errors: set allowed origins on FastAPI (see `sample_app.py` CORSMiddleware). For production, avoid `allow_origins=["*"]`; use the specific domain(s).
- Connection refused: ensure uvicorn is running and port is open. If using nginx, confirm proxy pass settings.
- Rate limits / 429s during ingestion: vectordb_converter has sleep and retry logic; increase delays if you hit the quota.
- Module import errors for language connectors: verify the connector package names and versions. Some SDKs/bridges may be named differently or require vendor SDK configuration.

---

## Where to customize

- System prompt: edit the `system_prompt` variable in `sample_app.py`. This is where you tell the assistant what tone to use and what to prioritize.
- Retrieval settings: change `retriever = vector_store.as_retriever(search_kwargs={"k": 5})` to adjust how many documents are fetched.
- Models: `GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview", ...)` and `ChatGoogleGenerativeAI(model="gemini-2.5-flash", ...)` can be swapped for other models if available.
- Front-end UI: `sample__index.html` is a basic example — adjust styling, message formatting, and behavior to match your brand.

---

## Files of interest

- sample__index.html — front-end chat widget example (Tailwind via CDN).
- sample_app.py — FastAPI backend and RAG pipeline setup.
- vectordb_converter.py — local file ingestion and vector upload helper.

---

## License & contact

This project is provided as-is for demonstration and internal use. If you want help deploying this on slmgx.live or want a tailored install, contact the repo owner (SL-MGx03) or open an issue with "Deployment help" and steps you've tried.

---

Thanks for building a helpful, human-first assistant. If you'd like, I can:
- Provide a sample production-ready Dockerfile and nginx configuration.
- Create a ready-to-commit requirements.txt and .env.example.
- Produce a polished floating chat button that directly toggles the widget on your site.
