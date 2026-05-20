import { useCallback, useEffect, useState } from 'react';
import { smartflowApi } from '../api/services';
import { 
  Users, 
  MessageSquare, 
  FileText, 
  ArrowUpRight, 
  ArrowDownRight,
  Clock,
  Wand2
} from 'lucide-react';
import { motion } from 'framer-motion';

const StatCard = ({ title, value, icon: Icon, trend, trendType }) => (
  <motion.div 
    whileHover={{ y: -5 }}
    className="m-card flex flex-col gap-4"
  >
    <div className="flex justify-between items-start">
      <div className="p-3 bg-teal-50 text-teal-700 rounded-xl">
        <Icon size={24} />
      </div>
      <div className={`flex items-center gap-1 text-sm font-bold ${trendType === 'up' ? 'text-green-600' : 'text-red-600'}`}>
        {trend}
        {trendType === 'up' ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
      </div>
    </div>
    <div>
      <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</p>
      <h3 className="text-3xl font-extrabold text-gray-800 mt-1">
        {typeof value === 'number' && title.includes('Invoices') ? `$${value.toLocaleString()}` : value.toLocaleString()}
      </h3>
    </div>
  </motion.div>
);

export default function Dashboard() {
  const [stats, setStats] = useState({
    contacts: 0,
    unread: 0,
    invoices: 0,
    calls: 0
  });

  const fetchStats = useCallback(async () => {
    try {
      const response = await smartflowApi.getHome();
      const home = response.data.data || {};
      setStats({
        contacts: home.contacts?.count || 0,
        unread: home.inbox?.unread_count || 0,
        invoices: home.documents?.counts_by_type?.invoice || 0,
        calls: home.ai_call_analytics?.total_calls || 0
      });
    } catch (error) {
      console.error(error);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-extrabold text-gray-800">Hello, Administrator</h1>
          <p className="text-gray-500 mt-1">Here's what's happening with Mabdel AI today.</p>
        </div>
        <div className="flex gap-4">
          <button className="px-6 py-3 glass rounded-xl font-bold text-teal-800 hover:bg-teal-50 transition-all">
            Export Report
          </button>
          <button className="px-6 py-3 bg-teal-700 text-white rounded-xl font-bold hover:bg-teal-800 transition-all shadow-lg shadow-teal-700/20">
            View Analytics
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Contacts" value={stats.contacts} icon={Users} trend="+12.5%" trendType="up" />
        <StatCard title="Unread Messages" value={stats.unread} icon={MessageSquare} trend="-2%" trendType="down" />
        <StatCard title="Pending Invoices" value={stats.invoices} icon={FileText} trend="+8.1%" trendType="up" />
        <StatCard title="Total Calls" value={stats.calls} icon={Clock} trend="+14.2%" trendType="up" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Activity Feed */}
        <div className="lg:col-span-2 glass rounded-3xl p-8 border-gray-200/50">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-xl font-bold text-gray-800">Platform Performance</h3>
            <select className="bg-transparent border-none text-sm font-bold text-teal-700 outline-none cursor-pointer">
              <option>Last 7 Days</option>
              <option>Last 30 Days</option>
            </select>
          </div>
          
          <div className="h-64 flex items-end justify-between gap-4 px-4">
            {[45, 78, 56, 89, 67, 95, 82].map((height, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-3 group">
                <div className="w-full relative">
                  <motion.div 
                    initial={{ height: 0 }}
                    animate={{ height: `${height}%` }}
                    transition={{ delay: i * 0.1, duration: 1, ease: "easeOut" }}
                    className="w-full bg-teal-700/10 group-hover:bg-teal-700/20 rounded-t-lg transition-all"
                  />
                  <motion.div 
                    initial={{ height: 0 }}
                    animate={{ height: `${height * 0.6}%` }}
                    transition={{ delay: i * 0.1 + 0.2, duration: 1, ease: "easeOut" }}
                    className="absolute bottom-0 w-full bg-teal-700 rounded-t-lg shadow-lg shadow-teal-700/30"
                  />
                </div>
                <span className="text-[10px] font-bold text-gray-400">Day {i + 1}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="glass rounded-3xl p-8 border-gray-200/50 flex flex-col gap-6">
          <h3 className="text-xl font-bold text-gray-800">Quick Actions</h3>
          <button className="flex items-center gap-4 p-4 rounded-2xl bg-teal-700 text-white font-bold hover:bg-teal-800 transition-all group">
            <div className="p-2 bg-white/20 rounded-lg group-hover:scale-110 transition-transform">
              <Wand2 size={20} />
            </div>
            Start AI Workflow
          </button>
          <button className="flex items-center gap-4 p-4 rounded-2xl bg-white text-gray-800 border border-gray-100 font-bold hover:bg-gray-50 transition-all group shadow-sm">
            <div className="p-2 bg-teal-50 text-teal-700 rounded-lg group-hover:scale-110 transition-transform">
              <Users size={20} />
            </div>
            Add New Contact
          </button>
          <button className="flex items-center gap-4 p-4 rounded-2xl bg-white text-gray-800 border border-gray-100 font-bold hover:bg-gray-50 transition-all group shadow-sm">
            <div className="p-2 bg-teal-50 text-teal-700 rounded-lg group-hover:scale-110 transition-transform">
              <FileText size={20} />
            </div>
            Create Invoice
          </button>
        </div>
      </div>
    </div>
  );
}
