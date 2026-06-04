import { useState } from "react";
import { AlertCircle, X } from "lucide-react";
import "./ErrorBoundary.css";

export default function ErrorBoundary({ error, onDismiss }) {
  if (!error) return null;

  const errorMessages = {
    network: "Connection failed. Please check your internet connection.",
    auth: "Authentication failed. Please log in again.",
    timeout: "Request timed out. Please try again.",
    server: "Server error. Please try again later.",
    unknown: "An unexpected error occurred. Please try again.",
  };

  const getErrorType = (err) => {
    const message = err?.message || "";
    if (message.includes("401")) return "auth";
    if (message.includes("timeout")) return "timeout";
    if (message.includes("Network")) return "network";
    if (message.includes("500")) return "server";
    return "unknown";
  };

  const errorType = getErrorType(error);
  const errorMessage = errorMessages[errorType];

  return (
    <div className="error-boundary">
      <div className="error-content">
        <AlertCircle size={20} className="error-icon" />
        <div className="error-message">
          <p className="error-title">Oops! Something went wrong</p>
          <p className="error-description">{errorMessage}</p>
        </div>
        <button className="error-dismiss" onClick={onDismiss}>
          <X size={16} />
        </button>
      </div>
    </div>
  );
}