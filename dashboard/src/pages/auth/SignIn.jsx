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
      await signIn.sso({
        strategy: 'oauth_google',
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/dashboard',
      });
    } catch (err) {
      console.error(err);
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
      console.error(err);
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

      <div className="login-glass-card animate-in max-w-md w-full p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl relative z-10">
        <div className="login-header text-center mb-8">
          <div className="login-logo-icon w-14 h-14 bg-gradient-to-br from-gold-primary to-gold-secondary rounded-xl flex items-center justify-center text-2xl font-extrabold text-bg-primary shadow-lg mx-auto mb-4">M</div>
          <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Mini-Medallion</h2>
          <p className="text-xs text-gold-primary font-semibold uppercase tracking-wider">Institutional Gold Trading</p>
        </div>

        <h3 className="text-lg font-medium text-white mb-6 text-center">Sign In to Dashboard</h3>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg text-center">
            {error}
          </div>
        )}

        {/* Google OAuth Login Button */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-3 py-3 px-4 mb-6 rounded-lg bg-white/5 border border-white/10 text-white font-medium text-sm hover:bg-white/10 transition-all duration-200 cursor-pointer disabled:opacity-50"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
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

        <div className="flex items-center my-6">
          <div className="flex-grow border-t border-white/5"></div>
          <span className="mx-4 text-xs text-text-muted font-medium uppercase tracking-wider">or sign in with email</span>
          <div className="flex-grow border-t border-white/5"></div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="input-group">
            <input
              type="email"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all"
            />
            <Mail className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors" size={18} />
          </div>

          <div className="input-group">
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all"
            />
            <Lock className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors" size={18} />
          </div>

          <div className="flex justify-end text-xs">
            <Link to="/forgot-password" className="text-gold-primary hover:text-gold-secondary transition-colors">
              Forgot Password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 mt-2 bg-gradient-to-r from-gold-primary to-gold-secondary hover:from-gold-secondary hover:to-gold-primary text-bg-primary font-bold rounded-lg shadow-md cursor-pointer transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:transform-none"
          >
            {isLoading ? (
              <Activity className="spin-icon animate-spin" size={18} />
            ) : (
              <>
                Sign In <ChevronRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-text-secondary">
          Don't have an account?{' '}
          <Link to="/sign-up" className="text-gold-primary hover:text-gold-secondary font-medium transition-colors">
            Sign Up
          </Link>
        </div>
      </div>
    </div>
  );
}
