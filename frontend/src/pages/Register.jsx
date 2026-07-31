import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../hooks/useAuth';
import rybbit from '../services/rybbit';

const Register = () => {
  const [formData, setFormData] = useState({ email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register, googleLogin } = useAuth();
  const navigate = useNavigate();

  const handleChange = (event) => setFormData({ ...formData, [event.target.name]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (formData.password !== formData.confirmPassword) return setError('Passwords do not match');
    if (formData.password.length < 8) return setError('Password must be at least 8 characters');
    setLoading(true);
    const result = await register({ email: formData.email, password: formData.password });
    if (result.success) {
      rybbit.track('Sign Up', { method: 'email' });
      navigate('/dashboard');
    } else setError(result.error);
    setLoading(false);
  };

  const handleGoogle = async (credential) => {
    setLoading(true);
    const result = await googleLogin(credential);
    if (result.success) {
      rybbit.track('Sign Up', { method: 'google' });
      navigate('/dashboard');
    } else setError(result.error);
    setLoading(false);
  };

  return (
    <div className="page-shell">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl lg:grid-cols-[1fr_0.85fr]">
        <section className="flex items-start px-5 py-12 sm:px-7 sm:py-16 lg:items-center lg:border-r lg:border-line lg:py-20">
          <div className="w-full max-w-md">
            <p className="eyebrow mb-3">Start watching</p>
            <h1 className="section-title mb-2">Create your account</h1>
            <p className="mb-8 text-sm text-muted">Free to use. No Purdue credentials required.</p>

            {error && <div role="alert" className="mb-5 rounded-md border border-line border-l-[3px] border-l-danger bg-canvas px-4 py-3 text-sm text-danger">{error}</div>}

            <div className="mb-6 flex justify-start">
              <GoogleLogin onSuccess={(response) => handleGoogle(response.credential)} onError={() => setError('Google sign up failed')} useOneTap theme="outline" shape="rectangular" />
            </div>

            <div className="mb-6 flex items-center gap-3 text-xs text-muted">
              <span className="h-px flex-1 bg-line" />
              Or sign up with email
              <span className="h-px flex-1 bg-line" />
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium">Email</label>
                <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required className="input-field" placeholder="you@example.com" autoComplete="email" />
              </div>
              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium">Password</label>
                <input id="password" name="password" type="password" value={formData.password} onChange={handleChange} required minLength={8} className="input-field" placeholder="••••••••" autoComplete="new-password" />
                <p className="mt-1.5 text-xs text-muted">Use at least 8 characters.</p>
              </div>
              <div>
                <label htmlFor="confirmPassword" className="mb-2 block text-sm font-medium">Confirm password</label>
                <input id="confirmPassword" name="confirmPassword" type="password" value={formData.confirmPassword} onChange={handleChange} required minLength={8} className="input-field" placeholder="••••••••" autoComplete="new-password" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Creating account…' : 'Create account'}
              </button>
            </form>
            <p className="mt-6 text-sm text-muted">
              Already have an account? <Link to="/login" className="font-semibold text-ink underline decoration-purdue-gold decoration-2 underline-offset-4">Sign in</Link>
            </p>
          </div>
        </section>

        <aside className="hidden bg-paper px-12 py-20 lg:flex lg:items-center">
          <div className="max-w-sm">
            <p className="eyebrow mb-5">What happens next</p>
            <h2 className="font-display text-3xl font-medium leading-tight">One account. Any section. No refreshing.</h2>
            <ol className="mt-8 space-y-6 text-sm leading-6 text-muted">
              <li><span className="font-mono text-xs text-deep-gold">01</span><br />Search the current Purdue course catalog.</li>
              <li><span className="font-mono text-xs text-deep-gold">02</span><br />Choose the exact CRN you need.</li>
              <li><span className="font-mono text-xs text-deep-gold">03</span><br />Wait for an email when availability changes.</li>
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default Register;
