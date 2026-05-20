import { Fragment, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, CheckCircle,
  MessageSquare, Upload, Loader2, Play 
} from 'lucide-react';
import { smartflowApi } from '../api/services';

const BulkMessaging = () => {
  const [step, setStep] = useState(1);
  const [message, setMessage] = useState('');
  const [recipients, setRecipients] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [sending, setSending] = useState(false);

  const handleValidate = async () => {
    try {
      setIsValidating(true);
      const recipientList = recipients.split('\n').filter(r => r.trim());
      const response = await smartflowApi.validateBulkRecipients({
        channel: 'email',
        recipient_emails: recipientList,
      });
      setValidationResult(response.data.data);
      setStep(2);
    } catch (error) {
      console.error('Validation failed:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const handleSend = async () => {
    try {
      setSending(true);
      const recipientList = recipients.split('\n').filter(r => r.trim());
      const response = await smartflowApi.createBulkMessage({
        channel: 'email',
        recipient_emails: recipientList,
        subject: 'Mabdel AI Broadcast',
        content: message,
        send_now: true,
      });
      if (response.data.data?.status === 'draft') {
        await smartflowApi.sendBulkMessage(response.data.data.id);
      }
      setStep(3);
    } catch (error) {
      console.error('Send failed:', error);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-teal-900">Bulk Messaging</h1>
        <p className="text-teal-700/60">Broadcast messages to multiple recipients simultaneously</p>
      </div>

      <div className="flex items-center justify-center gap-4 mb-8">
        {[1, 2, 3].map((s) => (
          <Fragment key={s}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
              step >= s ? 'bg-teal-600 text-white shadow-lg' : 'bg-teal-100 text-teal-400'
            }`}>
              {s === 3 && step === 3 ? <CheckCircle size={20} /> : s}
            </div>
            {s < 3 && <div className={`w-12 h-1 ${step > s ? 'bg-teal-600' : 'bg-teal-100'}`} />}
          </Fragment>
        ))}
      </div>

      <div className="glass-card p-8">
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <div className="space-y-2">
                <label className="text-sm font-semibold text-teal-900 flex items-center gap-2">
                  <Users size={16} />
                  Recipients
                </label>
                <textarea 
                  placeholder="Enter phone numbers or email addresses (one per line)..."
                  className="w-full h-48 px-4 py-3 bg-white/50 border border-teal-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                  value={recipients}
                  onChange={(e) => setRecipients(e.target.value)}
                />
                <p className="text-xs text-teal-700/50">You can also upload a CSV file with your contact list.</p>
              </div>

              <div className="flex justify-between items-center">
                <button className="flex items-center gap-2 text-teal-600 font-semibold hover:underline">
                  <Upload size={18} />
                  Upload CSV
                </button>
                <button 
                  onClick={handleValidate}
                  disabled={!recipients.trim() || isValidating}
                  className="px-8 py-3 bg-teal-600 text-white rounded-xl font-bold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isValidating && <Loader2 className="animate-spin" size={18} />}
                  Validate Recipients
                </button>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <div className="p-4 bg-teal-50 rounded-xl border border-teal-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="text-teal-600" size={24} />
                  <div>
                    <span className="font-bold text-teal-900">{validationResult?.valid_count || recipients.split('\n').filter(r => r.trim()).length}</span>
                    <span className="text-teal-700/70 ml-1 text-sm">Valid recipients found</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-teal-900 flex items-center gap-2">
                  <MessageSquare size={16} />
                  Message Content
                </label>
                <textarea 
                  placeholder="Type your broadcast message here... Use {name} for personalization."
                  className="w-full h-48 px-4 py-3 bg-white/50 border border-teal-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
                <div className="flex justify-between text-xs text-teal-700/50">
                  <span>Variables: {'{name}, {phone}, {date}'}</span>
                  <span>{message.length} characters</span>
                </div>
              </div>

              <div className="flex gap-4">
                <button 
                  onClick={() => setStep(1)}
                  className="flex-1 px-8 py-3 border border-teal-100 text-teal-700 rounded-xl font-bold hover:bg-white/50 transition-all"
                >
                  Back
                </button>
                <button 
                  onClick={handleSend}
                  disabled={!message.trim() || sending}
                  className="flex-[2] px-8 py-3 bg-teal-600 text-white rounded-xl font-bold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all flex items-center justify-center gap-2"
                >
                  {sending ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
                  Send Broadcast Now
                </button>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-12 space-y-6"
            >
              <div className="w-24 h-24 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle size={48} />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-teal-900">Broadcast Sent Successfully!</h2>
                <p className="text-teal-700/60 max-w-md mx-auto">
                  Your message is being delivered to all recipients. You can track the delivery status in your reports.
                </p>
              </div>
              <button 
                onClick={() => {
                  setStep(1);
                  setMessage('');
                  setRecipients('');
                }}
                className="px-8 py-3 bg-teal-600 text-white rounded-xl font-bold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all"
              >
                Send Another
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default BulkMessaging;
