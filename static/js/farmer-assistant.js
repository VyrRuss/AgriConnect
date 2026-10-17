document.addEventListener("DOMContentLoaded", () => {
  const widget = document.getElementById("farmerAssistant");
  const form = document.getElementById("assistantForm");
  const messages = document.getElementById("assistantMessages");
  const question = document.getElementById("assistantQuestion");
  if (!widget || !form || !messages || !question) return;

  const history = [];
  const copy = {
    en: { you: "You", assistant: "Farmer Assist", thinking: "Thinking…", error: "The assistant could not answer. Please try again.", connection: "Could not reach the assistant. Check your connection and try again.", empty: "Please enter a question." },
    hi: { you: "आप", assistant: "किसान सहायक", thinking: "सोच रहा है…", error: "सहायक जवाब नहीं दे पाया। कृपया फिर से प्रयास करें।", connection: "सहायक से संपर्क नहीं हो पाया। अपना कनेक्शन जाँचकर फिर से प्रयास करें।", empty: "कृपया अपना सवाल लिखें।" },
    kn: { you: "ನೀವು", assistant: "ರೈತ ಸಹಾಯಕ", thinking: "ಯೋಚಿಸುತ್ತಿದೆ…", error: "ಸಹಾಯಕ ಉತ್ತರಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.", connection: "ಸಹಾಯಕವನ್ನು ಸಂಪರ್ಕಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.", empty: "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ನಮೂದಿಸಿ." }
  };
  const activeLanguage = () => {
    const language = document.documentElement.lang;
    return copy[language] ? language : "en";
  };
  const text = (language, key) => copy[language][key];

  const addMessage = (role, content, language = activeLanguage()) => {
    const article = document.createElement("article");
    article.className = `assistant-message ${role === "model" ? "assistant-message-bot" : "assistant-message-user"}`;
    const label = document.createElement("strong");
    label.textContent = role === "model" ? text(language, "assistant") : text(language, "you");
    const paragraph = document.createElement("p");
    paragraph.textContent = content;
    article.append(label, paragraph);
    messages.append(article);
    messages.scrollTop = messages.scrollHeight;
    return article;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = question.value.trim();
    const language = activeLanguage();
    if (!message) {
      question.setCustomValidity(text(language, "empty"));
      question.reportValidity();
      return;
    }
    question.setCustomValidity("");
    addMessage("user", message, language);
    question.value = "";
    question.disabled = true;
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    const pending = addMessage("model", text(language, "thinking"), language);

    try {
      const response = await fetch(widget.dataset.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("meta[name='csrf-token']").content
        },
        body: JSON.stringify({ message, language, history: history.slice(-8) })
      });
      const payload = await response.json();
      pending.remove();
      if (!response.ok) {
        addMessage("model", payload.error || text(language, "error"), language);
        return;
      }
      addMessage("model", payload.answer, language);
      history.push({ role: "user", text: message }, { role: "model", text: payload.answer });
      if (history.length > 8) history.splice(0, history.length - 8);
    } catch (_error) {
      pending.remove();
      addMessage("model", text(language, "connection"), language);
    } finally {
      question.disabled = false;
      button.disabled = false;
      question.focus();
    }
  });
});
