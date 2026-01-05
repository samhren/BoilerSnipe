import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { trackEvent, EVENTS } from '../hooks/usePostHog';

const Navbar = () => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const handleNavClick = (destination) => {
    trackEvent(EVENTS.NAV_CLICK, {
      destination,
      from: location.pathname,
      is_authenticated: !!user,
    });
  };

  const handleMobileMenuToggle = () => {
    const newState = !menuOpen;
    setMenuOpen(newState);
    trackEvent(EVENTS.MOBILE_MENU_TOGGLE, { opened: newState });
  };

  return (
    <nav className="bg-slate-900 text-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex justify-between items-center h-14">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2" onClick={() => { setMenuOpen(false); handleNavClick('/'); }}>
            <span className="text-xl">🎯</span>
            <span className="font-bold text-lg">BoilerSnipe</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden sm:flex items-center gap-1">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  onClick={() => handleNavClick('/dashboard')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/dashboard') ? 'bg-slate-800 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/search"
                  onClick={() => handleNavClick('/search')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/search') ? 'bg-slate-800 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  Search
                </Link>
                <div className="w-px h-6 bg-slate-700 mx-2"></div>
                <span className="text-sm text-slate-400 px-2">{user.email}</span>
                <button
                  onClick={logout}
                  className="px-3 py-2 text-sm text-slate-300 hover:text-white transition-colors"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => handleNavClick('/login')}
                  className="px-3 py-2 text-sm text-slate-300 hover:text-white transition-colors"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  onClick={() => handleNavClick('/register')}
                  className="px-4 py-2 bg-amber-500 text-slate-900 rounded-lg text-sm font-semibold hover:bg-amber-400 transition-colors"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={handleMobileMenuToggle}
            className="sm:hidden p-2 text-slate-300 hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="sm:hidden border-t border-slate-800 py-3 space-y-1">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  onClick={() => { setMenuOpen(false); handleNavClick('/dashboard'); }}
                  className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                    isActive('/dashboard') ? 'bg-slate-800 text-white' : 'text-slate-300'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/search"
                  onClick={() => { setMenuOpen(false); handleNavClick('/search'); }}
                  className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                    isActive('/search') ? 'bg-slate-800 text-white' : 'text-slate-300'
                  }`}
                >
                  Search
                </Link>
                <div className="border-t border-slate-800 my-2"></div>
                <div className="px-3 py-2 text-sm text-slate-400">{user.email}</div>
                <button
                  onClick={() => { logout(); setMenuOpen(false); }}
                  className="block w-full text-left px-3 py-2 text-sm text-slate-300"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => { setMenuOpen(false); handleNavClick('/login'); }}
                  className="block px-3 py-2 text-sm text-slate-300"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  onClick={() => { setMenuOpen(false); handleNavClick('/register'); }}
                  className="block px-3 py-2 text-sm font-semibold text-amber-500"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
