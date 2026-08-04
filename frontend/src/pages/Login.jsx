import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../hooks/useAuth';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    const result = await login(email, password);
    if (result.success) navigate('/dashboard');
    else setError(result.error);
    setLoading(false);
  };

  const handleGoogle = async (credential) => {
    setLoading(true);
    const result = await googleLogin(credential);
    if (result.success) navigate('/dashboard');
    else setError(result.error);
    setLoading(false);
  };

  return (
    <div className="page-shell">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl lg:grid-cols-[1fr_0.85fr]">
        <section className="flex items-start px-5 py-12 sm:px-7 sm:py-16 lg:items-center lg:border-r lg:border-line lg:py-20">
          <div className="w-full max-w-md">
            <p className="eyebrow mb-3">Welcome back</p>
            <h1 className="section-title mb-2">Sign in</h1>
            <p className="mb-8 text-sm text-muted">Return to your watchlist and notification settings.</p>

            {error && <div role="alert" className="mb-5 rounded-md border border-line border-l-[3px] border-l-danger bg-canvas px-4 py-3 text-sm text-danger">{error}</div>}

            <div className="mb-6 flex justify-start">
              <GoogleLogin
                onSuccess={(response) => handleGoogle(response.credential)}
                onError={() => setError('Google sign in failed')}
                useOneTap
                theme="outline"
                shape="rectangular"
              />
            </div>

            <div className="mb-6 flex items-center gap-3 text-xs text-muted">
              <span className="h-px flex-1 bg-line" />
              Or continue with email
              <span className="h-px flex-1 bg-line" />
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium">Email</label>
                <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="input-field" placeholder="you@example.com" autoComplete="email" />
              </div>
              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium">Password</label>
                <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="input-field" placeholder="••••••••" autoComplete="current-password" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
            <p className="mt-6 text-sm text-muted">
              New to BoilerSnipe? <Link to="/register" className="font-semibold text-ink underline decoration-purdue-gold decoration-2 underline-offset-4">Create an account</Link>
            </p>
          </div>
        </section>

        <aside className="hidden bg-paper px-12 py-20 lg:flex lg:items-center">
          <div className="max-w-sm">
            <p className="eyebrow mb-5">Why sign in</p>
            <h2 className="font-display text-3xl font-medium leading-tight">Your watchlist follows you, not your browser.</h2>
            <div className="mt-8 space-y-6 text-sm leading-6 text-muted">
              <p><span className="font-mono text-xs text-deep-gold">01</span><br />Keep every watched CRN and notification preference together.</p>
              <p><span className="font-mono text-xs text-deep-gold">02</span><br />Get availability emails without sharing a Purdue login.</p>
              <p><span className="font-mono text-xs text-deep-gold">03</span><br />BoilerSnipe is free and open source.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default Login;
