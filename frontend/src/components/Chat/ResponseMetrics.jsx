import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Clock, Zap } from "lucide-react";
import "./ResponseMetrics.css";

export default function ResponseMetrics({ message, isStreaming }) {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    if (!isStreaming && message.role === "assistant") {
      // Calculate basic metrics
      const charCount = message.content.length;
      const wordCount = message.content.split(/\s+/).length;
      const estimatedTokens = Math.ceil(charCount / 4); // Rough estimate

      setMetrics({
        words: wordCount,
        tokens: estimatedTokens,
        status: "success",
      });
    }
  }, [isStreaming, message]);

  if (!metrics || message.role !== "assistant") return null;

  return (
    <div className="response-metrics">
      <div className="metric">
        <Zap size={12} /> {metrics.tokens} tokens
      </div>
      <div className="metric">
        <CheckCircle size={12} /> {metrics.words} words
      </div>
    </div>
  );
}