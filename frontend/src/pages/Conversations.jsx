import { useCallback, useEffect, useState } from 'react';
import { smartflowApi } from '../api/services';
import { Search, Send, MoreVertical, Phone, Video, Info, MessageSquare } from 'lucide-react';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [, setLoading] = useState(true);

  const fetchConversations = useCallback(async () => {
    try {
      const response = await smartflowApi.getConversations();
      setConversations(response.data.data.items || []);
      setLoading(false);
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  }, []);

  const fetchMessages = useCallback(async (id) => {
    try {
      const response = await smartflowApi.getMessages(id);
      setMessages(response.data.data.items || []);
    } catch (error) {
      console.error(error);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    if (selectedId) {
      fetchMessages(selectedId);
    }
  }, [fetchMessages, selectedId]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedId) return;

    try {
      await smartflowApi.sendMessage({
        conversation_id: selectedId,
        content: newMessage,
        platform: selectedConv?.platform || 'whatsapp',
        direction: 'outbound'
      });
      setNewMessage('');
      fetchMessages(selectedId);
    } catch (error) {
      console.error(error);
    }
  };

  const selectedConv = conversations.find(c => c.id === selectedId);

  return (
    <div className="flex h-[calc(100vh-12rem)] glass rounded-2xl overflow-hidden shadow-xl border-gray-200/50">
      {/* Sidebar List */}
      <div className="w-80 border-r border-gray-200/50 flex flex-col bg-white/50">
        <div className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input 
              type="text" 
              placeholder="Search chats..." 
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-gray-100 border-none focus:ring-2 focus:ring-teal-500 transition-all text-sm"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setSelectedId(conv.id)}
              className={`w-full p-4 flex gap-3 hover:bg-teal-50 transition-colors border-b border-gray-100 last:border-none ${selectedId === conv.id ? 'bg-teal-50 border-l-4 border-l-teal-700' : ''}`}
            >
              <div className="w-12 h-12 rounded-full bg-teal-100 flex-shrink-0 flex items-center justify-center text-teal-700 font-bold uppercase">
                {conv.contact_name?.[0] || 'C'}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="flex justify-between items-baseline">
                  <h4 className="font-semibold text-gray-800 truncate">{conv.contact_name || 'Anonymous'}</h4>
                  <span className="text-[10px] text-gray-400">{conv.last_message_time ? format(new Date(conv.last_message_time), 'HH:mm') : ''}</span>
                </div>
                <p className="text-xs text-gray-500 truncate">{conv.last_message_preview || 'No messages'}</p>
              </div>
              {conv.unread_count > 0 && (
                <div className="w-5 h-5 bg-teal-600 rounded-full flex items-center justify-center text-[10px] text-white font-bold">
                  {conv.unread_count}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white/30 backdrop-blur-sm">
        {selectedId ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200/50 flex items-center justify-between bg-white/80">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-teal-700 text-white flex items-center justify-center font-bold">
                  {selectedConv?.contact_name?.[0]}
                </div>
                <div>
                  <h3 className="font-bold text-gray-800">{selectedConv?.contact_name}</h3>
                  <p className="text-[10px] text-teal-600 font-medium uppercase tracking-wider">{selectedConv?.platform}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-gray-400">
                <Phone size={20} className="cursor-pointer hover:text-teal-600" />
                <Video size={20} className="cursor-pointer hover:text-teal-600" />
                <Info size={20} className="cursor-pointer hover:text-teal-600" />
                <MoreVertical size={20} className="cursor-pointer hover:text-teal-600" />
              </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-opacity-5">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[70%] p-3 rounded-2xl shadow-sm ${
                      msg.direction === 'outbound' 
                        ? 'bg-teal-700 text-white rounded-tr-none' 
                        : 'bg-white text-gray-800 rounded-tl-none border border-gray-100'
                    }`}>
                      <p className="text-sm">{msg.content}</p>
                      <p className={`text-[9px] mt-1 text-right ${msg.direction === 'outbound' ? 'text-teal-100' : 'text-gray-400'}`}>
                        {msg.timestamp ? format(new Date(msg.timestamp), 'HH:mm') : ''}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Input Area */}
            <form onSubmit={handleSendMessage} className="p-4 bg-white/80 border-t border-gray-200/50 flex gap-3">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type a message..."
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-teal-500 outline-none transition-all"
              />
              <button 
                type="submit"
                className="bg-teal-700 text-white p-3 rounded-xl hover:bg-teal-800 transition-all shadow-lg shadow-teal-700/20"
              >
                <Send size={20} />
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 opacity-50">
            <MessageSquare size={80} strokeWidth={1} />
            <p className="mt-4 text-lg">Select a conversation to start chatting</p>
          </div>
        )}
      </div>
    </div>
  );
}
