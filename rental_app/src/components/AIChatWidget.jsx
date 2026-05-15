import { useEffect, useRef, useState } from "react";
import "./AIChatWidget.css";

const WELCOME_MESSAGE =
  "Hi, I'm your RentalAI assistant. I can help you compare properties, understand rental risks, check contracts, and answer housing questions.";

const REPLY_PROPERTY =
  "I can help you compare this property by rent, area, commute, bills, and risk score. The full analysis engine will be connected soon.";

const REPLY_CONTRACT =
  "I can help you review rental contracts, identify risky clauses, and explain deposit-related issues. The contract engine will be connected soon.";

const REPLY_DEFAULT =
  "I understand your question. Soon I'll connect this chat to RentalAI's full analysis modules.";

const PROPERTY_KEYWORDS_EN = ["rent", "property", "house", "flat"];
const PROPERTY_KEYWORDS_ZH = ["房子", "租房"];
const CONTRACT_KEYWORDS_EN = ["contract", "tenancy", "deposit"];
const CONTRACT_KEYWORDS_ZH = ["合同", "押金"];

const REPLY_DELAY_MS = 800;

function nextMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function pickAssistantReply(userText) {
  const lower = userText.toLowerCase();
  const matchesContract =
    CONTRACT_KEYWORDS_EN.some((w) => lower.includes(w)) ||
    CONTRACT_KEYWORDS_ZH.some((w) => userText.includes(w));
  const matchesProperty =
    PROPERTY_KEYWORDS_EN.some((w) => lower.includes(w)) ||
    PROPERTY_KEYWORDS_ZH.some((w) => userText.includes(w));

  if (matchesContract) return REPLY_CONTRACT;
  if (matchesProperty) return REPLY_PROPERTY;
  return REPLY_DEFAULT;
}

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(() => [
    { id: nextMessageId(), role: "assistant", text: WELCOME_MESSAGE },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const listRef = useRef(null);
  const replyTimerRef = useRef(null);
  const replyGenerationRef = useRef(0);

  function cancelPendingReply() {
    if (replyTimerRef.current != null) {
      clearTimeout(replyTimerRef.current);
      replyTimerRef.current = null;
    }
    replyGenerationRef.current += 1;
    setIsLoading(false);
  }

  useEffect(() => {
    return () => {
      if (replyTimerRef.current != null) {
        clearTimeout(replyTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isOpen || !listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isOpen, isLoading]);

  function send() {
    const text = inputValue.trim();
    if (!text || isLoading) return;

    setInputValue("");
    setMessages((prev) => [...prev, { id: nextMessageId(), role: "user", text }]);
    setIsLoading(true);

    if (replyTimerRef.current != null) {
      clearTimeout(replyTimerRef.current);
    }
    replyGenerationRef.current += 1;
    const generation = replyGenerationRef.current;
    replyTimerRef.current = setTimeout(() => {
      replyTimerRef.current = null;
      if (generation !== replyGenerationRef.current) return;
      const reply = pickAssistantReply(text);
      setMessages((prev) => [
        ...prev,
        { id: nextMessageId(), role: "assistant", text: reply },
      ]);
      setIsLoading(false);
    }, REPLY_DELAY_MS);
  }

  function handleKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    send();
  }

  return (
    <div className="ai-chat-widget">
      {isOpen ? (
        <div
          id="ai-chat-widget-panel"
          className="ai-chat-widget__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ai-chat-widget-title"
          aria-busy={isLoading}
        >
          <header className="ai-chat-widget__header">
            <h2 id="ai-chat-widget-title" className="ai-chat-widget__title">
              RentalAI Assistant
            </h2>
            <button
              type="button"
              className="ai-chat-widget__close"
              onClick={() => {
                cancelPendingReply();
                setIsOpen(false);
              }}
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
            {messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "ai-chat-widget__bubble ai-chat-widget__bubble--user"
                    : "ai-chat-widget__bubble ai-chat-widget__bubble--assistant"
                }
              >
                {m.text}
              </div>
            ))}
            {isLoading ? (
              <div
                className="ai-chat-widget__typing"
                aria-live="polite"
                aria-label="Assistant is thinking"
              >
                <span className="ai-chat-widget__typing-dot" aria-hidden />
                <span className="ai-chat-widget__typing-dot" aria-hidden />
                <span className="ai-chat-widget__typing-dot" aria-hidden />
              </div>
            ) : null}
          </div>
          <footer className="ai-chat-widget__footer">
            <textarea
              className="ai-chat-widget__input"
              rows={1}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message…"
              aria-label="Message"
              disabled={isLoading}
            />
            <button
              type="button"
              className="ai-chat-widget__send"
              onClick={send}
              disabled={!inputValue.trim() || isLoading}
            >
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </footer>
        </div>
      ) : null}

      <button
        type="button"
        className="ai-chat-widget__fab"
        onClick={() => {
          if (isOpen) {
            cancelPendingReply();
            setIsOpen(false);
          } else {
            setIsOpen(true);
          }
        }}
        aria-expanded={isOpen}
        aria-controls={isOpen ? "ai-chat-widget-panel" : undefined}
        title={isOpen ? "Close assistant" : "Open RentalAI Assistant"}
      >
        {isOpen ? "×" : "✦"}
      </button>
    </div>
  );
}
