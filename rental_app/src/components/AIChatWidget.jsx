import { useEffect, useRef, useState } from "react";
import { sendAIChatMessage } from "../api/aiChatApi";
import { getRecommendedGuidesByIntent } from "../utils/guideUtils";
import "./AIChatWidget.css";

const WELCOME_MESSAGE =
  "Hi, I'm your RentalAI assistant. I can help you compare properties, understand rental risks, check contracts, and answer housing questions.";

const FALLBACK_ERROR_MESSAGE =
  "Sorry, I couldn't connect to RentalAI right now. Please try again later.";

function nextMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

const INTENT_LABELS = {
  property_search: "Property search",
  contract_help: "Contract help",
  area_info: "Area info",
  dispute_help: "Dispute help",
  landlord_help: "Landlord help",
  general: "General",
};

function formatIntentLabel(intent) {
  if (!intent) return "";
  return INTENT_LABELS[intent] || intent.replace(/_/g, " ");
}

function normalizeActions(actions) {
  if (!Array.isArray(actions)) return undefined;
  const items = actions
    .filter((item) => typeof item === "string" && item.trim())
    .map((item) => item.trim());
  return items.length > 0 ? items : undefined;
}

function buildAssistantMessage(data) {
  const intent = data.intent || undefined;
  const recommendedGuides = getRecommendedGuidesByIntent(data.intent);
  return {
    id: nextMessageId(),
    role: "assistant",
    content: data.answer || FALLBACK_ERROR_MESSAGE,
    intent,
    suggested_next_actions: normalizeActions(data.suggested_next_actions),
    recommended_guides:
      recommendedGuides.length > 0 ? recommendedGuides : undefined,
    isError: false,
  };
}

