import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { FloatingVoiceBot } from './components/FloatingVoiceBot';
import { SiteFooter } from './components/SiteFooter';
import Landing from './pages/Landing';
import FormFill from './pages/FormFill';
import Schemes from './pages/Schemes';
import Guidance from './pages/Guidance';
import FraudCheck from './pages/FraudCheck';

export default function App() {
  return (
    <Router>
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
    </Router>
  );
}
