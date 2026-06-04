import { createContext, useState, useEffect } from "react";

export const PreferencesContext = createContext();

export function PreferencesProvider({ children }) {
  const [preferences, setPreferences] = useState({
    theme: "dark",
    responseLength: "medium", // short, medium, long
    tone: "professional", // casual, professional, creative, technical
    autoSummary: true,
    enableMetrics: true,
    autoSave: true,
  });

  // Load preferences from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("flaw_preferences");
    if (saved) {
      try {
        setPreferences(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load preferences", e);
      }
    }
  }, []);

  // Save preferences to localStorage
  const updatePreferences = (newPrefs) => {
    const updated = { ...preferences, ...newPrefs };
    setPreferences(updated);
    localStorage.setItem("flaw_preferences", JSON.stringify(updated));
  };

  return (
    <PreferencesContext.Provider value={{ preferences, updatePreferences }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const context = React.useContext(PreferencesContext);
  if (!context) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return context;
}