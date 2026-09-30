const form = document.getElementById("message-form");
const contentInput = document.getElementById("content");
const imageInput = document.getElementById("image");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");
const listEl = document.getElementById("message-list");
const feedStatus = document.getElementById("feed-status");

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function setError(message) {
  if (!message) {
    formError.hidden = true;
    formError.textContent = "";
    return;
  }
  formError.hidden = false;
  formError.textContent = message;
}

function renderMessages(messages) {
  listEl.innerHTML = "";

  if (!messages.length) {
    feedStatus.textContent = "還沒有留言";
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "成為第一個留言的人吧。";
    listEl.appendChild(empty);
    return;
  }

  feedStatus.textContent = `共 ${messages.length} 則`;
  for (const message of messages) {
    const item = document.createElement("li");
    item.className = "message-card";

    const img = document.createElement("img");
    img.src = message.image_url;
    img.alt = "留言圖片";
    img.loading = "lazy";

    const body = document.createElement("div");
    body.className = "message-body";

    const text = document.createElement("p");
    text.textContent = message.content;

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = formatTime(message.created_at);

    body.append(text, meta);
    item.append(img, body);
    listEl.appendChild(item);
  }
}

async function loadMessages() {
  feedStatus.textContent = "載入中…";
  const response = await fetch("/api/messages");
  if (!response.ok) {
    throw new Error("無法載入留言列表");
  }
  const messages = await response.json();
  renderMessages(messages);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");

  const content = contentInput.value.trim();
  const image = imageInput.files?.[0];
  if (!content) {
    setError("請填寫留言內容");
    return;
  }
  if (!image) {
    setError("請選擇一張圖片");
    return;
  }

  const body = new FormData();
  body.append("content", content);
  body.append("image", image);

  submitBtn.disabled = true;
  submitBtn.textContent = "送出中…";

  try {
    const response = await fetch("/api/messages", {
      method: "POST",
      body,
    });
    if (!response.ok) {
      let detail = "送出失敗";
      try {
        const payload = await response.json();
        if (typeof payload.detail === "string") detail = payload.detail;
      } catch (_) {
        // ignore JSON parse errors
      }
      throw new Error(detail);
    }

    form.reset();
    await loadMessages();
  } catch (error) {
    setError(error.message || "送出失敗");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "送出留言";
  }
});

loadMessages().catch((error) => {
  feedStatus.textContent = "載入失敗";
  setError(error.message || "無法載入留言列表");
});
