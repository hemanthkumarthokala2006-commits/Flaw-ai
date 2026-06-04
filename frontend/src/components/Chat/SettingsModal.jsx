import { useState, useContext } from "react";
import { X, Settings } from "lucide-react";
import { PreferencesContext } from "../../context/PreferencesContext";
import "./SettingsModal.css";

export default function SettingsModal({ isOpen, onClose }) {
  const { preferences, updatePreferences } = useContext(PreferencesContext);
  const [localPrefs, setLocalPrefs] = useState(preferences);

  const handleChange = (key, value) => {
    setLocalPrefs({ ...localPrefs, [key]: value });
  };

  const handleSave = () => {
    updatePreferences(localPrefs);
    onClose();
  };

  const handleReset = () => {
    setLocalPrefs(preferences);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h3>Settings</h3>
          <button className="settings-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="settings-body">
          <div className="settings-section">
            <h4>Response Preferences</h4>
            
            <div className="setting-item">
              <label>Response Length</label>
              <select
                value={localPrefs.responseLength}
                onChange={(e) => handleChange("responseLength", e.target.value)}
              >
                <option value="short">Short & Concise</option>
                <option value="medium">Medium</option>
                <option value="long">Detailed</option>
              </select>
            </div>

            <div className="setting-item">
              <label>Tone</label>
              <select
                value={localPrefs.tone}
                onChange={(e) => handleChange("tone", e.target.value)}
              >
                <option value="casual">Casual</option>
                <option value="professional">Professional</option>
                <option value="creative">Creative</option>
                <option value="technical">Technical</option>
              </select>
            </div>
          </div>

          <div className="settings-section">
            <h4>Features</h4>
            
            <div className="setting-checkbox">
              <input
                type="checkbox"
                id="autoSummary"
                checked={localPrefs.autoSummary}
                onChange={(e) => handleChange("autoSummary", e.target.checked)}
              />
              <label htmlFor="autoSummary">Auto-generate chat summaries</label>
            </div>

            <div className="setting-checkbox">
              <input
                type="checkbox"
                id="enableMetrics"
                checked={localPrefs.enableMetrics}
                onChange={(e) => handleChange("enableMetrics", e.target.checked)}
              />
              <label htmlFor="enableMetrics">Show response metrics</label>
            </div>

            <div className="setting-checkbox">
              <input
                type="checkbox"
                id="autoSave"
                checked={localPrefs.autoSave}
                onChange={(e) => handleChange("autoSave", e.target.checked)}
              />
              <label htmlFor="autoSave">Auto-save chats</label>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button className="btn-secondary" onClick={handleReset}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}