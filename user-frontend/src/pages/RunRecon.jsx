import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Play, Download, Table2, List, Loader2 } from 'lucide-react';
import { apiCall } from '../api';

export default function RunRecon() {
  const [running, setRunning] = useState(false);
  const [showSummary, setShowSummary] = useState(true);
  const [results, setResults] = useState(null);
  const [filters, setFilters] = useState({
    validationType: 'All',
    period: '',
    orderId: '',
    matchPercentage: '100'
  });

  const handleRunRecon = async () => {
    if (running) return;
    setRunning(true);
    setResults(null);
    
    // Premium sequential notification flow
    toast.promise(
      new Promise(async (resolve, reject) => {
        try {
          // Simulate step 1
          toast.loading('Validation 1 (GRN vs Vendor) is running...', { id: 'v1' });
          await new Promise(r => setTimeout(r, 1500));
          toast.success('Validation 1 Complete', { id: 'v1' });

          // Simulate step 2
          toast.loading('Validation 2 (Vendor vs Tally) is running...', { id: 'v2' });
          await new Promise(r => setTimeout(r, 1500));
          toast.success('Validation 2 Complete', { id: 'v2' });

          // Simulate step 3
          toast.loading('Validation 3 (Tally vs Vendor) is running...', { id: 'v3' });
          await new Promise(r => setTimeout(r, 1500));
          toast.success('Validation 3 Complete', { id: 'v3' });

          // In real implementation, this would be a single API call that streams or returns all results
          // const data = await apiCall('/recon/run', { method: 'POST', body: JSON.stringify(filters) });
          resolve({ success: true, dummy: true });
        } catch (e) {
          reject(e);
        }
      }),
      {
        loading: 'Executing Reconciliation Pipeline...',
        success: (data) => {
          setResults({ 
            v1: [{ id: 1, remark: 'Matched 100%' }],
            v2: [{ id: 2, remark: 'Matched 100%' }],
            v3: [{ id: 3, remark: 'Matched 100%' }]
          });
          setRunning(false);
          return 'All validations completed successfully!';
        },
        error: (err) => {
          setRunning(false);
          return `Reconciliation failed: ${err.message}`;
        }
      }
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 relative">
      {/* Header & Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">Run Recon</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Execute 3-way reconciliation pipeline</p>
        </div>
        
        <div className="glass-card rounded-2xl p-2 flex flex-wrap gap-2 items-center shadow-sm">
          <select 
            className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300"
            value={filters.validationType}
            onChange={e => setFilters({...filters, validationType: e.target.value})}
          >
            <option value="All">All Validations</option>
            <option value="V1">Validation 1 (GRN vs Vendor)</option>
            <option value="V2">Validation 2 (Vendor vs Tally)</option>
            <option value="V3">Validation 3 (Tally vs Vendor)</option>
          </select>
          
          <select className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300">
            <option value="">Period (All)</option>
            {/* Dynamic periods will go here */}
          </select>

          <input 
            type="text" 
            placeholder="Order ID..." 
            className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 w-32 text-gray-700 dark:text-gray-300"
          />

          <select className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300">
            <option value="100">Match 100%</option>
            <option value="90">Match &gt; 90%</option>
            <option value="any">Any Match</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {[
          { title: 'GRN Amount', amount: '₹0.00', count: 0, color: 'from-green-500 to-emerald-700' },
          { title: 'Vendor Invoice Amount', amount: '₹0.00', count: 0, color: 'from-blue-500 to-indigo-700' },
          { title: 'Tally Amount', amount: '₹0.00', count: 0, color: 'from-purple-500 to-fuchsia-700' }
        ].map((card, i) => (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            key={card.title} 
            className="glass-card rounded-2xl p-6 relative overflow-hidden group"
          >
            <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${card.color} opacity-10 rounded-bl-full transition-transform group-hover:scale-110`} />
            <h3 className="text-gray-500 dark:text-gray-400 font-medium mb-2">{card.title}</h3>
            <div className="text-4xl font-bold text-gray-900 dark:text-white mb-1">{card.amount}</div>
            <div className="text-sm text-gray-400">{card.count} Orders Matched</div>
          </motion.div>
        ))}
      </div>

      {/* Execute Action */}
      <div className="flex justify-center mb-12">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleRunRecon}
          disabled={running}
          className={`flex items-center space-x-2 px-8 py-4 rounded-full font-bold text-white shadow-lg transition-all ${
            running ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-blue-500/25'
          }`}
        >
          {running ? (
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, ease: 'linear', duration: 1 }}>
              <Loader2 className="w-5 h-5" />
            </motion.div>
          ) : (
            <Play className="w-5 h-5" fill="currentColor" />
          )}
          <span>{running ? 'Processing Pipeline...' : 'Run Validation'}</span>
        </motion.button>
      </div>

      {/* Results View */}
      <AnimatePresence>
        {results && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card rounded-2xl p-6 mb-8"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Reconciliation Results</h3>
              <div className="flex space-x-3">
                <button 
                  onClick={() => setShowSummary(!showSummary)}
                  className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                >
                  {showSummary ? <List size={16} /> : <Table2 size={16} />}
                  <span>{showSummary ? 'Show Detailed' : 'Show Summary'}</span>
                </button>
                <button className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors">
                  <Download size={16} />
                  <span>Export</span>
                </button>
              </div>
            </div>

            <div className="text-center py-12 text-gray-500 dark:text-gray-400 border-2 border-dashed border-gray-200 dark:border-zinc-800 rounded-xl">
              [Data Tables Will Render Here based on backend response]
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
