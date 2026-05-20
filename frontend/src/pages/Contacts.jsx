import { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, MoreVertical, Mail, Phone, User, 
  Trash2, Filter, Download, UserPlus 
} from 'lucide-react';
import { smartflowApi } from '../api/services';

const Contacts = () => {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchContacts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await smartflowApi.getContacts();
      setContacts(response.data.data.items || []);
    } catch (error) {
      console.error('Error fetching contacts:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const filteredContacts = contacts.filter(contact => 
    contact.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contact.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contact.phone?.includes(searchTerm)
  );

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this contact?')) {
      try {
        await smartflowApi.deleteContact(id);
        setContacts(contacts.filter(c => c.id !== id));
      } catch (error) {
        console.error('Error deleting contact:', error);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-teal-900">Contacts</h1>
          <p className="text-teal-700/70">Manage your customer relationships and leads</p>
        </div>
        <button 
          onClick={fetchContacts}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-xl font-semibold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all active:scale-95"
        >
          <UserPlus size={20} />
          Add Contact
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-card p-4 flex flex-col md:flex-row gap-4 items-center">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-teal-600/50" size={20} />
          <input 
            type="text" 
            placeholder="Search contacts by name, email or phone..." 
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
          <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 border border-teal-100 rounded-lg text-teal-700 hover:bg-white/50 transition-all">
            <Download size={18} />
            Export
          </button>
        </div>
      </div>

      {/* Contacts List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AnimatePresence mode="popLayout">
          {loading ? (
            Array(6).fill(0).map((_, i) => (
              <div key={i} className="glass-card p-6 animate-pulse space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-teal-100 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-teal-100 rounded w-3/4" />
                    <div className="h-3 bg-teal-100 rounded w-1/2" />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="h-3 bg-teal-100 rounded w-full" />
                  <div className="h-3 bg-teal-100 rounded w-full" />
                </div>
              </div>
            ))
          ) : filteredContacts.length > 0 ? (
            filteredContacts.map((contact) => (
              <motion.div
                key={contact.id || contact._id}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="glass-card p-6 group hover:border-teal-400 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-teal-100 rounded-full flex items-center justify-center text-teal-700 font-bold text-xl uppercase">
                      {contact.avatar_url ? (
                        <img src={contact.avatar_url} alt={contact.name} className="w-full h-full rounded-full object-cover" />
                      ) : (
                        contact.initials || contact.name?.charAt(0) || <User size={24} />
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-teal-900">{contact.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        contact.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-teal-100 text-teal-700'
                      }`}>
                        {contact.status || 'Lead'}
                      </span>
                    </div>
                  </div>
                  <div className="relative group/menu">
                    <button className="p-1 hover:bg-teal-50 rounded-lg transition-colors text-teal-400 group-hover/menu:text-teal-600">
                      <MoreVertical size={20} />
                    </button>
                    {/* Dropdown would go here */}
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  <div className="flex items-center gap-3 text-teal-700/70 text-sm">
                    <Mail size={16} className="text-teal-500" />
                    {contact.email || 'No email provided'}
                  </div>
                  <div className="flex items-center gap-3 text-teal-700/70 text-sm">
                    <Phone size={16} className="text-teal-500" />
                    {contact.phone || 'No phone provided'}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-teal-50 flex items-center justify-between">
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleDelete(contact.id || contact._id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete Contact"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                  <button className="text-sm font-semibold text-teal-600 hover:underline">
                    View Activity
                  </button>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="col-span-full py-20 text-center">
              <div className="w-20 h-20 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-4 text-teal-200">
                <Search size={40} />
              </div>
              <h3 className="text-xl font-bold text-teal-900">No contacts found</h3>
              <p className="text-teal-700/60">Try adjusting your search or add a new contact</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Contacts;
