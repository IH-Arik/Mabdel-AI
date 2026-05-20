import { useCallback, useEffect, useState } from 'react';
import { smartflowApi } from '../api/services';
import { Phone, PhoneIncoming, PhoneOutgoing, Play, Download, Clock, Calendar } from 'lucide-react';
import { format } from 'date-fns';

export default function Calls() {
  const [calls, setCalls] = useState([]);
  const [, setLoading] = useState(true);

  const fetchCalls = useCallback(async () => {
    try {
      const response = await smartflowApi.getCalls();
      setCalls(response.data.data.items || []);
      setLoading(false);
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCalls();
  }, [fetchCalls]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">Phone Agent Logs</h1>
        <div className="flex gap-3">
          <div className="glass px-4 py-2 rounded-lg text-sm font-medium text-teal-700">
            Total Calls: {calls.length}
          </div>
        </div>
      </div>

      <div className="glass rounded-2xl overflow-hidden border-gray-200/50">
        <table className="w-full text-left">
          <thead className="bg-teal-700 text-white">
            <tr>
              <th className="p-4 font-semibold">Direction</th>
              <th className="p-4 font-semibold">Contact</th>
              <th className="p-4 font-semibold">Duration</th>
              <th className="p-4 font-semibold">Time</th>
              <th className="p-4 font-semibold">Status</th>
              <th className="p-4 font-semibold text-center">Recording</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.length > 0 ? calls.map((call) => (
              <tr key={call.id} className="hover:bg-teal-50/50 transition-colors bg-white/50">
                <td className="p-4">
                  {['incoming', 'incoming_automated'].includes(call.call_type) ? (
                    <div className="flex items-center gap-2 text-blue-600">
                      <PhoneIncoming size={16} />
                      <span className="text-xs font-bold uppercase">Inbound</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-teal-600">
                      <PhoneOutgoing size={16} />
                      <span className="text-xs font-bold uppercase">Outbound</span>
                    </div>
                  )}
                </td>
                <td className="p-4">
                  <p className="font-semibold text-gray-800">{call.contact_name || 'Unknown'}</p>
                  <p className="text-xs text-gray-500">{call.phone_number}</p>
                </td>
                <td className="p-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    {Math.floor(call.duration / 60)}m {call.duration % 60}s
                  </div>
                </td>
                <td className="p-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Calendar size={14} />
                    {format(new Date(call.timestamp), 'MMM dd, HH:mm')}
                  </div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                    call.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {call.status}
                  </span>
                </td>
                <td className="p-4">
                  {call.recording_url ? (
                    <div className="flex justify-center gap-2">
                      <button className="p-2 bg-teal-100 text-teal-700 rounded-full hover:bg-teal-700 hover:text-white transition-all">
                        <Play size={16} fill="currentColor" />
                      </button>
                      <button className="p-2 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-700 hover:text-white transition-all">
                        <Download size={16} />
                      </button>
                    </div>
                  ) : (
                    <p className="text-center text-xs text-gray-400 italic">No recording</p>
                  )}
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="6" className="p-12 text-center text-gray-400">
                  <Phone size={48} className="mx-auto mb-4 opacity-20" />
                  No call logs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
