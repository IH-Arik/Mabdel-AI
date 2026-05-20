import { useCallback, useEffect, useMemo, useState } from 'react';
import { FileCheck2, FileText, Plus, ScrollText, Trash2, Wand2 } from 'lucide-react';
import { smartflowApi } from '../api/services';

const tabs = [
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'leases', label: 'Leases', icon: ScrollText },
  { id: 'agreements', label: 'Agreements', icon: FileCheck2 },
];

export default function Documents() {
  const [active, setActive] = useState('documents');
  const [documents, setDocuments] = useState([]);
  const [leases, setLeases] = useState([]);
  const [agreements, setAgreements] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [docs, leaseList, agreementList] = await Promise.all([
        smartflowApi.getDocuments(),
        smartflowApi.getLeases(),
        smartflowApi.getAgreements(),
      ]);
      setDocuments(docs.data.data.items || []);
      setLeases(leaseList.data.data.items || []);
      setAgreements(agreementList.data.data.items || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Documents could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const rows = useMemo(() => {
    if (active === 'leases') return leases;
    if (active === 'agreements') return agreements;
    return documents;
  }, [active, agreements, documents, leases]);

  async function createSample() {
    setError('');
    try {
      if (active === 'documents') {
        await smartflowApi.createDocument({ name: `Document ${Date.now()}`, type: 'others', file_url: 'https://example.com/document.pdf' });
      }
      if (active === 'leases') {
        await smartflowApi.createLease({
          property_address: 'Demo Property',
          landlord_name: 'Mabdel Admin',
          tenant_name: 'Demo Tenant',
          monthly_rent: 1200,
          start_date: new Date().toISOString().slice(0, 10),
          end_date: new Date(Date.now() + 31536000000).toISOString().slice(0, 10),
        });
      }
      if (active === 'agreements') {
        await smartflowApi.createAgreement({
          title: 'Demo Service Agreement',
          client_name: 'Demo Client',
          agreement_type: 'service',
          priority: 'standard',
          content: draft || 'This service agreement covers standard business services and payment terms.',
        });
      }
      setDraft('');
      await fetchAll();
    } catch (err) {
      setError(err.response?.data?.message || 'Create action failed.');
    }
  }

  async function generateDraft() {
    try {
      const text = draft || 'Create a simple service agreement for Acme Corp with standard payment terms.';
      const response = active === 'leases'
        ? await smartflowApi.generateLease({ property_address: 'Demo Property', landlord_name: 'Mabdel Admin', tenant_name: 'Demo Tenant', custom_terms: text })
        : await smartflowApi.generateAgreement({ title: 'AI Draft', client_name: 'Acme Corp', agreement_type: 'service', priority: 'standard', prompt: text });
      setDraft(JSON.stringify(response.data.data, null, 2));
    } catch (err) {
      setError(err.response?.data?.message || 'AI draft failed.');
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-teal-900">Documents</h1>
          <p className="text-teal-700/70">Manage files, leases, agreements, AI drafts, reviews, and signatures.</p>
        </div>
        <button onClick={createSample} className="px-5 py-3 bg-teal-700 text-white rounded-xl font-bold flex items-center gap-2">
          <Plus size={18} /> Create {tabs.find((tab) => tab.id === active)?.label.slice(0, -1)}
        </button>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-red-700 text-sm">{error}</div>}

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActive(tab.id)} className={`px-4 py-2 rounded-xl font-semibold flex items-center gap-2 ${active === tab.id ? 'bg-teal-700 text-white' : 'bg-white/60 text-teal-700 border border-teal-100'}`}>
              <Icon size={18} /> {tab.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[420px_minmax(0,1fr)] gap-6">
        <div className="glass-card p-5 space-y-4">
          <h2 className="font-bold text-teal-900 flex items-center gap-2"><Wand2 size={18} /> Draft Assistant</h2>
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Describe the document or paste terms to review..." className="w-full min-h-64 px-4 py-3 bg-white/60 border border-teal-100 rounded-xl outline-none font-mono text-sm" />
          <button onClick={generateDraft} disabled={active === 'documents'} className="w-full py-3 bg-teal-600 text-white rounded-xl font-bold disabled:opacity-40">
            Generate AI Draft
          </button>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-teal-100 font-bold text-teal-900">{tabs.find((tab) => tab.id === active)?.label}</div>
          {loading ? <div className="p-12 text-center text-teal-700/60">Loading...</div> : (
            <div className="divide-y divide-teal-50">
              {rows.length ? rows.map((item) => (
                <div key={item.id} className="p-5 flex items-center justify-between gap-4 hover:bg-white/50">
                  <div className="min-w-0">
                    <h3 className="font-bold text-teal-900 truncate">{item.name || item.title || item.agreement_number || item.lease_number || item.id}</h3>
                    <p className="text-sm text-teal-700/60 mt-1 truncate">{item.type || item.status_label || item.status || item.client_name || 'Document'}</p>
                  </div>
                  {active === 'documents' && (
                    <button onClick={() => smartflowApi.deleteDocument(item.id).then(fetchAll)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              )) : <div className="p-12 text-center text-teal-700/60">No records yet.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
