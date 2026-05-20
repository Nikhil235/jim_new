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
      console.error('Reset code error:', err);
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
      console.error('Password reset error:', err);
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

      <div className="login-glass-card animate-in">
        <div className="login-header">
          <div className="login-logo-icon">M</div>
          <h2>Reset Password</h2>
          <p>Secure Access Protocol</p>
        </div>

        {error && (
          <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,77,106,0.1)', border: '1px solid rgba(255,77,106,0.2)', color: 'var(--red)', fontSize: '13px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
            {error}
          </div>
        )}

        {successMessage && (
          <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(0,196,140,0.1)', border: '1px solid rgba(0,196,140,0.2)', color: 'var(--green)', fontSize: '13px', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
            {successMessage}
          </div>
        )}

        {step === 1 ? (
          /* Step 1: Input Email */
          <form onSubmit={handleSendCode} className="login-form">
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '8px' }}>
              Enter your registered email address to receive a secure password reset code.
            </p>

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

            <button
              type="submit"
              disabled={isLoading}
              className="login-button"
            >
              {isLoading ? (
                <Activity className="spin-icon" size={18} />
              ) : (
                <>
                  Send Reset Code <ChevronRight size={18} />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Step 2: Input Verification Code & New Password */
          <form onSubmit={handleResetPassword} className="login-form">
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '8px' }}>
              Enter the reset code sent to <span style={{ color: 'var(--text-bright)', fontWeight: 500 }}>{email}</span> and configure your new password.
            </p>

            <div className="input-group">
              <input
                type="text"
                placeholder="Verification Code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                style={{ textAlign: 'center', letterSpacing: '4px', fontFamily: 'var(--font-mono)', fontSize: '18px' }}
              />
              <ShieldAlert className="input-icon" size={18} />
            </div>

            <div className="input-group">
              <input
                type="password"
                placeholder="New Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock className="input-icon" size={18} />
            </div>

            <div className="input-group">
              <input
                type="password"
                placeholder="Confirm New Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              <KeyRound className="input-icon" size={18} />
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
                  Reset Password <ChevronRight size={18} />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => setStep(1)}
              style={{ fontSize: '12px', color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', marginTop: '8px', textAlign: 'center' }}
            >
              Request a new code
            </button>
          </form>
        )}

        <div className="auth-footer-link">
          Back to{' '}
          <Link to="/sign-in">Sign In</Link>
        </div>
      </div>
    </div>
  );
}
