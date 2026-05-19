import { useState } from 'react';
import { useSignIn, useClerk, useAuth } from '@clerk/react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, ChevronRight, Activity, ShieldAlert, KeyRound } from 'lucide-react';

export default function ForgotPassword() {
  const { signIn } = useSignIn();
  const { setActive } = useClerk();
  const { isLoaded } = useAuth();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [step, setStep] = useState(1); // 1 = Enter Email, 2 = Verify Code & New Password
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const navigate = useNavigate();

  const handleSendCode = async (e) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setIsLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      // 1. Create a sign in attempt specifying the strategy and identifier
      await signIn.create({
        strategy: 'reset_password_email_code',
        identifier: email,
      });

      setSuccessMessage('A reset code has been sent to your email.');
      setStep(2);
    } catch (err) {
      console.error(err);
      setError(err.errors?.[0]?.message || 'Failed to send reset code. Please verify your email.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // 2. Attempt verification with code and the new password
      const result = await signIn.attemptFirstFactor({
        strategy: 'reset_password_email_code',
        code: code,
        password: password,
      });

      if (result.status === 'complete') {
        // Log the user in with their active session
        await setActive({ session: result.createdSessionId });
        setSuccessMessage('Password reset successfully. Redirecting...');
        setTimeout(() => {
          navigate('/dashboard');
        }, 1500);
      } else {
        console.log('Reset password status not complete:', result.status);
        setError('Verification complete, but password reset failed. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setError(err.errors?.[0]?.message || 'Failed to reset password. The code might be incorrect or expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Background Orbs */}
      <div className="orb orb-1"></div>
      <div className="orb orb-2"></div>
      <div className="orb orb-3"></div>

      <div className="login-glass-card animate-in max-w-md w-full p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl relative z-10">
        <div className="login-header text-center mb-8">
          <div className="login-logo-icon w-14 h-14 bg-gradient-to-br from-gold-primary to-gold-secondary rounded-xl flex items-center justify-center text-2xl font-extrabold text-bg-primary shadow-lg mx-auto mb-4">M</div>
          <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Reset Password</h2>
          <p className="text-xs text-gold-primary font-semibold uppercase tracking-wider">Secure Access Protocol</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg text-center">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 text-green-400 text-sm rounded-lg text-center">
            {successMessage}
          </div>
        )}

        {step === 1 ? (
          /* Step 1: Input Email */
          <form onSubmit={handleSendCode} className="flex flex-col gap-4">
            <p className="text-sm text-text-secondary text-center mb-2">
              Enter your registered email address to receive a secure password reset code.
            </p>

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

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 mt-2 bg-gradient-to-r from-gold-primary to-gold-secondary hover:from-gold-secondary hover:to-gold-primary text-bg-primary font-bold rounded-lg shadow-md cursor-pointer transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:transform-none"
            >
              {isLoading ? (
                <Activity className="spin-icon animate-spin" size={18} />
              ) : (
                <>
                  Send Reset Code <ChevronRight size={18} />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Step 2: Input Verification Code & New Password */
          <form onSubmit={handleResetPassword} className="flex flex-col gap-4">
            <p className="text-sm text-text-secondary text-center mb-2">
              Enter the reset code sent to <span className="text-white font-medium">{email}</span> and configure your new password.
            </p>

            <div className="input-group">
              <input
                type="text"
                placeholder="Verification Code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white placeholder-slate-500 text-center tracking-widest font-mono text-lg focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all"
              />
              <ShieldAlert className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors" size={18} />
            </div>

            <div className="input-group">
              <input
                type="password"
                placeholder="New Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all"
              />
              <Lock className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors" size={18} />
            </div>

            <div className="input-group">
              <input
                type="password"
                placeholder="Confirm New Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all"
              />
              <KeyRound className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors" size={18} />
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
                  Reset Password <ChevronRight size={18} />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-xs text-text-muted hover:text-white transition-colors mt-2 text-center bg-transparent border-none cursor-pointer"
            >
              Request a new code
            </button>
          </form>
        )}

        <div className="mt-6 text-center text-sm text-text-secondary">
          Back to{' '}
          <Link to="/sign-in" className="text-gold-primary hover:text-gold-secondary font-medium transition-colors">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
