# EduGenie 2.0 – AI-Powered Adaptive Learning Platform

A FastAPI backend + vanilla HTML/CSS/JS frontend implementing:

- Learner profiles (name, level, language)
- Gemini-powered question answering and explanations
- RAG: upload your own study materials (PDF) and get answers grounded in them
- Adaptive quizzes that raise/lower difficulty based on your score
- Dynamic learning paths that reorder around your weak topics
- A Learn → Assess → Analyze → Adapt feedback loop
- A progress dashboard (scores by topic, weak topics)

## 1. Setup

```bash
cd edugenie2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your real Gemini API key (get one free at
https://aistudio.google.com/app/apikey). The app will still run without a
key — `/ask` and quiz/path generation will return a placeholder message
instead of real AI output, so you can build and test everything else first.

## 2. Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser.

## 3. First run on Mac M1 — RAG note

The first time you upload a document, `sentence-transformers` downloads the
`all-MiniLM-L6-v2` embedding model (~90MB) from Hugging Face. This needs an
internet connection once; after that it's cached locally and runs on CPU.

## 4. Project structure

```
app/
  main.py              FastAPI app, user endpoints, mounts routers + static
  database.py          SQLAlchemy engine/session
  models.py            User, Interaction, QuizAttempt, LearningPathItem
  routers/
    chat.py            /api/ask, /api/history
    quiz.py            /api/quiz/generate, /api/quiz/submit
    upload.py          /api/upload (PDF ingestion for RAG)
    progress.py        /api/progress/{user_id}
    path.py            /api/path/generate, /api/path/{user_id}
  services/
    gemini_service.py  Gemini API wrapper (ask, ask_json)
    rag_service.py     Chunking, embedding, ChromaDB retrieval
    adaptive_service.py Difficulty adjustment, weak-topic detection, feedback loop
static/                style.css, app.js
templates/index.html   Single-page frontend
```

## 5. Demo script (matches the project's stated scenarios)

1. Create a profile.
2. Ask: "Which is the largest ocean?" (no RAG) — general knowledge answer.
3. Upload a PDF of SQL notes, then ask an SQL question with "Answer from my
   uploaded materials" checked — grounded answer with a source filename.
4. Generate a quiz on "Pythagoras Theorem," answer it, submit — see the
   score, the suggested next difficulty, and any weak topics detected.
5. Generate a learning path for "SQL" — see the ordered topic list, which
   will reorder around weak topics after more quiz attempts.
6. Check the Progress tab for the dashboard view.

## 6. Known simplifications (worth noting in your report)

- No password-based auth — a learner profile is just a name. Add real auth
  (e.g. OAuth or hashed passwords + JWT) before any real deployment.
- Difficulty adjustment and weak-topic detection use simple fixed
  thresholds rather than a trained model — easy to explain and defend,
  and replaceable with a more sophisticated approach later.
- RAG retrieval is per-user but does not de-duplicate re-uploaded files.
