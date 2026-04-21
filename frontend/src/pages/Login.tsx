import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import { jwtDecode } from 'jwt-decode';

interface JwtPayload {
  sub: string;
  role: string;
  exp: number;
}

const Login = () => {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'instructor' | 'ta'>('instructor');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      let token = '';
      if (tab === 'login') {
        const res = await API.post('/auth/login', { email, password });
        token = res.data.access_token;
      } else {
        const res = await API.post('/auth/register', { name, email, password, role });
        token = res.data.access_token;
      }
      const decoded = jwtDecode<JwtPayload>(token);
      login(token, decoded.role);
      if (decoded.role === 'instructor') navigate('/instructor');
      else navigate('/ta');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="bg-gray-900 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-800">
        <h1 className="text-3xl font-bold text-white mb-1">GradeOps</h1>
        <p className="text-gray-400 mb-6 text-sm">AI-powered exam grading platform</p>

        <div className="flex mb-6 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setTab('login')}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${tab === 'login' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Sign In
          </button>
          <button
            onClick={() => setTab('register')}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${tab === 'register' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === 'register' && (
            <div>
              <label className="text-gray-300 text-sm mb-1 block">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
                placeholder="Your full name"
                required
              />
            </div>
          )}

          <div>
            <label className="text-gray-300 text-sm mb-1 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
              placeholder="you@university.edu"
              required
            />
          </div>

          <div>
            <label className="text-gray-300 text-sm mb-1 block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
              placeholder="••••••••"
              required
            />
          </div>

          {tab === 'register' && (
            <div>
              <label className="text-gray-300 text-sm mb-1 block">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'instructor' | 'ta')}
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
              >
                <option value="instructor">Instructor / Professor</option>
                <option value="ta">Teaching Assistant (TA)</option>
              </select>
            </div>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition disabled:opacity-50"
          >
            {loading ? 'Please wait...' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
