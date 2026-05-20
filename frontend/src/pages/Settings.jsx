import { useCallback, useEffect, useState } from 'react';
import { Bell, CreditCard, Cpu, LifeBuoy, LogOut, Save, Shield, User } from 'lucide-react';
import { motion } from 'framer-motion';
import { smartflowApi } from '../api/services';
import { useAuthStore } from '../store/useAuthStore';

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'support', label: 'Support', icon: LifeBuoy },
  { id: 'ai', label: 'AI Configuration', icon: Cpu },
  { id: 'security', label: 'Security', icon: Shield },
];

export default function Settings() {
  const { user, logout, checkAuth } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [profile, setProfile] = useState({ full_name: '', email: '', country: '', language_preference: 'EN' });
  const [notifications, setNotifications] = useState({});
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [support, setSupport] = useState({ subject: '', message: '', topic: 'general' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadSettings = useCallback(async () => {
    try {
      const [settingsRes, notificationRes, plansRes, subscriptionRes] = await Promise.all([
        smartflowApi.getSettings(),
        smartflowApi.getNotificationSettings(),
        smartflowApi.getSubscriptionPlans(),
        smartflowApi.getCurrentSubscription(),
      ]);
      const data = settingsRes.data.data;
      setProfile({
        full_name: data.full_name || '',
        email: data.email || '',
        country: data.country || '',
        language_preference: data.language_preference || 'EN',
      });
      setNotifications(notificationRes.data.data || {});
      setPlans(plansRes.data.data || []);
      setSubscription(subscriptionRes.data.data || null);
    } catch (err) {
      setError(err.response?.data?.message || 'Settings could not be loaded.');
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  async function saveProfile() {
    setMessage('');
    setError('');
    try {
      await smartflowApi.updateSettings(profile);
      await checkAuth();
      setMessage('Profile saved.');
    } catch (err) {
      setError(err.response?.data?.message || 'Profile save failed.');
    }
  }

  async function saveNotifications(next = notifications) {
    setNotifications(next);
    await smartflowApi.updateNotificationSettings(next);
    setMessage('Notification settings saved.');
  }

  async function submitTicket(event) {
    event.preventDefault();
    setError('');
    try {
      await smartflowApi.createSupportTicket(support);
      setSupport({ subject: '', message: '', topic: 'general' });
      setMessage('Support ticket submitted.');
    } catch (err) {
      setError(err.response?.data?.message || 'Support ticket failed.');
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-teal-900">Settings</h1>
        <p className="text-teal-700/70">Manage profile, notifications, billing, support, and account security.</p>
      </div>

      {message && <div className="p-3 bg-green-50 border border-green-100 rounded-lg text-green-700 text-sm">{message}</div>}
      {error && <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-red-700 text-sm">{error}</div>}

      <div className="flex flex-col lg:flex-row gap-8">
        <div className="w-full lg:w-64 space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${activeTab === tab.id ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/20' : 'text-teal-700/70 hover:bg-white/50 hover:text-teal-900'}`}>
                <Icon size={20} /> {tab.label}
              </button>
            );
          })}
          <div className="pt-4 border-t border-teal-100">
            <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-red-600 hover:bg-red-50 transition-all">
              <LogOut size={20} /> Logout Session
            </button>
          </div>
        </div>

        <div className="flex-1">
          <motion.div key={activeTab} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="glass-card p-8 space-y-8">
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div className="flex items-center gap-6">
                  <div className="w-20 h-20 bg-teal-100 rounded-2xl flex items-center justify-center text-teal-700 text-3xl font-bold border-4 border-white shadow-xl">
                    {profile.full_name?.charAt(0) || user?.full_name?.charAt(0) || 'A'}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-teal-900">{profile.full_name || user?.full_name}</h3>
                    <p className="text-teal-700/60 text-sm mt-1">{profile.email || user?.email}</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  <input value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} placeholder="Full name" className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none" />
                  <input value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} placeholder="Email" className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none" />
                  <input value={profile.country || ''} onChange={(e) => setProfile({ ...profile, country: e.target.value })} placeholder="Country" className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none" />
                  <select value={profile.language_preference} onChange={(e) => setProfile({ ...profile, language_preference: e.target.value })} className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none">
                    <option value="EN">English</option>
                    <option value="BN">Bengali</option>
                    <option value="ES">Spanish</option>
                  </select>
                </div>
                <button onClick={saveProfile} className="flex items-center gap-2 px-8 py-3 bg-teal-600 text-white rounded-xl font-bold">
                  <Save size={20} /> Save Changes
                </button>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-4">
                {Object.entries(notifications).map(([key, value]) => (
                  <label key={key} className="flex items-center justify-between p-4 border border-teal-50 rounded-xl">
                    <span className="font-semibold text-teal-900 capitalize">{key.replace(/_/g, ' ')}</span>
                    <input type="checkbox" checked={Boolean(value)} onChange={(e) => saveNotifications({ ...notifications, [key]: e.target.checked })} className="w-5 h-5 accent-teal-600" />
                  </label>
                ))}
              </div>
            )}

            {activeTab === 'billing' && (
              <div className="space-y-5">
                <div className="p-4 rounded-xl bg-teal-50 border border-teal-100 text-teal-800">
                  Current plan: <span className="font-bold">{subscription?.plan?.name || 'Free'}</span> ({subscription?.status || 'free'})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {plans.map((plan) => (
                    <div key={plan.code} className="border border-teal-100 rounded-xl p-5 bg-white/50">
                      <h3 className="font-bold text-teal-900">{plan.name}</h3>
                      <p className="text-2xl font-bold text-teal-900 mt-3">${(plan.price_cents / 100).toFixed(0)}</p>
                      <p className="text-sm text-teal-700/60 mt-2">{plan.description}</p>
                      <ul className="mt-4 space-y-2 text-sm text-teal-700/70">
                        {plan.features?.map((feature) => <li key={feature}>{feature}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'support' && (
              <form onSubmit={submitTicket} className="space-y-4">
                <select value={support.topic} onChange={(e) => setSupport({ ...support, topic: e.target.value })} className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none">
                  <option value="general">General</option>
                  <option value="account">Account</option>
                  <option value="billing">Billing</option>
                  <option value="technical">Technical</option>
                  <option value="feature_request">Feature Request</option>
                </select>
                <input value={support.subject} onChange={(e) => setSupport({ ...support, subject: e.target.value })} required placeholder="Subject" className="w-full px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none" />
                <textarea value={support.message} onChange={(e) => setSupport({ ...support, message: e.target.value })} required placeholder="Describe the issue" className="w-full min-h-40 px-4 py-3 bg-white/50 border border-teal-100 rounded-xl outline-none" />
                <button className="px-8 py-3 bg-teal-600 text-white rounded-xl font-bold">Submit Ticket</button>
              </form>
            )}

            {activeTab === 'ai' && (
              <div className="space-y-4">
                <div className="p-4 bg-teal-50 rounded-xl border border-teal-100">
                  <h4 className="font-bold text-teal-900">AI Voice Assistant</h4>
                  <p className="text-sm text-teal-700/70 mt-1">Voice, workflow prefill, command history, replay, and AI chat are connected from the AI Workflow page.</p>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-4">
                <button onClick={() => smartflowApi.updateSettings({})} className="px-6 py-3 bg-teal-600 text-white rounded-xl font-bold">Refresh Account Session</button>
                <p className="text-sm text-teal-700/60">Password change and session revoke endpoints are available through authenticated settings APIs.</p>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
