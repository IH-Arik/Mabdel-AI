import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Lock, Loader2, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, error, isLoading } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    await login(email, password);
  };

  return (
    <div className="min-h-screen bg-[#f6f4ef] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Decorative Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-teal-200/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-teal-300/10 rounded-full blur-3xl animate-pulse" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="glass-card p-8 md:p-12 shadow-2xl relative overflow-hidden">
          {/* Logo Section */}
          <div className="text-center mb-10">
            <div className="w-16 h-16 bg-teal-700 text-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-xl shadow-teal-700/20">
              <span className="text-3xl font-bold">M</span>
            </div>
            <h1 className="text-3xl font-extrabold text-teal-900 tracking-tight flex items-center justify-center gap-2">
              Mabdel AI <Sparkles size={24} className="text-teal-500" />
            </h1>
            <p className="text-teal-700/60 mt-2 font-medium">Your Intelligent Business Companion</p>
          </div>

          {error && (
            <motion.div 
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm flex items-center gap-2"
            >
              <ShieldCheck size={18} />
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-teal-900 ml-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-teal-400" size={18} />
                <input 
                  type="email" 
                  placeholder="name@company.com"
                  className="w-full pl-12 pr-4 py-4 bg-white/50 border border-teal-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20 transition-all font-medium"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-teal-900 ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-teal-400" size={18} />
                <input 
                  type="password" 
                  placeholder="••••••••"
                  className="w-full pl-12 pr-4 py-4 bg-white/50 border border-teal-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20 transition-all font-medium"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-sm px-1">
              <label className="flex items-center gap-2 text-teal-700/70 cursor-pointer hover:text-teal-900 transition-colors">
                <input type="checkbox" className="rounded border-teal-200 text-teal-600 focus:ring-teal-500/20 w-4 h-4" />
                Remember me
              </label>
              <a href="#" className="text-teal-600 font-bold hover:underline">Forgot password?</a>
            </div>

            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full py-4 bg-teal-700 text-white rounded-xl font-bold text-lg shadow-xl shadow-teal-700/20 hover:bg-teal-800 transition-all active:scale-[0.98] disabled:opacity-70 flex items-center justify-center gap-3 group"
            >
              {isLoading ? (
                <Loader2 className="animate-spin" size={24} />
              ) : (
                <>
                  Sign In to Dashboard
                  <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-teal-700/60 text-sm font-medium">
            Don't have an account yet?{' '}
            <a href="#" className="text-teal-700 font-bold hover:underline decoration-teal-300 decoration-2 underline-offset-4">Get Early Access</a>
          </p>
        </div>
        
        {/* Footer info */}
        <p className="text-center mt-8 text-teal-700/40 text-xs font-medium uppercase tracking-widest">
          Secured by Mabdel Cloud Engine • v2.0.4
        </p>
      </motion.div>
    </div>
  );
};

export default LoginPage;
