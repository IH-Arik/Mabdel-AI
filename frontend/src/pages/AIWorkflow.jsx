import { useState } from 'react';
import { smartflowApi } from '../api/services';
import { Sparkles, Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function AIWorkflow() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleProcess = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    try {
      const data = await smartflowApi.processAI({ prompt });
      setResult(data);
      setLoading(false);
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-teal-100 text-teal-700 font-bold text-sm">
          <Sparkles size={16} />
          Mabdel Intelligence
        </div>
        <h1 className="text-4xl font-extrabold text-gray-800">What can I help you with today?</h1>
        <p className="text-gray-500">Generate invoices, schedule meetings, or create documents just by asking.</p>
      </div>

      <div className="glass p-2 rounded-3xl shadow-2xl bg-white/40 border-teal-100">
        <form onSubmit={handleProcess} className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Generate an invoice for Sarah Jenkins for $500 for web design services..."
            className="w-full h-40 p-6 rounded-2xl bg-white/80 border-none focus:ring-0 text-lg outline-none resize-none placeholder:text-gray-300"
          />
          <div className="absolute bottom-4 right-4 flex items-center gap-4">
            <span className="text-xs text-gray-400">Shift + Enter to submit</span>
            <button 
              disabled={loading}
              className="bg-teal-700 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:bg-teal-800 transition-all disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <Send size={18} />
                  Run Workflow
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-8 rounded-3xl border-teal-500/30 bg-teal-50/50"
        >
          <div className="flex items-start gap-4">
            <div className="p-3 bg-teal-600 text-white rounded-2xl shadow-lg shadow-teal-700/20">
              <CheckCircle2 size={24} />
            </div>
            <div className="flex-1 space-y-6">
              <div>
                <h3 className="text-xl font-bold text-teal-900">AI Successfully Prepared Workflow</h3>
                <p className="text-teal-700/70 text-sm mt-1">Intent detected: <span className="font-bold uppercase">{result.workflow?.intent}</span></p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(result.prefill || {}).map(([key, value]) => (
                  <div key={key} className="bg-white/60 p-4 rounded-xl border border-teal-100">
                    <p className="text-[10px] text-teal-600 font-bold uppercase tracking-wider">{key.replace(/_/g, ' ')}</p>
                    <p className="text-gray-800 font-medium mt-1 truncate">{JSON.stringify(value)}</p>
                  </div>
                ))}
              </div>

              {result.missing_fields?.length > 0 && (
                <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-100 flex items-center gap-3 text-yellow-700">
                  <AlertCircle size={20} />
                  <p className="text-sm font-medium">Missing fields: {result.missing_fields.join(', ')}</p>
                </div>
              )}

              <button className="w-full py-4 bg-teal-700 text-white rounded-xl font-bold hover:bg-teal-800 transition-all shadow-lg shadow-teal-700/20">
                Confirm and Execute {result.workflow?.intent}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 opacity-60">
        <div className="p-6 rounded-2xl border border-dashed border-gray-300 hover:border-teal-500 hover:bg-teal-50 transition-all cursor-pointer group">
          <h4 className="font-bold text-gray-700 group-hover:text-teal-700">Invoice Generation</h4>
          <p className="text-xs text-gray-500 mt-2">"Create a bill for Acme Corp for consulting."</p>
        </div>
        <div className="p-6 rounded-2xl border border-dashed border-gray-300 hover:border-teal-500 hover:bg-teal-50 transition-all cursor-pointer group">
          <h4 className="font-bold text-gray-700 group-hover:text-teal-700">Meeting Booking</h4>
          <p className="text-xs text-gray-500 mt-2">"Schedule a Zoom with John for tomorrow at 2pm."</p>
        </div>
        <div className="p-6 rounded-2xl border border-dashed border-gray-300 hover:border-teal-500 hover:bg-teal-50 transition-all cursor-pointer group">
          <h4 className="font-bold text-gray-700 group-hover:text-teal-700">Contract Drafting</h4>
          <p className="text-xs text-gray-500 mt-2">"Write a lease agreement for a 2-bedroom apt."</p>
        </div>
      </div>
    </div>
  );
}
