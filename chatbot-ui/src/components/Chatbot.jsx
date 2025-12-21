import React, { useState, useRef, useEffect } from "react";

/*
  Chatbot UI for Agentic Loan Processing System

  Responsibilities:
  - Manages chat UI and state
  - Handles session & customer identity
  - Sends messages/files to backend
  - Renders agent replies and documents
*/
const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";



export default function Chatbot() {
  // -------------------- Session & Identity --------------------
  const [sessionId, setSessionId] = useState(() => `sess_${Date.now()}`);
  const [customerId, setCustomerId] = useState("");
  const [pendingCustomerId, setPendingCustomerId] = useState("");

  // -------------------- Chat State --------------------
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // -------------------- File Upload --------------------
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Append a new message to chat
  function pushMessage(author, text, meta = {}) {
    setMessages(prev => [
      ...prev,
      {
        id: `m_${prev.length}_${Date.now()}`,
        author,
        text,
        time: new Date(),
        ...meta
      }
    ]);
  }

  // Initialize conversation once customer ID is set
  useEffect(() => {
    if (!customerId) return;
    setMessages([
      {
        id: "sys_welcome",
        author: "system",
        text: `Welcome! Session started for customer ID: ${customerId}. LoanAgent AI online.`
      }
    ]);
  }, [customerId]);

  // Activate customer session
  function activateCustomer() {
    if (!pendingCustomerId.trim()) return;
    setCustomerId(pendingCustomerId.trim());
    setPendingCustomerId("");
  }

  // -------------------- Message Send Logic --------------------
  async function handleSend(e) {
    e?.preventDefault();
    if (!input.trim() && !file) return;

    if (!customerId) {
      pushMessage("system", "Please enter your Customer ID before starting.");
      return;
    }

    // Show user message instantly
    if (input.trim()) pushMessage("user", input.trim());

    const messageText = input.trim();
    setInput("");

    let fileId = null;

    // Upload file (salary slip) if present
    if (file) {
      try {
        setUploading(true);
        const form = new FormData();
        form.append("file", file);

        // upload
        const res = await fetch(`${API_BASE}/api/upload`, {
          method: "POST",
          body: form
        });


        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();

        fileId = data.fileId;
        pushMessage("user", `📎 Uploaded file: ${data.filename}`);
      } catch (err) {
        pushMessage("system", `File upload failed: ${err.message}`);
      } finally {
        setUploading(false);
        setFile(null);
      }
    }

    // Send chat message to backend
    setIsTyping(true);
    try {
      // chat
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          customerId,
          message: messageText,
          fileId
        })
      });


      if (!res.ok) {
        pushMessage("system", `Server error: ${await res.text()}`);
        return;
      }

      const data = await res.json();

      // Render agent replies sequentially
      if (Array.isArray(data.replies)) {
        for (const r of data.replies) {
          await new Promise(res => setTimeout(res, 350));
          pushMessage(r.role || "bot", r.text, { meta: r.meta || {} });
        }
      }

      // Sanction document link
      if (data.sanctionUrl) {
        pushMessage(
          "system",
          `Sanction letter generated.`,
          { link: data.sanctionUrl }
        );
      }
    } catch (err) {
      pushMessage("system", `Chat error: ${err.message}`);
    } finally {
      setIsTyping(false);
    }
  }

  // Handle file selection
  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  }

  // Quick reply buttons
  function handleQuickReply(text) {
    if (!customerId) {
      pushMessage("system", "Please set Customer ID first.");
      return;
    }
    setInput(text);
    setTimeout(handleSend, 250);
  }

  // -------------------- UI --------------------
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-6">
      <div className="w-full max-w-4xl shadow-2xl rounded-2xl overflow-hidden grid grid-cols-12 bg-white">

        {/* Left Panel — Session & Actions */}
        <div className="col-span-4 border-r p-4 bg-slate-50">
          <div className="font-bold mb-2">LoanAgent AI</div>

          <div className="mb-4">
            <div className="text-xs text-slate-500">Session ID</div>
            <div className="font-mono text-sm bg-slate-100 p-2 rounded">
              {sessionId}
            </div>
            <button
              className="text-xs text-indigo-600 mt-1"
              onClick={() => setSessionId(`sess_${Date.now()}`)}
            >
              Start new session
            </button>
          </div>

          <div className="mb-4">
            <div className="text-xs text-slate-500">Customer ID</div>
            <div className="flex gap-2 mt-1">
              <input
                value={pendingCustomerId}
                onChange={e => setPendingCustomerId(e.target.value)}
                placeholder="CUST001"
                className="flex-1 p-2 border rounded text-sm"
              />
              <button
                onClick={activateCustomer}
                className="px-3 bg-indigo-600 text-white rounded text-sm"
              >
                Set
              </button>
            </div>
            {customerId && (
              <div className="text-xs mt-2">
                Active: <b>{customerId}</b>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <button onClick={() => handleQuickReply("Hi, show me loan offers")} className="btn">
              Start pitch
            </button>
            <button onClick={() => handleQuickReply("I want ₹150000 for 24 months")} className="btn">
              Request loan
            </button>
          </div>
        </div>

        {/* Right Panel — Chat */}
        <div className="col-span-8 flex flex-col">
          <div className="flex-1 overflow-auto p-6 space-y-4">
            {messages.map(msg => <ChatMessage key={msg.id} msg={msg} />)}

            {isTyping && (
              <div className="text-sm text-slate-500">LoanAgent AI is typing...</div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="border-t p-4 flex gap-3">
            <textarea
              rows={2}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type message..."
              className="flex-1 p-2 border rounded"
              disabled={!customerId}
            />

            <div className="flex flex-col gap-2">
              <input type="file" onChange={handleFileChange} disabled={uploading} />
              <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded">
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// -------------------- Message Bubble --------------------
function ChatMessage({ msg }) {
  const isUser = msg.author === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`${isUser ? "bg-indigo-600 text-white" : "bg-slate-100"} p-3 rounded max-w-[70%]`}>
        <div className="text-sm whitespace-pre-wrap">{msg.text}</div>
        {msg.meta?.link && (
          // pdf link
          <a
            href={`${API_BASE}${msg.meta.link}`}
            target="_blank"
            rel="noreferrer"
            className="text-xs underline mt-2 inline-block"
          >
            Open document
          </a>

        )}
        <div className="text-[10px] text-slate-400 mt-1">
          {formatTime(msg.time)}
        </div>
      </div>
    </div>
  );
}

// Format timestamp
function formatTime(t) {
  if (!t) return "";
  return new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
