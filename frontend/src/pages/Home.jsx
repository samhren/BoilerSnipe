import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';


const Home = () => {
  const { user } = useAuth();



  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero */}
      <div className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="text-center max-w-2xl mx-auto">
            <h1 className="text-4xl sm:text-5xl font-bold mb-4">
              <span className="text-amber-400">Boiler</span>Snipe
            </h1>
            <p className="text-lg sm:text-xl text-slate-300 mb-8">
              Get notified instantly when seats open up in your Purdue courses
            </p>
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-400/10 px-4 py-2 text-sm font-medium text-amber-200 mb-8">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              Updated for Fall 2026 courses
            </div>

            {user ? (
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link
                  to="/dashboard"

                  className="px-6 py-3 bg-white text-slate-900 rounded-lg font-semibold hover:bg-slate-100 transition-colors"
                >
                  Go to Dashboard
                </Link>
                <Link
                  to="/search"

                  className="px-6 py-3 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700 transition-colors border border-slate-700"
                >
                  Search Courses
                </Link>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link
                  to="/register"

                  className="px-6 py-3 bg-amber-500 text-slate-900 rounded-lg font-semibold hover:bg-amber-400 transition-colors"
                >
                  Get Started
                </Link>
                <Link
                  to="/login"

                  className="px-6 py-3 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700 transition-colors border border-slate-700"
                >
                  Login
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <div className="grid sm:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Search Courses</h3>
            <p className="text-slate-500 text-sm">
              Find courses by subject code, course number, or CRN
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Track Availability</h3>
            <p className="text-slate-500 text-sm">
              We check seat availability every 5 minutes automatically
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Instant Alerts</h3>
            <p className="text-slate-500 text-sm">
              Get an email notification the moment a seat opens
            </p>
          </div>
        </div>

        {/* How it works */}
        <div className="mt-12 sm:mt-16 bg-white rounded-xl border border-slate-200 p-6 sm:p-8">
          <h2 className="text-xl font-bold text-slate-800 mb-6">How it works</h2>
          <div className="space-y-4">
            {[
              { step: 1, title: 'Create an account', desc: 'Sign up with your email' },
              { step: 2, title: 'Search for courses', desc: 'Find the courses you want to track' },
              { step: 3, title: 'Start tracking', desc: 'Add courses to your watchlist' },
              { step: 4, title: 'Get notified', desc: 'Receive instant alerts when seats open' },
            ].map(item => (
              <div key={item.step} className="flex gap-4">
                <div className="w-8 h-8 bg-amber-500 text-slate-900 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0">
                  {item.step}
                </div>
                <div>
                  <div className="font-medium text-slate-800">{item.title}</div>
                  <div className="text-slate-500 text-sm">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
