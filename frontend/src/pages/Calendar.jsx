import { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Clock, MapPin, Plus, Trash2 } from 'lucide-react';
import { smartflowApi } from '../api/services';

const initialForm = {
  title: '',
  description: '',
  starts_at: '',
  ends_at: '',
  meeting_mode: 'online',
  meeting_link: '',
  location: '',
};

export default function Calendar() {
  const [events, setEvents] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      const response = await smartflowApi.getCalendarEvents({ page_size: 50 });
      setEvents(response.data.data.items || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Calendar events could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const updateForm = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  async function createEvent(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await smartflowApi.createCalendarEvent({
        ...form,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setForm(initialForm);
      await fetchEvents();
    } catch (err) {
      setError(err.response?.data?.message || 'Event creation failed.');
    } finally {
      setSaving(false);
    }
  }

  async function deleteEvent(id) {
    await smartflowApi.deleteCalendarEvent(id);
    setEvents((items) => items.filter((item) => item.id !== id));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-teal-900">Calendar</h1>
          <p className="text-teal-700/70">Schedule meetings and keep customer follow-ups in one place.</p>
        </div>
        <div className="glass-card px-5 py-3">
          <span className="text-sm text-teal-700/60">Total Events</span>
          <p className="text-2xl font-bold text-teal-900">{events.length}</p>
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-red-700 text-sm">{error}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-6">
        <form onSubmit={createEvent} className="glass-card p-5 space-y-4">
          <h2 className="font-bold text-teal-900 flex items-center gap-2"><Plus size={18} /> New Event</h2>
          <input value={form.title} onChange={(e) => updateForm('title', e.target.value)} required placeholder="Meeting title" className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none" />
          <textarea value={form.description} onChange={(e) => updateForm('description', e.target.value)} placeholder="Notes" className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none min-h-24" />
          <div className="grid grid-cols-1 gap-3">
            <label className="text-xs font-bold text-teal-700">Starts</label>
            <input type="datetime-local" value={form.starts_at} onChange={(e) => updateForm('starts_at', e.target.value)} required className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none" />
            <label className="text-xs font-bold text-teal-700">Ends</label>
            <input type="datetime-local" value={form.ends_at} onChange={(e) => updateForm('ends_at', e.target.value)} required className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none" />
          </div>
          <select value={form.meeting_mode} onChange={(e) => updateForm('meeting_mode', e.target.value)} className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none">
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>
          <input value={form.meeting_link} onChange={(e) => updateForm('meeting_link', e.target.value)} placeholder="Meeting link" className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none" />
          <input value={form.location} onChange={(e) => updateForm('location', e.target.value)} placeholder="Location" className="w-full px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none" />
          <button disabled={saving} className="w-full py-3 bg-teal-700 text-white rounded-xl font-bold disabled:opacity-60">
            {saving ? 'Saving...' : 'Create Event'}
          </button>
        </form>

        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-teal-100 flex items-center gap-2 font-bold text-teal-900">
            <CalendarDays size={20} /> Upcoming Events
          </div>
          <div className="divide-y divide-teal-50">
            {loading ? Array(5).fill(0).map((_, index) => <div key={index} className="p-5 animate-pulse h-24 bg-white/30" />) : events.length ? events.map((item) => (
              <div key={item.id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-white/50">
                <div>
                  <h3 className="font-bold text-teal-900">{item.title}</h3>
                  <p className="text-sm text-teal-700/60 mt-1">{item.description || 'No description'}</p>
                  <div className="flex flex-wrap gap-3 mt-3 text-xs text-teal-700/70">
                    <span className="flex items-center gap-1"><Clock size={14} /> {new Date(item.starts_at).toLocaleString()}</span>
                    <span className="flex items-center gap-1"><MapPin size={14} /> {item.meeting_link || item.location || item.meeting_mode}</span>
                  </div>
                </div>
                <button onClick={() => deleteEvent(item.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg self-start md:self-auto">
                  <Trash2 size={18} />
                </button>
              </div>
            )) : (
              <div className="p-12 text-center text-teal-700/60">No events scheduled.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
