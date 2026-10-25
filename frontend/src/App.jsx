import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { FloatingVoiceBot } from './components/FloatingVoiceBot';
import { SiteFooter } from './components/SiteFooter';
import { AuthProvider } from './auth/AuthContext';
import { useAuth } from './hooks/useAuth';
import { AuthLoadingScreen } from './components/AuthLoadingScreen';
import AuthPage from './pages/AuthPage';
import Landing from './pages/Landing';
import FormFill from './pages/FormFill';
import Schemes from './pages/Schemes';
import Guidance from './pages/Guidance';
import FraudCheck from './pages/FraudCheck';

function AuthEntry() {
  const { loading, isAuthenticated } = useAuth();
  if (loading) return <AuthLoadingScreen />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <AuthPage />;
}

function AppShell() {
  return (
    <>
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/form-fill" element={<FormFill />} />
          <Route path="/schemes" element={<Schemes />} />
          <Route path="/guidance" element={<Guidance />} />
          <Route path="/fraud-check" element={<FraudCheck />} />
        </Routes>
      </main>

      {/* Persistent Bottom-Right Voice Chatbot (matching user sketch) */}
      <FloatingVoiceBot />

      <SiteFooter />
    </>
  );
}

function ProtectedShell() {
  const { loading, isAuthenticated } = useAuth();
  const location = useLocation();
  if (loading) return <AuthLoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/auth" replace state={{ from: location }} />;
  return <AppShell />;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/auth" element={<AuthEntry />} />
          <Route path="*" element={<ProtectedShell />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
