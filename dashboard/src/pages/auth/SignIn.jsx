import { useState } from 'react';
import { useSignIn, useClerk, useAuth } from '@clerk/react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, ChevronRight, Activity } from 'lucide-react';

export default function SignIn() {
  const { signIn } = useSignIn();
  const { setActive } = useClerk();
  const { isLoaded } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleGoogleSignIn = async () => {
    if (!isLoaded || !signIn) return;
    setIsLoading(true);
    setError('');
    try {
      await signIn.authenticateWithRedirect({
        strategy: 'oauth_google',
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/dashboard',
      });
    } catch (err) {
      console.error('Google SSO error:', err);
      setError(err.errors?.[0]?.message || 'Failed to initialize Google OAuth');
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setIsLoading(true);
    setError('');

    try {
      const result = await signIn.create({
        identifier: email,
        password,
      });

      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId });
        navigate('/dashboard');
      } else {
        console.log('SignIn status not complete:', result.status);
        setError('Authentication incomplete. Please contact support.');
      }
    } catch (err) {
      console.error('Email sign-in error:', err);
      setError(err.errors?.[0]?.message || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Background Orbs for dynamic aesthetic */}
      <div className="orb orb-1"></div>
      <div className="orb orb-2"></div>
      <div className="orb orb-3"></div>

      <div className="login-glass-card animate-in">
        <div className="login-header">
          <div className="login-logo-icon">M</div>
          <h2>Mini-Medallion</h2>
          <p>Institutional Gold Trading</p>
        </div>

        <h3 style={{ fontSize: '17px', fontWeight: 500, color: 'var(--text-bright)', marginBottom: '24px', textAlign: 'center' }}>Sign In to Dashboard</h3>

        {error && (
          <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,77,106,0.1)', border: '1px solid rgba(255,77,106,0.2)', color: 'var(--red)', fontSize: '13px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
            {error}
          </div>
        )}

        {/* Google OAuth Login Button */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isLoading}
          className="google-oauth-btn"
        >
          <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24">
            <path
              fill="#EA4335"
              d="M12 5.04c1.62 0 3.08.56 4.22 1.66l3.15-3.15C17.45 1.74 14.93 1 12 1 7.35 1 3.4 3.65 1.5 7.5l3.6 2.8C6.01 7.2 8.76 5.04 12 5.04z"
            />
            <path
              fill="#4285F4"
              d="M23.49 12.27c0-.81-.07-1.59-.2-2.34H12v4.44h6.44c-.28 1.48-1.12 2.73-2.38 3.58l3.69 2.86c2.16-1.99 3.4-4.92 3.4-8.54z"
            />
            <path
              fill="#FBBC05"
              d="M5.1 14.8c-.24-.72-.38-1.49-.38-2.3s.14-1.58.38-2.3L1.5 7.4C.54 9.3 0 11.4 0 13.7s.54 4.4 1.5 6.3l3.6-2.9z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.24 0 5.97-1.07 7.96-2.91l-3.69-2.86c-1.03.69-2.34 1.1-4.27 1.1-3.24 0-5.99-2.16-6.96-5.06l-3.6 2.8C3.4 20.35 7.35 23 12 23z"
            />
          </svg>
          Continue with Google
        </button>

        <div className="auth-divider">
          <span>or sign in with email</span>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <input
              type="email"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Mail className="input-icon" size={18} />
          </div>

          <div className="input-group">
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Lock className="input-icon" size={18} />
          </div>

          <div style={{ textAlign: 'right' }}>
            <Link to="/forgot-password" style={{ fontSize: '12px', color: 'var(--gold-primary)' }}>
              Forgot Password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="login-button"
          >
            {isLoading ? (
              <Activity className="spin-icon" size={18} />
            ) : (
              <>
                Sign In <ChevronRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-footer-link">
          Don't have an account?{' '}
          <Link to="/sign-up">Sign Up</Link>
        </div>

        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
          <button
            type="button"
            onClick={() => {
              localStorage.setItem('AUTH_BYPASS', 'true');
              window.location.href = '/dashboard';
            }}
            style={{
              background: 'rgba(240,185,11,0.08)',
              border: '1px solid rgba(240,185,11,0.2)',
              color: 'var(--gold-primary)',
              padding: '10px 16px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              letterSpacing: '0.5px',
              transition: 'all 0.2s',
              width: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(240,185,11,0.15)';
              e.currentTarget.style.boxShadow = '0 0 12px rgba(240,185,11,0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(240,185,11,0.08)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            Bypass Sign In (Developer Mode)
          </button>
        </div>
      </div>
    </div>
  );
}
