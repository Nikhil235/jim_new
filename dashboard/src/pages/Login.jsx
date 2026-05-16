import { useState } from 'react';
import { Lock, User, ChevronRight, Activity } from 'lucide-react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate secure auth delay
    setTimeout(() => {
      setIsLoading(false);
      onLogin();
    }, 1500);
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
          <p>Institutional Gold Trading Engine</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <input 
              type="text" 
              placeholder="System ID or Username" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required 
            />
            <User className="input-icon" size={18} />
          </div>
          
          <div className="input-group">
            <input 
              type="password" 
              placeholder="Encryption Key" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
            <Lock className="input-icon" size={18} />
          </div>

          <button type="submit" className={`login-button ${isLoading ? 'loading' : ''}`} disabled={isLoading}>
            {isLoading ? (
              <Activity className="spin-icon" size={20} />
            ) : (
              <>
                Initialize Link <ChevronRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="login-footer">
          <div className="status-badge" style={{ justifyContent: 'center' }}>
            <span className="status-dot online"></span>
            <span>Engine Ready • Secure Connection</span>
          </div>
        </div>
      </div>
    </div>
  );
}
