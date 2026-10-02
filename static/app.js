let currentUserId = localStorage.getItem("edugenie_user_id") || null;
let currentQuiz = null;

if (currentUserId) {
  document.getElementById("user-status").textContent = `Logged in as user #${currentUserId}`;
}

function showTab(name) {
  document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
  document.getElementById(`tab-${name}`).style.display = "block";
  event.target.classList.add("active");
  if (name === "path") loadPath();
  if (name === "progress") loadProgress();
}

async function createUser() {
  const name = document.getElementById("user-name").value.trim();
  const level = document.getElementById("user-level").value;
  if (!name) return alert("Enter your name first.");

  const res = await fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, level }),
  });
  const data = await res.json();
  currentUserId = data.id;
  localStorage.setItem("edugenie_user_id", currentUserId);
  document.getElementById("user-status").textContent = `Logged in as ${data.name} (user #${data.id})`;
}

function requireUser() {
  if (!currentUserId) {
    alert("Create a learner profile first (Section 1).");
    return false;
  }
  return true;
}

async function askQuestion() {
  if (!requireUser()) return;
  const topic = document.getElementById("ask-topic").value || "general";
  const question = document.getElementById("ask-question").value.trim();
  const useRag = document.getElementById("use-rag").checked;
  if (!question) return;

  const box = document.getElementById("ask-answer");
  box.textContent = "Thinking...";

  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: Number(currentUserId), question, topic, use_rag: useRag }),
  });
  const data = await res.json();
  let text = data.answer;
  if (data.sources && data.sources.length) {
    text += `\n\nSources: ${data.sources.join(", ")}`;
  }
  box.textContent = text;
}

async function uploadFile() {
  if (!requireUser()) return;
  const fileInput = document.getElementById("upload-file");
  if (!fileInput.files.length) return alert("Choose a file first.");

  const formData = new FormData();
  formData.append("user_id", currentUserId);
  formData.append("file", fileInput.files[0]);

  document.getElementById("upload-status").textContent = "Uploading and indexing...";
  const res = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();
  document.getElementById("upload-status").textContent =
    `Indexed "${data.filename}" into ${data.chunks_indexed} chunks. You can now ask questions with RAG enabled.`;
}

async function generateQuiz() {
  if (!requireUser()) return;
  const topic = document.getElementById("quiz-topic").value.trim();
  const difficulty = document.getElementById("quiz-difficulty").value;
  if (!topic) return alert("Enter a topic.");

  const area = document.getElementById("quiz-area");
  area.innerHTML = "Generating quiz...";

  const res = await fetch("/api/quiz/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: Number(currentUserId), topic, difficulty, num_questions: 5 }),
  });
  const data = await res.json();

  if (!Array.isArray(data.questions)) {
    area.innerHTML = `<p>Could not generate quiz. ${data.questions?.error || ""}</p>`;
    return;
  }

  currentQuiz = { topic, difficulty, questions: data.questions, answers: {} };
  renderQuiz();
}

function renderQuiz() {
  const area = document.getElementById("quiz-area");
  area.innerHTML = "";
  currentQuiz.questions.forEach((q, i) => {
    const div = document.createElement("div");
    div.className = "quiz-question";
    div.innerHTML = `<strong>Q${i + 1}. ${q.question}</strong><br>` +
      q.options.map(opt =>
        `<label><input type="radio" name="q${i}" value="${opt}" onchange="recordAnswer(${i}, '${opt.replace(/'/g, "\\'")}')"> ${opt}</label><br>`
      ).join("");
    area.appendChild(div);
  });
  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Submit Quiz";
  submitBtn.onclick = submitQuiz;
  area.appendChild(submitBtn);
}

function recordAnswer(index, value) {
  currentQuiz.answers[index] = value;
}

async function submitQuiz() {
  let correct = 0;
  currentQuiz.questions.forEach((q, i) => {
    if (currentQuiz.answers[i] === q.correct_answer) correct++;
  });
  const total = currentQuiz.questions.length;

  const res = await fetch("/api/quiz/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: Number(currentUserId),
      topic: currentQuiz.topic,
      difficulty: currentQuiz.difficulty,
      total_questions: total,
      correct_answers: correct,
    }),
  });
  const data = await res.json();

  const area = document.getElementById("quiz-area");
  area.innerHTML = `<p>Score: ${correct}/${total} (${data.score_percent.toFixed(0)}%)</p>
    <p>Next difficulty suggested: <strong>${data.next_difficulty}</strong></p>
    <p>Weak topics identified: ${data.feedback_loop.weak_topics.map(w => w.topic).join(", ") || "none"}</p>`;
}

async function generatePath() {
  if (!requireUser()) return;
  const subject = document.getElementById("path-subject").value.trim();
  if (!subject) return alert("Enter a subject.");

  const res = await fetch("/api/path/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: Number(currentUserId), subject }),
  });
  await res.json();
  loadPath();
}

async function loadPath() {
  if (!currentUserId) return;
  const res = await fetch(`/api/path/${currentUserId}`);
  const items = await res.json();
  const list = document.getElementById("path-list");
  list.innerHTML = "";
  items.forEach(item => {
    const li = document.createElement("li");
    li.className = item.status === "weak" ? "weak" : "ok";
    li.textContent = `${item.order + 1}. ${item.topic} — ${item.status}`;
    list.appendChild(li);
  });
}

async function loadProgress() {
  if (!currentUserId) return;
  const res = await fetch(`/api/progress/${currentUserId}`);
  const data = await res.json();
  const area = document.getElementById("progress-area");

  let html = `<p>Total quiz attempts: ${data.total_attempts}</p>`;
  html += "<h3>By topic</h3><ul>";
  data.topics.forEach(t => {
    html += `<li>${t.topic}: ${t.avg_score}% avg over ${t.attempts} attempt(s)</li>`;
  });
  html += "</ul>";

  html += "<h3>Weak topics</h3>";
  html += data.weak_topics.length
    ? "<ul>" + data.weak_topics.map(w => `<li>${w.topic} (${w.avg_score}%)</li>`).join("") + "</ul>"
    : "<p>None detected yet.</p>";

  area.innerHTML = html;
}
