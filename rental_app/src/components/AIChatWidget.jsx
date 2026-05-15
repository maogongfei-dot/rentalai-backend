import { useEffect, useRef, useState } from "react";
import "./AIChatWidget.css";

const WELCOME_MESSAGE =
  "Hi, I'm your RentalAI assistant. I can help you compare properties, understand rental risks, check contracts, and answer housing questions.";

const PLACEHOLDER_REPLY =
  "Thanks, I've received your question. The AI response engine will be connected in the next step.";

export default function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState(() => [
    { role: "assistant", text: WELCOME_MESSAGE },
  ]);
  const [input, setInput] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    if (!open || !listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, open]);

  function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: PLACEHOLDER_REPLY },
    ]);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  return (
    <div className="ai-chat-widget">
      {open ? (
        <div
          id="ai-chat-widget-panel"
          className="ai-chat-widget__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ai-chat-widget-title"
        >
          <header className="ai-chat-widget__header">
            <h2 id="ai-chat-widget-title" className="ai-chat-widget__title">
              RentalAI Assistant
            </h2>
            <button
              type="button"
              className="ai-chat-widget__close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </header>
          <div
            ref={listRef}
            className="ai-chat-widget__messages"
            role="log"
            aria-live="polite"
            aria-relevant="additions"
          >
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ai-chat-widget__bubble ai-chat-widget__bubble--user"
                    : "ai-chat-widget__bubble ai-chat-widget__bubble--assistant"
                }
              >
                {m.text}
              </div>
            ))}
          </div>
          <footer className="ai-chat-widget__footer">
            <textarea
              className="ai-chat-widget__input"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message…"
              aria-label="Message"
            />
            <button
              type="button"
              className="ai-chat-widget__send"
              onClick={send}
              disabled={!input.trim()}
            >
              Send
            </button>
          </footer>
        </div>
      ) : null}

      <button
        type="button"
        className="ai-chat-widget__fab"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={open ? "ai-chat-widget-panel" : undefined}
        title={open ? "Close assistant" : "Open RentalAI Assistant"}
      >
        {open ? "×" : "✦"}
      </button>
    </div>
  );
}