function buildErrorAssistantMessage() {
  return {
    id: nextMessageId(),
    role: "assistant",
    content: FALLBACK_ERROR_MESSAGE,
    intent: undefined,
    suggested_next_actions: undefined,
    recommended_guides: undefined,
    isError: true,
  };
}

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(() => [
    {
      id: nextMessageId(),
      role: "assistant",
      content: WELCOME_MESSAGE,
      intent: undefined,
      suggested_next_actions: undefined,
      recommended_guides: undefined,
      isError: false,
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const listRef = useRef(null);
  const requestIdRef = useRef(0);

  function cancelPendingRequest() {
    requestIdRef.current += 1;
    setIsLoading(false);
  }

  useEffect(() => {
    if (!isOpen || !listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isOpen, isLoading]);

  async function handleSendMessage(customMessage) {
    const text = (typeof customMessage === "string" ? customMessage : inputValue).trim();
    if (!text || isLoading) return;

    if (typeof customMessage !== "string") {
      setInputValue("");
    }

    setMessages((prev) => [
      ...prev,
      { id: nextMessageId(), role: "user", content: text },
    ]);
    setIsLoading(true);

    const requestId = ++requestIdRef.current;

    try {
      const data = await sendAIChatMessage(text);
      if (requestId !== requestIdRef.current) return;

      setMessages((prev) => [...prev, buildAssistantMessage(data)]);
    } catch {
      if (requestId !== requestIdRef.current) return;
      setMessages((prev) => [...prev, buildErrorAssistantMessage()]);
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }

  function sendFromInput() {
    handleSendMessage();
  }

  function handleKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    sendFromInput();
  }

  function handleActionClick(actionText) {
    handleSendMessage(actionText);
  }

  function handleGuideCardClick(guide) {
    const first = guide?.starter_questions?.[0];
    if (typeof first === "string" && first.trim()) {
      handleSendMessage(first.trim());
    }
  }

  const latestAssistantMessageId = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && !m.isError)?.id;

  return (
    <div className="ai-chat-widget">
      {isOpen ? (
        <div
          id="ai-chat-widget-panel"
          className="ai-chat-widget__panel ai-chat-widget__panel--open"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ai-chat-widget-title"
          aria-busy={isLoading}
        >
          <header className="ai-chat-widget__header">
            <div className="ai-chat-widget__header-text">
              <h2 id="ai-chat-widget-title" className="ai-chat-widget__title">
                RentalAI Assistant
              </h2>
              <p className="ai-chat-widget__subtitle">UK rental guidance</p>
            </div>
            <button
              type="button"
              className="ai-chat-widget__close"
              onClick={() => {
                cancelPendingRequest();
                setIsOpen(false);
              }}
              aria-label="Close chat"
            >
              <span aria-hidden>×</span>
            </button>
          </header>
          <div
            ref={listRef}
            className="ai-chat-widget__messages"
            role="log"
            aria-live="polite"
            aria-relevant="additions"
          >
            {messages.map((m) =>
              m.role === "user" ? (
                <div
                  key={m.id}
                  className="ai-chat-widget__row ai-chat-widget__row--user"
                >
                  <div className="ai-chat-widget__bubble ai-chat-widget__bubble--user">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div
                  key={m.id}
                  className="ai-chat-widget__row ai-chat-widget__row--assistant"
                >
                  <div className="ai-chat-widget__assistant-block">
                    {m.intent && !m.isError ? (
                      <span className="ai-chat-widget__intent" title={m.intent}>
                        {formatIntentLabel(m.intent)}
                      </span>
                    ) : null}
                    <div
                      className={
                        m.isError
                          ? "ai-chat-widget__bubble ai-chat-widget__bubble--assistant ai-chat-widget__bubble--error"
                          : "ai-chat-widget__bubble ai-chat-widget__bubble--assistant"
                      }
                    >
                      {m.content}
                    </div>
                    {m.recommended_guides?.length > 0 &&
                    m.id === latestAssistantMessageId &&
                    !isLoading ? (
                      <div
                        className="ai-chat-widget__guides"
                        role="group"
                        aria-label="Recommended guides"
                      >
                        {m.recommended_guides.map((guide) => (
                          <button
                            key={guide.id}
                            type="button"
                            className="ai-chat-widget__guide-card"
                            onClick={() => handleGuideCardClick(guide)}
                            disabled={isLoading}
                          >
                            <span className="ai-chat-widget__guide-card-category">
                              {guide.category}
                            </span>
                            <span className="ai-chat-widget__guide-card-title">
                              {guide.title}
                            </span>
                            <span className="ai-chat-widget__guide-card-desc">
                              {guide.description}
                            </span>
                            {(guide.starter_questions ?? [])
                              .slice(0, 2)
                              .map((q, hi) => (
                                <span
                                  key={`${guide.id}-hint-${hi}`}
                                  className="ai-chat-widget__guide-card-hint"
                                >
                                  {q}
                                </span>
                              ))}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {m.suggested_next_actions?.length > 0 &&
                    m.id === latestAssistantMessageId &&
                    !isLoading ? (
                      <div
                        className="ai-chat-widget__actions"
                        role="group"
                        aria-label="Suggested next actions"
                      >
                        {m.suggested_next_actions.map((label) => (
                          <button
                            key={`${m.id}-${label}`}
                            type="button"
                            className="ai-chat-widget__action"
                            onClick={() => handleActionClick(label)}
                            disabled={isLoading}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            )}
            {isLoading ? (
              <div
                className="ai-chat-widget__row ai-chat-widget__row--assistant"
                aria-live="polite"
                aria-label="Assistant is thinking"
              >
                <div className="ai-chat-widget__typing">
                  <span className="ai-chat-widget__typing-dots" aria-hidden>
                    <span className="ai-chat-widget__typing-dot" />
                    <span className="ai-chat-widget__typing-dot" />
                    <span className="ai-chat-widget__typing-dot" />
                  </span>
                  <span className="ai-chat-widget__typing-label">Thinking</span>
                </div>
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
              placeholder="Ask about rent, contracts, or listings…"
              aria-label="Message"
              disabled={isLoading}
            />
            <button
              type="button"
              className="ai-chat-widget__send"
              onClick={sendFromInput}
              disabled={!inputValue.trim() || isLoading}
            >
              {isLoading ? (
                <span className="ai-chat-widget__send-label">Thinking…</span>
              ) : (
                <span className="ai-chat-widget__send-label">Send</span>
              )}
            </button>
          </footer>
        </div>
      ) : null}

      <button
        type="button"
        className={`ai-chat-widget__fab${isOpen ? " ai-chat-widget__fab--open" : ""}`}
        onClick={() => {
          if (isOpen) {
            cancelPendingRequest();
            setIsOpen(false);
          } else {
            setIsOpen(true);
          }
        }}
        aria-expanded={isOpen}
        aria-controls={isOpen ? "ai-chat-widget-panel" : undefined}
        title={isOpen ? "Close assistant" : "Ask RentalAI"}
      >
        {isOpen ? (
          <span className="ai-chat-widget__fab-icon" aria-hidden>
            ×
          </span>
        ) : (
          <>
            <span className="ai-chat-widget__fab-label ai-chat-widget__fab-label--short">
              AI
            </span>
            <span className="ai-chat-widget__fab-label ai-chat-widget__fab-label--long">
              Ask RentalAI
            </span>
          </>
        )}
      </button>
    </div>
  );
}
