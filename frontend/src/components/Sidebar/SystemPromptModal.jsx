import { useState } from "react";
import { X } from "lucide-react";
import "./SystemPromptModal.css";

export default function SystemPromptModal({ isOpen, onClose, onSave }) {
  const [prompt, setPrompt] = useState("");

  const handleSave = () => {
    onSave(prompt);
    setPrompt("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Custom System Prompt</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <textarea
            placeholder="Enter a custom system prompt for this conversation (optional)..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={6}
          />
          <p className="modal-help">
            This will override the default AI behavior for this chat. Leave empty to use default.
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave}>Create Chat</button>
        </div>
      </div>
    </div>
  );
}