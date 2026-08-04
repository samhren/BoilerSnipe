import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const exampleSections = [
  { code: 'CS 18000', meta: 'CRN 12345 · MWF 9:30 AM', status: '1 seat available', tone: 'bg-available', muted: false },
  { code: 'CS 18000', meta: 'CRN 18732 · TR 1:30 PM', status: '2 seats left', tone: 'bg-limited', muted: false },
  { code: 'MA 26100', meta: 'CRN 33210 · TR 2:30 PM', status: 'Full', tone: 'bg-muted', muted: true },
];

const steps = [
  ['01', 'Find a section', 'Search by subject, course number, or CRN.'],
  ['02', 'Watch it', 'One click adds that exact section to your watchlist.'],
  ['03', 'Get an email', 'We check public course pages every five minutes.'],
  ['04', 'Register through Purdue', 'BoilerSnipe never registers or holds a seat for you.'],
];

const Home = () => {
  const { user } = useAuth();

  return (
    <div className="page-shell">
      <section className="border-b border-line">
        <div className="page-container grid items-start gap-12 py-14 sm:py-20 lg:grid-cols-[1fr_0.92fr] lg:gap-20">
          <div>
            <p className="eyebrow mb-4">Fall 2026 · checked every 5 minutes</p>
            {user ? (
              <>
                <h1 className="display-title max-w-xl">Your next seat could open at any time.</h1>
                <p className="mt-5 max-w-lg text-lg leading-8 text-muted">
                  Keep an eye on every section from one calm watchlist. We’ll email you as soon as availability changes.
                </p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <Link to="/dashboard" className="btn-primary">Open my watchlist</Link>
                  <Link to="/search" className="btn-secondary">Search sections</Link>
                </div>
              </>
            ) : (
              <>
                <h1 className="display-title max-w-xl">The seat you need, without the constant refreshing.</h1>
                <p className="mt-5 max-w-lg text-lg leading-8 text-muted">
                  Choose a Purdue section. BoilerSnipe checks it every five minutes and emails you when availability changes—no Purdue login, no auto-registration.
                </p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <Link to="/register" className="btn-primary">Find a section</Link>
                  <Link to="/login" className="btn-secondary">Sign in</Link>
                </div>
                <p className="mono-detail mt-5">Free · No Purdue login · Does not register for you</p>
              </>
            )}
          </div>

          <div className="pt-1 lg:pt-8" aria-label="Example course watchlist">
            <p className="mb-2 text-xs text-muted">Example watchlist</p>
            <div className="surface overflow-hidden">
              {exampleSections.map((section) => (
                <div key={section.meta} className="flex flex-col gap-3 border-b border-line p-4 last:border-0 sm:flex-row sm:items-center sm:justify-between">
                  <div className={section.muted ? 'text-muted' : ''}>
                    <div className="text-sm font-semibold">{section.code} · Lecture</div>
                    <div className="mono-detail mt-1">{section.meta}</div>
                  </div>
                  <div className={`flex items-center gap-2 text-sm ${section.muted ? 'text-muted' : ''}`}>
                    <span className={`status-dot ${section.tone}`} />
                    {section.status}
                  </div>
                </div>
              ))}
            </div>
            <p className="mono-detail mt-3 leading-5">
              Sections track independently by CRN and meeting time, even when the course code is the same.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-line">
        <div className="mx-auto grid max-w-6xl sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(([number, title, description], index) => (
            <div key={number} className={`px-5 py-8 sm:px-7 lg:py-10 ${index ? 'border-t border-line sm:border-l sm:border-t-0' : ''} ${index === 2 ? 'sm:border-t lg:border-t-0' : ''}`}>
              <div className="mb-3 font-mono text-xs text-deep-gold">{number}</div>
              <h2 className="mb-1 text-sm font-semibold">{title}</h2>
              <p className="text-sm leading-6 text-muted">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="page-container grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <div>
          <p className="eyebrow mb-3">Made for students</p>
          <h2 className="section-title">A simple watcher, and nothing more.</h2>
        </div>
        <div className="grid gap-8 text-sm leading-7 text-muted sm:grid-cols-2">
          <p>
            BoilerSnipe reads the same public course availability pages anyone can view. It never asks for your Purdue credentials or accesses a student account.
          </p>
          <p>
            It sends a notification when a seat changes. You still make every registration decision yourself in Purdue’s official system.
          </p>
        </div>
      </section>
    </div>
  );
};

export default Home;
