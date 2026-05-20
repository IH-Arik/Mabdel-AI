import client from './client';

export const smartflowApi = {
  getHome: () => client.get('/api/v1/smartflow/home'),
  
  // Contacts
  getContacts: () => client.get('/api/v1/smartflow/contacts'),
  getContact: (id) => client.get(`/api/v1/smartflow/contacts/${id}`),
  createContact: (data) => client.post('/api/v1/smartflow/contacts', data),
  updateContact: (id, data) => client.patch(`/api/v1/smartflow/contacts/${id}`, data),
  deleteContact: (id) => client.delete(`/api/v1/smartflow/contacts/${id}`),
  uploadContactAvatar: (id, formData) => client.post(`/api/v1/smartflow/contacts/${id}/avatar`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),

  // Conversations
  getConversations: () => client.get('/api/v1/smartflow/conversations'),
  getMessages: (id) => client.get(`/api/v1/smartflow/conversations/${id}/messages`),
  sendMessage: (data) => client.post('/api/v1/smartflow/messages', data),
  markRead: (id) => client.post(`/api/v1/smartflow/conversations/${id}/mark-read`),
  archiveConversation: (id) => client.patch(`/api/v1/smartflow/conversations/${id}/archive`),
  getTypingStatus: (id) => client.get(`/api/v1/smartflow/conversations/${id}/typing`),
  setTypingStatus: (id, typing) => client.post(`/api/v1/smartflow/conversations/${id}/typing`, { typing }),

  // AI & Voice
  processAI: (data) => client.post('/api/v1/smartflow/ai/workflow-prefill', {
    transcript: data.prompt || data.transcript,
    workflow_intent: data.workflow_intent,
    current_values: data.current_values || {},
  }),
  getAIWorkflowPrefill: (transcript, options = {}) => client.post('/api/v1/smartflow/ai/workflow-prefill', {
    transcript,
    workflow_intent: options.workflow_intent,
    current_values: options.current_values || {},
  }),
  aiChat: (content, options = {}) => client.post('/api/v1/smartflow/ai/chat', {
    content,
    response_mode: options.response_mode || 'text',
    voice_id: options.voice_id,
  }),
  getAIVoices: () => client.get('/api/v1/smartflow/ai/voices'),
  getAIHistory: () => client.get('/api/v1/smartflow/ai/history'),
  replayAIResponse: (id) => client.post(`/api/v1/smartflow/ai/history/${id}/replay`),
  voiceChat: (audioBlob) => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob);
    return client.post('/api/v1/smartflow/ai/voice-chat-upload', formData);
  },


  // Bulk Messaging
  validateBulkRecipients: (data) => client.post('/api/v1/smartflow/bulk-messages/recipients/validate', data),
  getBulkMessages: (params) => client.get('/api/v1/smartflow/bulk-messages', { params }),
  createBulkMessage: (data) => client.post('/api/v1/smartflow/bulk-messages', data),
  sendBulkMessage: (id) => client.post(`/api/v1/smartflow/bulk-messages/${id}/send`),
  cancelBulkMessage: (id) => client.post(`/api/v1/smartflow/bulk-messages/${id}/cancel`),

  // Documents & Leases
  getDocuments: () => client.get('/api/v1/smartflow/documents'),
  createDocument: (data) => client.post('/api/v1/smartflow/documents', data),
  deleteDocument: (id) => client.delete(`/api/v1/smartflow/documents/${id}`),
  getLeases: () => client.get('/api/v1/smartflow/leases'),
  createLease: (data) => client.post('/api/v1/smartflow/leases', data),
  generateLease: (data) => client.post('/api/v1/smartflow/leases/generate', data),
  enhanceLeaseTerms: (data) => client.post('/api/v1/smartflow/leases/enhance-terms', data),
  reviewLease: (data) => client.post('/api/v1/smartflow/leases/review', data),
  getAgreements: () => client.get('/api/v1/smartflow/agreements'),
  createAgreement: (data) => client.post('/api/v1/smartflow/agreements', data),
  generateAgreement: (data) => client.post('/api/v1/smartflow/agreements/generate', data),
  reviewAgreement: (data) => client.post('/api/v1/smartflow/agreements/review', data),

  // Calendar
  getCalendarEvents: (params) => client.get('/api/v1/smartflow/calendar/events', { params }),
  createCalendarEvent: (data) => client.post('/api/v1/smartflow/calendar/events', data),
  updateCalendarEvent: (id, data) => client.patch(`/api/v1/smartflow/calendar/events/${id}`, data),
  deleteCalendarEvent: (id) => client.delete(`/api/v1/smartflow/calendar/events/${id}`),
  
  // Calls
  getCalls: () => client.get('/api/v1/smartflow/calls'),
  createCall: (data) => client.post('/api/v1/smartflow/calls', data),
  createOutboundCall: (data) => client.post('/api/v1/smartflow/calls/outbound', data),
  getCallRecording: (id) => client.get(`/api/v1/smartflow/calls/${id}/recording`, { responseType: 'blob' }),

  // Integrations
  getIntegrations: () => client.get('/api/v1/smartflow/integrations'),
  getIntegrationCatalog: () => client.get('/api/v1/smartflow/integrations/catalog'),
  syncIntegration: (platform) => client.post(`/api/v1/smartflow/integrations/${platform}/sync`),
  disconnectIntegration: (platform) => client.delete(`/api/v1/smartflow/integrations/${platform}`),
  startIntegrationOAuth: (platform) => client.get(`/api/v1/smartflow/integrations/${platform}/oauth/start`),

  // Notifications
  getNotifications: (params) => client.get('/api/v1/smartflow/notifications', { params }),
  markAllNotificationsRead: () => client.post('/api/v1/smartflow/notifications/mark-all-read'),
  markNotificationRead: (id) => client.patch(`/api/v1/smartflow/notifications/${id}/read`),
  deleteNotification: (id) => client.delete(`/api/v1/smartflow/notifications/${id}`),

  // Invoices
  getInvoices: () => client.get('/api/v1/invoices'),
  createInvoice: (data) => client.post('/api/v1/invoices', data),
  downloadInvoice: (id) => client.get(`/api/v1/invoices/${id}/pdf`, { responseType: 'blob' }),

  // Settings
  getSettings: () => client.get('/api/v1/smartflow/settings'),
  updateSettings: (data) => client.patch('/api/v1/smartflow/settings', data),
  getNotificationSettings: () => client.get('/api/v1/smartflow/settings/notifications'),
  updateNotificationSettings: (data) => client.patch('/api/v1/smartflow/settings/notifications', data),
  getBusinessProfile: () => client.get('/api/v1/smartflow/business-profile'),
  updateBusinessProfile: (data) => client.patch('/api/v1/smartflow/business-profile', data),
  getSubscriptionPlans: () => client.get('/api/v1/smartflow/subscription/plans'),
  getCurrentSubscription: () => client.get('/api/v1/smartflow/subscription/current'),
  createSupportTicket: (data) => client.post('/api/v1/smartflow/support/tickets', data),
  getSupportSession: () => client.get('/api/v1/smartflow/support/session'),
  getSupportMessages: (params) => client.get('/api/v1/smartflow/support/messages', { params }),
  sendSupportMessage: (data) => client.post('/api/v1/smartflow/support/messages', data),
};

export const adminApi = {
  getSummary: () => client.get('/api/v1/dashboard/admin/summary'),
  getUsers: (params) => client.get('/api/v1/dashboard/admin/users', { params }),
  getUserDetails: (id) => client.get(`/api/v1/dashboard/admin/users/${id}`),
  updateUserStatus: (id, status) => client.patch(`/api/v1/dashboard/admin/users/${id}/status`, null, { params: { status } }),
  getUsersGrowth: () => client.get('/api/v1/dashboard/admin/users-growth'),
  getEarnings: () => client.get('/api/v1/dashboard/admin/earnings'),
  getTransactions: (params) => client.get('/api/v1/dashboard/admin/earnings/transactions', { params }),
  getAIStats: () => client.get('/api/v1/dashboard/admin/ai/stats'),
  getAILogs: (limit = 50) => client.get('/api/v1/dashboard/admin/ai/logs', { params: { limit } }),
  getReports: (params) => client.get('/api/v1/dashboard/admin/reports', { params }),
  getAdmins: () => client.get('/api/v1/dashboard/admin/admins'),
  getSubscriptions: () => client.get('/api/v1/dashboard/admin/subscriptions'),
  getChats: () => client.get('/api/v1/dashboard/admin/chats'),
};
