import { useState, useEffect, useRef } from "react";
import { Send, Mic, Camera, Paperclip, ChevronDown, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { chatAPI } from "../../services/api";
import Sidebar from "../Sidebar/Sidebar";
import VoiceAssistant from "../VoiceAssistant/VoiceAssistant";
import "./Chat.css";

export default function ChatPage() {
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [showVoiceAssistant, setShowVoiceAssistant] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const recorderRef = useRef(null);

  useEffect(() => {
    if (activeChat) loadMessages(activeChat.id);
    else setMessages([]);
  }, [activeChat]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadMessages = async (chatId) => {
    try {
      const data = await chatAPI.getMessages(chatId);
      setMessages(data || []);
    } catch (e) { console.error(e); }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;

    let chat = activeChat;
    if (!chat) {
      try {
        chat = await chatAPI.create("New Chat");
        setActiveChat(chat);
      } catch (e) { console.error(e); return; }
    }

    const userMsg = { id: Date.now(), role: "user", content: input, message_type: "text", created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const aiMsg = await chatAPI.sendMessage(chat.id, input);
      setMessages((prev) => [...prev, aiMsg]);
    } catch (e) {
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: "assistant", content: "Sorry, something went wrong. Please try again.", message_type: "text", created_at: new Date().toISOString() }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const createOrGetChat = async () => {
    if (activeChat) return activeChat;
    const chat = await chatAPI.create("New Chat");
    setActiveChat(chat);
    setMessages([]);
    return chat;
  };

  const uploadMedia = async (chatId, file, type) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("message_type", type);
    formData.append("content", file.name);

    setSending(true);
    try {
      const attachmentMsg = await chatAPI.uploadMedia(chatId, formData);
      setMessages((prev) => [...prev, attachmentMsg]);
    } catch (e) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "assistant",
          content: "Upload failed. Please try again.",
          message_type: "text",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleAttachClick = () => fileInputRef.current?.click();
  const handleCameraClick = () => cameraInputRef.current?.click();

  const handleFileChange = async (event, type) => {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.value = null;

    const chat = await createOrGetChat();
    await uploadMedia(chat.id, file, type);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="app-layout">
      <Sidebar
        activeChat={activeChat?.id}
        onSelectChat={(chat) => setActiveChat(chat)}
        onNewChat={(chat) => { setActiveChat(chat); setMessages([]); }}
      />

      <main className="chat-main">
        {/* Header */}
        <header className="chat-header">
          <div className="chat-header-info">
            <h2>Flaw AI <ChevronDown size={16} style={{ display: 'inline', verticalAlign: 'middle', marginLeft: '4px' }} /></h2>
          </div>
        </header>

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && !activeChat && (
            <div className="chat-welcome fade-in">
              <div className="welcome-logo">
                <svg width="64" height="64" viewBox="0 0 48 48" fill="none">
                  <defs><linearGradient id="wl-grad" x1="0" y1="0" x2="48" y2="48">
                    <stop offset="0%" stopColor="#00d4ff"/><stop offset="100%" stopColor="#7c3aed"/>
                  </linearGradient></defs>
                  <circle cx="24" cy="24" r="22" stroke="url(#wl-grad)" strokeWidth="2" fill="none"/>
                  <path d="M16 18h16M16 24h12M16 30h8" stroke="url(#wl-grad)" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <h1>Ready when you are.</h1>
              <div className="welcome-chips">
                {["Create an image", "Write or edit", "Look something up", "Analyze data"].map((t) => (
                  <button key={t} className="welcome-chip" onClick={() => { setInput(t); inputRef.current?.focus(); }}>
                    <Sparkles size={14} /> {t}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role} fade-in`}>
              <div className="message-avatar">
                {msg.role === "user" ? "U" : (
                  <svg width="18" height="18" viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="22" stroke="#00d4ff" strokeWidth="2.5" fill="none"/>
                    <path d="M16 18h16M16 24h12M16 30h8" stroke="#00d4ff" strokeWidth="2.5" strokeLinecap="round"/>
                  </svg>
                )}
              </div>
              <div className="message-content">
                {msg.message_type === "image" && msg.media_url ? (
                  <img src={msg.media_url} alt={msg.content} className="message-image" />
                ) : msg.message_type === "voice" && msg.media_url ? (
                  <audio controls src={msg.media_url} className="message-audio" />
                ) : msg.message_type === "file" && msg.media_url ? (
                  <a href={msg.media_url} target="_blank" rel="noopener noreferrer" className="message-file-link">
                    {msg.content || "Download file"}
                  </a>
                ) : (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="message assistant fade-in">
              <div className="message-avatar">
                <svg width="18" height="18" viewBox="0 0 48 48" fill="none">
                  <circle cx="24" cy="24" r="22" stroke="#00d4ff" strokeWidth="2.5" fill="none"/>
                  <path d="M16 18h16M16 24h12M16 30h8" stroke="#00d4ff" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
              </div>
              <div className="message-content typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <input ref={fileInputRef} type="file" style={{ display: "none" }} onChange={(e) => handleFileChange(e, "file")} />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={(e) => handleFileChange(e, "image")}
        />

        {/* Input Bar */}
        <div className="chat-input-container">
          <div className="chat-input-bar glass-card">
            <button className="btn-icon" title="Attach file" onClick={handleAttachClick}>
              <Paperclip size={18} />
            </button>
            <button className="btn-icon" title="Camera" onClick={handleCameraClick}>
              <Camera size={18} />
            </button>
            <textarea
              ref={inputRef}
              className="chat-textarea"
              placeholder="Message Flaw AI..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className={`btn-icon`}
              title="AI Voice Assistant"
              onClick={() => setShowVoiceAssistant(true)}
              type="button"
            >
              <Mic size={18} />
            </button>
            <button className="btn-icon send-btn" onClick={handleSend} disabled={!input.trim() || sending} title="Send">
              <Send size={18} />
            </button>
          </div>
          <p className="chat-disclaimer">Flaw AI can make mistakes. Verify important information.</p>
        </div>
      </main>

      {showVoiceAssistant && (
        <VoiceAssistant onClose={() => setShowVoiceAssistant(false)} />
      )}
    </div>
  );
}
