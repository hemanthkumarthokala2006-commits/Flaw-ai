import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { lazy, Suspense } from "react";

const LoginPage = lazy(() => import("./components/Auth/LoginPage"));
const ChatPage = lazy(() => import("./components/Chat/ChatPage"));

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="loading-spinner" /></div>;
  return user ? children : <Navigate to="/login" replace />;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="loading-spinner" /></div>;
  return user ? <Navigate to="/" replace /> : children;
}

function LoadingFallback() {
  return (
    <div className="loading-screen">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="loading-logo">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="48" y2="48">
          <stop offset="0%" stopColor="#00d4ff"/><stop offset="100%" stopColor="#7c3aed"/>
        </linearGradient></defs>
        <circle cx="24" cy="24" r="22" stroke="url(#lg)" strokeWidth="2.5" fill="none"/>
        <path d="M16 18h16M16 24h12M16 30h8" stroke="url(#lg)" strokeWidth="2.5" strokeLinecap="round"/>
      </svg>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
            <Route path="/" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
