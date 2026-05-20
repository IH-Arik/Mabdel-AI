import { useCallback, useEffect, useState } from 'react';
import { 
  FileText, Download, Plus, Search, Filter, 
  CheckCircle, Clock, AlertCircle, MoreVertical 
} from 'lucide-react';
import { smartflowApi } from '../api/services';

const Invoices = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchInvoices = useCallback(async () => {
    try {
      setLoading(true);
      const response = await smartflowApi.getInvoices();
      setInvoices(response.data.data.items || []);
    } catch (error) {
      console.error('Error fetching invoices:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const getStatusStyle = (status) => {
    switch (status?.toLowerCase()) {
      case 'paid': return 'bg-green-100 text-green-700 border-green-200';
      case 'pending': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'overdue': return 'bg-red-100 text-red-700 border-red-200';
      default: return 'bg-teal-100 text-teal-700 border-teal-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-teal-900">Invoices</h1>
          <p className="text-teal-700/70">Track your billing history and pending payments</p>
        </div>
        <button className="flex items-center justify-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-xl font-semibold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all active:scale-95">
          <Plus size={20} />
          Create Invoice
        </button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 border-l-4 border-l-green-500">
          <div className="text-teal-700/60 text-sm font-medium">Total Paid</div>
          <div className="text-2xl font-bold text-teal-900 mt-1">$12,450.00</div>
          <div className="text-xs text-green-600 mt-2 flex items-center gap-1">
            <CheckCircle size={12} /> +15% from last month
          </div>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-yellow-500">
          <div className="text-teal-700/60 text-sm font-medium">Pending</div>
          <div className="text-2xl font-bold text-teal-900 mt-1">$3,120.00</div>
          <div className="text-xs text-yellow-600 mt-2 flex items-center gap-1">
            <Clock size={12} /> 5 invoices awaiting payment
          </div>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-red-500">
          <div className="text-teal-700/60 text-sm font-medium">Overdue</div>
          <div className="text-2xl font-bold text-teal-900 mt-1">$850.00</div>
          <div className="text-xs text-red-600 mt-2 flex items-center gap-1">
            <AlertCircle size={12} /> 2 high priority items
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="glass-card p-4 flex flex-col md:flex-row gap-4 items-center">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-teal-600/50" size={20} />
          <input 
            type="text" 
            placeholder="Search by invoice # or client..." 
            className="w-full pl-10 pr-4 py-2 bg-white/50 border border-teal-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500/20 transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 border border-teal-100 rounded-lg text-teal-700 hover:bg-white/50 transition-all">
            <Filter size={18} />
            Filter
          </button>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-teal-50/50 text-teal-900 font-semibold text-sm">
                <th className="px-6 py-4">Invoice #</th>
                <th className="px-6 py-4">Client</th>
                <th className="px-6 py-4">Date</th>
                <th className="px-6 py-4">Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-teal-50">
              {loading ? (
                Array(5).fill(0).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-teal-100 rounded w-20" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-teal-100 rounded w-32" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-teal-100 rounded w-24" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-teal-100 rounded w-16" /></td>
                    <td className="px-6 py-4"><div className="h-6 bg-teal-100 rounded-full w-16" /></td>
                    <td className="px-6 py-4 text-right"><div className="h-8 bg-teal-100 rounded w-8 ml-auto" /></td>
                  </tr>
                ))
              ) : invoices.length > 0 ? (
                invoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-white/50 transition-colors group">
                    <td className="px-6 py-4 font-medium text-teal-900">{invoice.invoice_number || `#INV-${invoice.id.slice(0, 5)}`}</td>
                    <td className="px-6 py-4 text-teal-700">{invoice.client_name || 'Walking Customer'}</td>
                    <td className="px-6 py-4 text-teal-700/70 text-sm">
                      {new Date(invoice.issue_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 font-bold text-teal-900">
                      {invoice.currency} {invoice.total_amount?.toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusStyle(invoice.status)}`}>
                        {invoice.status || 'Pending'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button className="p-2 text-teal-600 hover:bg-teal-50 rounded-lg transition-colors">
                          <Download size={18} />
                        </button>
                        <button className="p-2 text-teal-400 hover:bg-teal-50 rounded-lg transition-colors">
                          <MoreVertical size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-6 py-20 text-center">
                    <div className="w-16 h-16 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-4 text-teal-200">
                      <FileText size={32} />
                    </div>
                    <h3 className="text-lg font-bold text-teal-900">No invoices yet</h3>
                    <p className="text-teal-700/60">Start by creating your first client invoice</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Invoices;
