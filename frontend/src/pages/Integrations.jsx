import { useCallback, useEffect, useState } from 'react';
import { Link2, RefreshCw, ShieldCheck, Unplug } from 'lucide-react';
import { smartflowApi } from '../api/services';

export default function Integrations() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchIntegrations = useCallback(async () => {
    try {
      setLoading(true);
      const response = await smartflowApi.getIntegrationCatalog();
      setItems(response.data.data || response.data.data?.items || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Integrations could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  async function startOAuth(platform) {
    try {
      const response = await smartflowApi.startIntegrationOAuth(platform);
      const url = response.data.data?.auth_url;
      if (url) window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      setError(err.response?.data?.message || 'OAuth is not configured for this provider.');
    }
  }

  async function sync(platform) {
    try {
      await smartflowApi.syncIntegration(platform);
      await fetchIntegrations();
    } catch (err) {
      setError(err.response?.data?.message || 'Sync failed.');
    }
  }

  async function disconnect(platform) {
    await smartflowApi.disconnectIntegration(platform);
    await fetchIntegrations();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-teal-900">Integrations</h1>
        <p className="text-teal-700/70">Connect social, messaging, calendar, and business channels.</p>
      </div>
      {error && <div className="p-3 bg-yellow-50 border border-yellow-100 rounded-lg text-yellow-800 text-sm">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {loading ? Array(6).fill(0).map((_, i) => <div key={i} className="glass-card h-44 animate-pulse" />) : items.map((item) => (
          <div key={item.platform} className="glass-card p-5 flex flex-col gap-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-bold text-teal-900">{item.platform_label || item.platform}</h3>
                <p className="text-sm text-teal-700/60 mt-1">{item.description || 'Provider integration'}</p>
              </div>
              <span className={`px-2 py-1 text-xs rounded-full font-bold ${item.connected ? 'bg-green-100 text-green-700' : 'bg-teal-100 text-teal-700'}`}>
                {item.status || (item.connected ? 'connected' : 'disconnected')}
              </span>
            </div>
            <div className="mt-auto flex gap-2">
              <button onClick={() => startOAuth(item.platform)} className="flex-1 px-3 py-2 bg-teal-700 text-white rounded-lg font-semibold flex items-center justify-center gap-2">
                <Link2 size={16} /> Connect
              </button>
              <button onClick={() => sync(item.platform)} className="px-3 py-2 border border-teal-100 text-teal-700 rounded-lg">
                <RefreshCw size={16} />
              </button>
              {item.connected && (
                <button onClick={() => disconnect(item.platform)} className="px-3 py-2 border border-red-100 text-red-600 rounded-lg">
                  <Unplug size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="glass-card p-4 text-sm text-teal-700 flex gap-2">
        <ShieldCheck size={18} /> OAuth providers require credentials in `.env`; configured providers open their authorization flow.
      </div>
    </div>
  );
}
