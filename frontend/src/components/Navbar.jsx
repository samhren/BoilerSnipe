import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import rybbit from '../services/rybbit';

const Navbar = () => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = user
    ? [{ to: '/dashboard', label: 'Watchlist' }, { to: '/search', label: 'Search' }]
    : [{ to: '/about', label: 'About' }];

  const handleNav = (destination) => {
    setMenuOpen(false);
    rybbit.track('Navigation Click', {
      destination,
      from: location.pathname,
      is_authenticated: !!user,
    });
  };

  const linkClass = (path) => `border-b py-2 text-sm font-medium transition-colors sm:border-0 ${
    location.pathname === path
      ? 'border-ink text-ink'
      : 'border-transparent text-muted hover:text-ink'
  }`;

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-canvas/95 backdrop-blur">
      <nav className="mx-auto max-w-6xl px-5 sm:px-7" aria-label="Main navigation">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link
              to="/"
              className="flex items-center gap-2.5 text-[15px] font-semibold tracking-[-0.01em]"
              onClick={() => handleNav('/')}
            >
              <img src="/boilersnipe.svg" alt="" className="h-6 w-6" />
              BoilerSnipe
            </Link>

            <div className="hidden items-center gap-6 sm:flex">
              {navItems.map((item) => (
                <Link key={item.to} to={item.to} onClick={() => handleNav(item.to)} className={linkClass(item.to)}>
                  {item.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="hidden items-center gap-5 sm:flex">
            {user ? (
              <>
                <span className="max-w-52 truncate font-mono text-xs text-muted">{user.email}</span>
                <button onClick={logout} className="text-sm font-medium text-muted hover:text-ink">Sign out</button>
                <Link to="/search" onClick={() => handleNav('/search')} className="btn-primary min-h-10 px-4 py-2 text-sm">
                  Find a section
                </Link>
              </>
            ) : (
              <>
                <Link to="/login" onClick={() => handleNav('/login')} className="text-sm font-medium text-muted hover:text-ink">
                  Sign in
                </Link>
                <Link to="/register" onClick={() => handleNav('/register')} className="btn-primary min-h-10 px-4 py-2 text-sm">
                  Find a section
                </Link>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-ink sm:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          >
            <span className="sr-only">Menu</span>
            <span aria-hidden="true" className="font-mono text-lg">{menuOpen ? '×' : '≡'}</span>
          </button>
        </div>

        {menuOpen && (
          <div id="mobile-menu" className="border-t border-line pb-5 pt-2 sm:hidden">
            <div className="flex flex-col">
              {navItems.map((item) => (
                <Link key={item.to} to={item.to} onClick={() => handleNav(item.to)} className={linkClass(item.to)}>
                  {item.label}
                </Link>
              ))}
              {user && <div className="py-3 font-mono text-xs text-muted">{user.email}</div>}
              <div className="mt-3 grid grid-cols-2 gap-3">
                {user ? (
                  <>
                    <button onClick={() => { logout(); setMenuOpen(false); }} className="btn-secondary text-sm">Sign out</button>
                    <Link to="/search" onClick={() => handleNav('/search')} className="btn-primary text-sm">Find a section</Link>
                  </>
                ) : (
                  <>
                    <Link to="/login" onClick={() => handleNav('/login')} className="btn-secondary text-sm">Sign in</Link>
                    <Link to="/register" onClick={() => handleNav('/register')} className="btn-primary text-sm">Get started</Link>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export default Navbar;
