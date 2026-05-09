import { useState, useEffect } from "react";
import { Plus, MessageSquare, Trash2, LogOut, Settings, Search, Edit } from "lucide-react";
import { chatAPI } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import "./Sidebar.css";

export default function Sidebar({ activeChat, onSelectChat, onNewChat }) {
  const [chats, setChats] = useState([]);
  const { user, logout } = useAuth();

  useEffect(() => { loadChats(); }, []);

  const loadChats = async () => {
    try {
      const data = await chatAPI.list();
      setChats(data || []);
    } catch (e) { console.error("Failed to load chats", e); }
  };

  const handleNewChat = async () => {
    try {
      const chat = await chatAPI.create();
      setChats((prev) => [chat, ...prev]);
      onNewChat(chat);
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await chatAPI.delete(id);
      setChats((prev) => prev.filter((c) => c.id !== id));
      if (activeChat === id) onNewChat(null);
    } catch (e) { console.error(e); }
  };

  return (
    <aside className="sidebar glass-card">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <div className="sidebar-brand">
            <div className="gpt-logo">
              <svg width="20" height="20" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="22" stroke="#ececec" strokeWidth="3" fill="none"/>
                <path d="M16 18h16M16 24h12M16 30h8" stroke="#ececec" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            </div>
            <span>New chat</span>
          </div>
          <Edit size={16} />
        </button>
      </div>
      
      <div className="sidebar-nav">
        <button className="nav-item">
          <Search size={16} /> Search chats
        </button>
        <button className="nav-item">
          <div className="explore-icon"></div> Explore Assistants
        </button>
      </div>

      <div className="sidebar-section">
        <span className="section-title">Recents</span>
      </div>

      <div className="sidebar-chats">
        {chats.length === 0 && (
          <div className="sidebar-empty">
            <p>No conversations yet</p>
          </div>
        )}
        {chats.map((chat) => (
          <div key={chat.id}
            className={`sidebar-chat-item ${activeChat === chat.id ? "active" : ""}`}
            onClick={() => onSelectChat(chat)}
          >
            <span className="chat-title">{chat.title}</span>
            <button className="chat-delete" onClick={(e) => handleDelete(e, chat.id)} title="Delete">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {user?.username?.charAt(0).toUpperCase() || "U"}
          </div>
          <span className="sidebar-username">{user?.username || "User"}</span>
        </div>
        <button className="btn-icon" onClick={logout} title="Logout">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
