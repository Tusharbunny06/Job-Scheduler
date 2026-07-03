import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

export default function Login() {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      if (isRegistering) {
        // Register the user
        await apiClient.post('/auth/register', {
          email,
          password,
          full_name: email.split('@')[0]
        });
      }

      // Log them in (works for both existing users and newly registered ones)
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      localStorage.setItem('token', response.data.access_token);
      navigate('/');
    } catch (err: any) {
      console.error('Auth failed', err);
      const serverMsg = err?.response?.data?.detail;
      const networkErr = err?.code === 'ERR_NETWORK' || err?.code === 'ECONNREFUSED';
      if (networkErr) {
        setError('Cannot reach server. Make sure the backend is running on port 8000.');
      } else if (serverMsg) {
        setError(typeof serverMsg === 'string' ? serverMsg : JSON.stringify(serverMsg));
      } else {
        setError(`${isRegistering ? 'Registration' : 'Login'} failed. Please try again.`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <div className="w-full max-w-md bg-white p-8 rounded-xl shadow-md border border-slate-200">
        
        {/* Toggle Header */}
        <div className="flex justify-center mb-8 border-b border-slate-200">
          <button 
            className={`pb-3 px-6 text-lg font-medium border-b-2 transition-colors ${!isRegistering ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            onClick={() => { setIsRegistering(false); setError(''); }}
          >
            Sign In
          </button>
          <button 
            className={`pb-3 px-6 text-lg font-medium border-b-2 transition-colors ${isRegistering ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            onClick={() => { setIsRegistering(true); setError(''); }}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Email</label>
            <input 
              type="email" 
              required
              className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Password</label>
            <input 
              type="password" 
              required
              className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
          <button 
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {loading ? 'Processing…' : (isRegistering ? 'Create Account' : 'Sign in')}
          </button>
        </form>
      </div>
    </div>
  );
}
