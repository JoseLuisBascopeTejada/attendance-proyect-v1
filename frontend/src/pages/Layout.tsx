import { Outlet, Link, useLocation } from 'react-router-dom';
import '../App.css';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/register', label: 'Registrar' },
  { path: '/recognize', label: 'Reconocer' },
  { path: '/recognize-group', label: 'Reconocimiento Grupal' },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-logo">
          Sistema de Asistencia
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
        <Outlet />
      </main>
    </div>
  );
}
