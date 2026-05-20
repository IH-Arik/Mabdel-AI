import { useCallback, useEffect, useState } from 'react';
import { BellRing, CheckCheck, Trash2 } from 'lucide-react';
import { smartflowApi } from '../api/services';

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const response = await smartflowApi.getNotifications({ page_size: 50 });
      setNotifications(response.data.data.items || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  async function markAllRead() {
    await smartflowApi.markAllNotificationsRead();
    await fetchNotifications();
  }

  async function deleteNotification(id) {
    await smartflowApi.deleteNotification(id);
    setNotifications((items) => items.filter((item) => item.id !== id));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-teal-900">Notifications</h1>
          <p className="text-teal-700/70">Messages, calls, AI tasks, calendar reminders, and system alerts.</p>
        </div>
        <button onClick={markAllRead} className="px-5 py-3 bg-teal-700 text-white rounded-xl font-bold flex items-center gap-2">
          <CheckCheck size={18} /> Mark All Read
        </button>
      </div>
      <div className="glass-card overflow-hidden">
        {loading ? <div className="p-12 text-center text-teal-700/60">Loading...</div> : notifications.length ? notifications.map((item) => (
          <div key={item.id} className="p-5 border-b border-teal-50 flex items-start justify-between gap-4 hover:bg-white/50">
            <div className="flex gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${item.unread ? 'bg-teal-700 text-white' : 'bg-teal-50 text-teal-700'}`}>
                <BellRing size={18} />
              </div>
              <div>
                <h3 className="font-bold text-teal-900">{item.title}</h3>
                <p className="text-sm text-teal-700/60 mt-1">{item.body}</p>
                <p className="text-xs text-teal-700/40 mt-2">{item.display_time_label || new Date(item.created_at).toLocaleString()}</p>
              </div>
            </div>
            <button onClick={() => deleteNotification(item.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
              <Trash2 size={18} />
            </button>
          </div>
        )) : <div className="p-12 text-center text-teal-700/60">No notifications yet.</div>}
      </div>
    </div>
  );
}
