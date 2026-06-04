import { useState, useEffect, useRef } from "react";
import { Send, Mic, Camera, Paperclip, ChevronDown, Sparkles, X, Copy, Check, Monitor, Globe, Video, Zap, Terminal, Edit, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import Mermaid from "./Mermaid";
import { chatAPI, systemAPI } from "../../services/api";
import Sidebar from "../Sidebar/Sidebar";
import VoiceAssistant from "../VoiceAssistant/VoiceAssistant";
import "./Chat.css";

export default function ChatPage() {
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showVoiceAssistant, setShowVoiceAssistant] = useState(false);
  const [pendingFile, setPendingFile] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [editingMessage, setEditingMessage] = useState(null);
  const [editInput, setEditInput] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (activeChat) {
      loadMessages(activeChat.id);
      setHasMore(false);
    } else {
      setMessages([]);
    }
  }, [activeChat]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadMessages = async (chatId, append = false) => {
    try {
      const limit = 50;
      const offset = append ? messages.length : 0;
      const data = await chatAPI.getMessages(chatId, limit, offset);
      if (append) {
        setMessages(prev => [...data, ...prev]);
      } else {
        setMessages(data || []);
      }
      setHasMore(data.length === limit);
    } catch (e) { console.error(e); }
  };

  const loadMoreMessages = async () => {
    if (!activeChat || loadingMore) return;
    setLoadingMore(true);
    await loadMessages(activeChat.id, true);
    setLoadingMore(false);
  };

  const startEditing = (message) => {
    if (message.role !== "user") return;
    setEditingMessage(message.id);
    setEditInput(message.content);
  };

  const cancelEditing = () => {
    setEditingMessage(null);
    setEditInput("");
  };

  const saveEdit = async () => {
    if (!editingMessage || !editInput.trim()) return;
    try {
      await chatAPI.editMessage(activeChat.id, editingMessage, editInput);
      setMessages(prev => prev.map(m => m.id === editingMessage ? { ...m, content: editInput, edited_at: new Date().toISOString() } : m));
      cancelEditing();
    } catch (e) {
      console.error(e);
    }
  };

  const handleExport = async (format = "json") => {
    if (!activeChat) return;
    try {
      const data = await chatAPI.exportConversation(activeChat.id, format);
      if (format === "markdown") {
        const blob = new Blob([data.content], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${activeChat.title}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSend = async (forcedInput = null, forcedMediaUrl = null) => {
    const currentInput = forcedInput !== null ? forcedInput : input;
    const currentMediaUrl = forcedMediaUrl !== null ? forcedMediaUrl : null;
    
    if ((!currentInput.trim() && !pendingFile && !currentMediaUrl) || sending) return;
    
    let chat = activeChat;
    if (!chat) {
      chat = await chatAPI.create("New Chat");
      setActiveChat(chat);
    }

    // Intercept slash commands
    const trimmedInput = currentInput.trim();
    if (trimmedInput.startsWith("/") && !forcedMediaUrl) {
      const spaceIndex = trimmedInput.indexOf(" ");
      const command = spaceIndex !== -1 ? trimmedInput.substring(1, spaceIndex).toLowerCase() : trimmedInput.substring(1).toLowerCase();
      const query = spaceIndex !== -1 ? trimmedInput.substring(spaceIndex + 1).trim() : "";
      
      if (command === "search" && query) {
        setInput("");
        const userMsg = { id: Date.now(), role: "user", content: `/search ${query}` };
        setMessages(prev => [...prev, userMsg]);
        
        const assistantMsg = { id: Date.now() + 1, role: "assistant", content: `Searching the web for "${query}"...` };
        setMessages(prev => [...prev, assistantMsg]);
        
        window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
        return;
      }
      
      if (command === "play" && query) {
        setInput("");
        const userMsg = { id: Date.now(), role: "user", content: `/play ${query}` };
        setMessages(prev => [...prev, userMsg]);
        
        const assistantMsgId = Date.now() + 1;
        setMessages(prev => [...prev, { id: assistantMsgId, role: "assistant", content: `Playing "${query}" on YouTube...` }]);
        
        try {
          await systemAPI.playMedia(query);
        } catch (e) {
          window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`, '_blank');
        }
        return;
      }
      
      if (command === "open" && query) {
        setInput("");
        const userMsg = { id: Date.now(), role: "user", content: `/open ${query}` };
        setMessages(prev => [...prev, userMsg]);
        
        const assistantMsgId = Date.now() + 1;
        setMessages(prev => [...prev, { id: assistantMsgId, role: "assistant", content: `Opening ${query}...` }]);
        
        try {
          await systemAPI.openApp(query);
        } catch (e) {
          window.open(`https://www.${query.replace(/\s+/g, '')}.com`, '_blank');
        }
        return;
      }
    }

    let mediaUrl = currentMediaUrl;
    if (pendingFile) {
      const formData = new FormData();
      formData.append("file", pendingFile.file);
      formData.append("message_type", pendingFile.type);
      try {
        const res = await chatAPI.uploadMedia(chat.id, formData);
        mediaUrl = res.media_url;
        setMessages(prev => [...prev, res]);
      } catch (e) { console.error(e); }
      setPendingFile(null);
    }

    if (currentInput.trim() || mediaUrl) {
      const isImage = !!mediaUrl && !currentInput.trim();
      const userMsg = { 
        id: Date.now(), 
        role: "user", 
        content: currentInput || "File uploaded", 
        message_type: isImage ? "image" : "text",
        media_url: mediaUrl 
      };
      setMessages(prev => [...prev, userMsg]);
      
      const assistantMsgId = Date.now() + 1;
      setMessages(prev => [...prev, { id: assistantMsgId, role: "assistant", content: "" }]);
      
      if (forcedInput === null) {
        setInput("");
      }
      setSending(true);

      try {
        let fullResponse = "";
        await chatAPI.streamMessage(
          chat.id, 
          currentInput || "Analyze this image", 
          isImage ? "image" : "text", 
          mediaUrl, 
          (chunk) => {
            fullResponse += chunk;
            setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: fullResponse } : m));
          }
        );
      } catch (e) {
        console.error(e);
      } finally {
        setSending(false);
      }
    }
  };

  const handleScreenshot = async () => {
    setSending(true);
    try {
      const res = await systemAPI.takeScreenshot();
      if (res.media_url) {
        await handleSend("Analyze this screenshot", res.media_url);
      }
    } catch (e) { 
      console.error(e); 
      const errorMsg = { id: Date.now(), role: "assistant", content: "Failed to take screenshot." };
      setMessages(prev => [...prev, errorMsg]);
    } finally { 
      setSending(false); 
    }
  };

  return (
    <div className="app-layout">
      <Sidebar 
        activeChat={activeChat?.id} 
        onSelectChat={setActiveChat} 
        onNewChat={(chat) => { setActiveChat(chat); setMessages([]); }} 
      />
      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-header-info">
            <h2>Flaw AI <span className="pro-badge">PRO</span></h2>
          </div>
          <div className="chat-header-actions">
            {activeChat && (
              <button className="btn-icon" onClick={() => handleExport("json")} title="Export JSON">
                <Download size={16} />
              </button>
            )}
            <div className="system-status">
              <span className="status-dot"></span> System Online
            </div>
          </div>
        </header>

        <div className="chat-messages">
          {hasMore && (
            <button className="load-more-btn" onClick={loadMoreMessages} disabled={loadingMore}>
              {loadingMore ? "Loading..." : "Load More Messages"}
            </button>
          )}
          {messages.length === 0 && (
            <div className="chat-welcome fade-in">
              <h1>How can I help you, Hemanth?</h1>
              <div className="welcome-chips">
                {["Search the web", "Summarize screen", "Code helper"].map(t => (
                  <button key={t} className="welcome-chip" onClick={() => setInput(t)}>{t}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role} fade-in`}>
              {editingMessage === msg.id ? (
                <div className="message-edit">
                  <textarea
                    value={editInput}
                    onChange={(e) => setEditInput(e.target.value)}
                    rows={3}
                    autoFocus
                  />
                  <div className="edit-actions">
                    <button onClick={cancelEditing}>Cancel</button>
                    <button onClick={saveEdit}>Save</button>
                  </div>
                </div>
              ) : (
                <>
                  <div className={`message-content ${sending && messages.length > 0 && msg.id === messages[messages.length-1].id ? "streaming-cursor" : ""}`}>
                    {msg.message_type === "image" ? <img src={msg.media_url} className="message-image" alt="upload" /> : <ReactMarkdown>{msg.content}</ReactMarkdown>}
                  </div>
                  {msg.role === "user" && (
                    <button className="edit-btn" onClick={() => startEditing(msg)} title="Edit">
                      <Edit size={14} />
                    </button>
                  )}
                  {msg.edited_at && <span className="edited-label">(edited)</span>}
                </>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <div className="quick-actions-bar">
            <button onClick={handleScreenshot}><Monitor size={14} /> Screen</button>
            <button onClick={() => setInput("/search ")}><Globe size={14} /> Search</button>
            <button onClick={() => setInput("/play ")}><Video size={14} /> Video</button>
            <button onClick={() => setInput("/open ")}><Zap size={14} /> App</button>
          </div>
          
          {pendingFile && (
            <div className="pending-file-preview">
              <span>{pendingFile.file.name}</span>
              <button onClick={() => setPendingFile(null)}><X size={14} /></button>
            </div>
          )}

          <div className="chat-input-bar glass-card">
            <button className="btn-icon" onClick={() => fileInputRef.current.click()}><Paperclip size={18} /></button>
            <textarea
              ref={inputRef}
              className="chat-textarea"
              placeholder="Ask Flaw AI anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
              rows={1}
            />
            <button className="btn-icon" onClick={() => setShowVoiceAssistant(true)}><Mic size={18} /></button>
            <button className="btn-icon send-btn" onClick={handleSend} disabled={sending}><Send size={18} /></button>
          </div>
          <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={(e) => setPendingFile({ file: e.target.files[0], type: 'image' })} />
        </div>
      </main>

      {showVoiceAssistant && (
        <VoiceAssistant 
          onClose={() => setShowVoiceAssistant(false)} 
          chatId={activeChat?.id}
          onNewMessage={(msg) => setMessages(prev => [...prev, msg])}
        />
      )}
    </div>
  );
}
