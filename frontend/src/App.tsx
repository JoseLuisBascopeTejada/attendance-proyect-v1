import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Register } from './pages/Register';
import { Recognize } from './pages/Recognize';
import { RecognizeGroup } from './pages/RecognizeGroup';
import './App.css';

function Dashboard() {
  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8, color: 'var(--text-h)' }}>
        Dashboard
      </h1>
      <p style={{ color: 'var(--text)' }}>Coming in Phase 4.</p>
    </div>
  );
}

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/register', label: 'Register' },
  { path: '/recognize', label: 'Recognize' },
  { path: '/recognize-group', label: 'Recognize Group' },
];

function App() {
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-logo">
          Face Attendance
        </Link>
        <nav className="app-nav">
          {NAV_ITEMS.map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={`nav-link ${location.pathname === path ? 'active' : ''}`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/register" element={<Register />} />
          <Route path="/recognize" element={<Recognize />} />
          <Route path="/recognize-group" element={<RecognizeGroup />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
