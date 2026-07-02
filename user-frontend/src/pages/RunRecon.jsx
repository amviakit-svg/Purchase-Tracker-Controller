import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Play, Download, Table2, List, Loader2, Search, FileSpreadsheet, Clock } from 'lucide-react';
import { apiCall } from '../api';

// Export helper (CSV fallback since xlsx is not installed)
export const exportToExcel = (data, filename) => {
  if (data.length === 0) {
    toast.info('No data to export');
    return;
  }
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => `"${String(row[h] || '').replace(/"/g, '""')}"`).join(','))
  ].join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${filename}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export default function RunRecon() {
  const [running, setRunning] = useState(false);
  const [folders, setFolders] = useState([]);
  
  const [filters, setFilters] = useState({
    period: '',
    orderId: '',
    matchPercentage: 'any'
  });

  const [extractedData, setExtractedData] = useState({
    v1: { data: null, file: null, error: null },
    v2: { data: null, file: null, error: null },
    v3: { data: null, file: null, error: null }
  });

  const [searchTerms, setSearchTerms] = useState({
    v1: '',
    v2: '',
    v3: ''
  });

  useEffect(() => {
    fetchFolders();
    loadHistoricalData();
  }, []);

  const loadHistoricalData = async () => {
     try {
       const vids = [1, 2, 3];
       for (const vid of vids) {
          try {
             const res = await apiCall(`/processed/files?validation_id=${vid}`);
             if (res.success && res.files && res.files.length > 0) {
                const latestFile = res.files[0];
                const preview = await apiCall(`/processed/${latestFile.id}/preview`);
                setExtractedData(prev => ({ 
                  ...prev, 
                  [`v${vid}`]: { data: preview, file: latestFile, error: null } 
                }));
             } else {
                setExtractedData(prev => ({ 
                  ...prev, 
                  [`v${vid}`]: { data: null, file: null, error: null, isEmpty: true } 
                }));
             }
          } catch(e) {
             console.error(`Error loading preview for V${vid}`, e);
             setExtractedData(prev => ({ 
               ...prev, 
               [`v${vid}`]: { data: null, file: null, error: 'Failed to load historical data' } 
             }));
          }
       }
     } catch(e) {
       console.error("Failed to load historical data", e);
     }
  };

  const fetchFolders = async () => {
    try {
      const data = await apiCall('/folders');
      if (data.success) {
        setFolders(data.folders || []);
        if (data.folders && data.folders.length > 0 && !filters.period) {
          setFilters(prev => ({ ...prev, period: data.folders[0].id }));
        }
      }
    } catch (e) {
      toast.error('Failed to load folders');
    }
  };

  const pollProcessStatus = async (vid) => {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await apiCall('/process/status', { skipCache: true });
          // If status is 'error', it also implies is_processing is false (or undefined)
          if (!status.is_processing || status.status === 'error') {
            clearInterval(interval);
            
            if (status.status === 'error') {
               reject(new Error(status.message || 'Processing failed internally'));
               return;
            }
            
            // Catch graceful validation failures from backend (e.g. "No Phase 1 rules configured")
            if (status.result && status.result.success === false) {
               reject(new Error(status.result.message || 'Validation failed to generate output.'));
               return;
            }

            try {
              const res = await apiCall(`/processed/files?validation_id=${vid}`, { skipCache: true });
              if (res.success) {
                resolve(res.files || []);
              } else {
                resolve([]);
              }
            } catch(e) {
              resolve([]);
            }
          }
        } catch (e) {
          clearInterval(interval);
          reject(e);
        }
      }, 2000);
    });
  };

  const runValidation = async (vid) => {
    const formData = new FormData();
    formData.append('validation_id', vid);
    formData.append('force', 'false');
    if (filters.period) {
      formData.append('selected_source_files', JSON.stringify([filters.period]));
    }
    
    const startData = await apiCall('/process', { method: 'POST', body: formData });
    if (startData.type === 'validation_warning') {
       throw new Error(`Missing columns: ${startData.missing_columns.join(', ')}`);
    }
    if (startData.success) {
      const resultFiles = await pollProcessStatus(vid);
      if (resultFiles.length > 0) {
        const preview = await apiCall(`/processed/${resultFiles[0].id}/preview`);
        return { data: preview, file: resultFiles[0] };
      }
      throw new Error(`No output files were generated for Validation ${vid}`);
    }
    throw new Error(startData.message || 'Failed to start processing');
  };

  const handleRunRecon = async () => {
    if (running || !filters.period) return;
    setRunning(true);
    setExtractedData({ 
       v1: { data: null, file: null, error: null }, 
       v2: { data: null, file: null, error: null }, 
       v3: { data: null, file: null, error: null } 
    });
    
    toast.promise(
      new Promise(async (resolve, reject) => {
        let errCount = 0;
        
        try {
          const v1 = await runValidation(1);
          setExtractedData(prev => ({ ...prev, v1: { ...v1, error: null } }));
        } catch (e) {
          errCount++;
          setExtractedData(prev => ({ ...prev, v1: { data: null, file: null, error: e.message } }));
        }

        try {
          const v2 = await runValidation(2);
          setExtractedData(prev => ({ ...prev, v2: { ...v2, error: null } }));
        } catch (e) {
          errCount++;
          setExtractedData(prev => ({ ...prev, v2: { data: null, file: null, error: e.message } }));
        }

        try {
          const v3 = await runValidation(3);
          setExtractedData(prev => ({ ...prev, v3: { ...v3, error: null } }));
        } catch (e) {
          errCount++;
          setExtractedData(prev => ({ ...prev, v3: { data: null, file: null, error: e.message } }));
        }
        
        if (errCount === 3) {
           reject(new Error("All 3 validations failed to process."));
        } else if (errCount > 0) {
           resolve(`Reconciliation finished, but ${errCount} validation(s) had errors.`);
        } else {
           resolve('Reconciliation completed successfully!');
        }
      }),
      {
        loading: 'Executing All Reconciliation Pipelines (V1, V2, V3)...',
        success: (msg) => {
          setRunning(false);
          return msg;
        },
        error: (err) => {
          setRunning(false);
          return err.message;
        }
      }
    );
  };

  const ValidationSection = ({ title, stateObj, searchKey, summaryTitle, summaryColor }) => {
    const [view, setView] = useState('preview');
    
    if (!stateObj || (!stateObj.data && !stateObj.error && !stateObj.isEmpty)) {
        return (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-md">
            <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gradient-to-r from-gray-50 to-white dark:from-zinc-900/50 dark:to-zinc-800/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center opacity-50">
                <Table2 className="mr-3 text-blue-500" size={24} /> {title}
              </h3>
            </div>
            <div className="p-16 flex flex-col justify-center items-center">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, ease: 'linear', duration: 1 }}>
                  <Loader2 className="w-8 h-8 text-blue-500 mb-4" />
                </motion.div>
                <span className="text-gray-500 dark:text-gray-400 font-medium">Fetching historical data...</span>
            </div>
          </motion.div>
        );
    }
    
    if (stateObj.isEmpty) return null;

    // Dynamically calculate summary metrics from the processed file data
    let totalRecords = 0;
    let totalAmount = 0;
    
    if (stateObj.data && stateObj.data.sections) {
       stateObj.data.sections.forEach(sec => {
          totalRecords += sec.data.length;
          // Look for 'Amount' or 'Total' column
          const amountIdx = sec.headers.findIndex(h => h.toLowerCase().includes('amount') || h.toLowerCase().includes('total'));
          if (amountIdx >= 0) {
             sec.data.forEach(row => {
                 const val = parseFloat(String(row[amountIdx]).replace(/,/g, ''));
                 if (!isNaN(val)) totalAmount += val;
             });
          }
       });
    }

    if (stateObj.error) {
       return (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 p-6 glass-card rounded-2xl border-l-4 border-red-500 shadow-md bg-red-50/30 dark:bg-red-900/10">
             <h3 className="text-xl font-bold text-red-600 dark:text-red-400 mb-2">{title} Failed</h3>
             <div className="text-gray-700 dark:text-gray-300 text-sm overflow-x-auto max-h-64 p-3 bg-white dark:bg-zinc-900 rounded border border-red-100 dark:border-red-900/30">
               <pre className="whitespace-pre-wrap font-mono text-xs">{stateObj.error}</pre>
             </div>
          </motion.div>
       );
    }

    if (!stateObj.data || !stateObj.data.sections) return null;
    
    const searchTerm = searchTerms[searchKey].toLowerCase();
    const dataObj = stateObj.data;
    
    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-md">
        <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gradient-to-r from-gray-50 to-white dark:from-zinc-900/50 dark:to-zinc-800/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex flex-col">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
              <Table2 className="mr-3 text-blue-500" size={24} /> {title}
            </h3>
            {stateObj.file && (
              <span className="text-sm text-gray-500 mt-1 flex items-center">
                <Clock size={14} className="mr-1" /> Last Processed: {new Date(stateObj.file.created_at).toLocaleString()}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-3 w-full md:w-auto">
            <button 
              onClick={() => setView(view === 'summary' ? 'preview' : 'summary')}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
            >
              {view === 'summary' ? <Table2 size={16} /> : <List size={16} />}
              <span>{view === 'summary' ? 'Data Preview' : 'Summary'}</span>
            </button>
            {view === 'preview' && (
              <>
                <div className="relative flex-1 md:flex-none">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                  <input 
                    type="text" 
                    value={searchTerms[searchKey]}
                    onChange={(e) => setSearchTerms(prev => ({ ...prev, [searchKey]: e.target.value }))}
                    placeholder="Search rows..." 
                    className="w-full pl-9 pr-4 py-2 bg-white dark:bg-zinc-900 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 ring-blue-500 shadow-sm"
                  />
                </div>
                <button 
                  onClick={() => {
                    let exportRows = [];
                    dataObj.sections.forEach(sec => {
                        sec.data.forEach(row => {
                            let rowObj = { "Section": sec.name };
                            sec.headers.forEach((h, i) => { rowObj[h] = row[i]; });
                            exportRows.push(rowObj);
                        });
                    });
                    exportToExcel(exportRows, `${title.replace(/ /g, '_')}_ExtractedData`);
                  }}
                  className="flex items-center px-4 py-2 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
                >
                  <FileSpreadsheet size={16} className="mr-2 text-green-600 dark:text-green-500" /> Export
                </button>
              </>
            )}
          </div>
        </div>

        {view === 'summary' ? (
           <div className="p-8 bg-gray-50/50 dark:bg-zinc-900/30">
              <div className="glass-card rounded-2xl p-6 relative overflow-hidden group max-w-sm mx-auto">
                <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${summaryColor} opacity-10 rounded-bl-full transition-transform group-hover:scale-110`} />
                <h3 className="text-gray-500 dark:text-gray-400 font-medium mb-2">{summaryTitle}</h3>
                <div className="text-4xl font-bold text-gray-900 dark:text-white mb-1">₹{totalAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                <div className="text-sm text-gray-400">{totalRecords} Records Processed</div>
              </div>
           </div>
        ) : (
        <div className="p-0">
          {dataObj.sections.map((section, idx) => {
            const filteredData = section.data.filter(row => {
               if (filters.orderId && !row.some(cell => String(cell).toLowerCase().includes(filters.orderId.toLowerCase()))) {
                 return false;
               }
               if (searchTerm && !row.some(cell => String(cell).toLowerCase().includes(searchTerm))) {
                 return false;
               }
               
               if (filters.matchPercentage !== 'any') {
                  const varIndex = section.headers.findIndex(h => String(h).toLowerCase().includes('variance') || String(h).toLowerCase().includes('diff'));
                  if (varIndex >= 0) {
                     const val = parseFloat(String(row[varIndex]).replace(/,/g, ''));
                     if (!isNaN(val)) {
                         if (filters.matchPercentage === '100' && Math.abs(val) > 0.01) return false;
                         if (filters.matchPercentage === '90' && Math.abs(val) > (0.1 * 100)) return false; 
                     }
                  }
               }
               return true;
            });

            if (filteredData.length === 0) return null;

            return (
              <div key={idx} className="mb-0">
                <div className="px-6 py-3 bg-gray-100/50 dark:bg-zinc-800/80 font-semibold text-gray-700 dark:text-gray-300 border-y border-gray-200 dark:border-zinc-700 flex justify-between items-center">
                  <span>{section.name}</span>
                  <span className="text-xs px-2 py-1 bg-white dark:bg-zinc-900 rounded-full border border-gray-200 dark:border-zinc-700 text-gray-500">{filteredData.length} records</span>
                </div>
                <div className="overflow-x-auto max-h-[500px] custom-scrollbar bg-white dark:bg-[#1a1a1a]">
                  <table className="w-full text-sm text-left text-gray-600 dark:text-gray-400 border-collapse">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50/90 dark:bg-zinc-900/90 backdrop-blur-md dark:text-gray-400 border-b border-gray-200 dark:border-zinc-800 sticky top-0 z-10 shadow-sm">
                      <tr>
                        {section.headers.map((h, i) => (
                          <th key={i} className="px-6 py-4 whitespace-nowrap font-bold tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-zinc-800/60">
                      {filteredData.slice(0, 100).map((row, i) => (
                        <tr key={i} className="bg-white dark:bg-transparent hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-200 group">
                          {row.map((cell, j) => (
                            <td key={j} className="px-6 py-4 whitespace-nowrap group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filteredData.length > 100 && (
                    <div className="px-6 py-4 bg-gray-50 dark:bg-zinc-800/50 text-center border-t border-gray-200 dark:border-zinc-700 text-sm text-gray-500">
                      Showing first 100 of {filteredData.length} records. Please download the file to view all records.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 relative">
      {/* Header */}
      <div className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">Run Recon</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Execute 3-way reconciliation pipeline</p>
        </div>
      </div>
      
      {/* Filters */}
      <div className="glass-card rounded-2xl p-3 flex flex-wrap justify-between items-center shadow-sm mb-8 w-full max-w-5xl">
        <div className="flex flex-wrap gap-3 items-center">
          <select 
            className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300"
            value={filters.period}
            onChange={e => setFilters({...filters, period: e.target.value})}
          >
            <option value="">Period (All)</option>
            {folders.map(f => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>

          <input 
            type="text" 
            placeholder="Order ID Filter..." 
            className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 w-40 text-gray-700 dark:text-gray-300"
            value={filters.orderId}
            onChange={e => setFilters({...filters, orderId: e.target.value})}
          />

          <select 
            className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300"
            value={filters.matchPercentage}
            onChange={e => setFilters({...filters, matchPercentage: e.target.value})}
          >
            <option value="any">Any Variance Match</option>
            <option value="100">Match 100% (No Variance)</option>
            <option value="90">Match &gt; 90%</option>
          </select>
        </div>
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
          <span>{running ? 'Processing All Validations...' : 'Run Reconciliation'}</span>
        </motion.button>
      </div>

      {/* Extracted Data Views */}
      <AnimatePresence>
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <ValidationSection title="Validation 1 (GRN vs Vendor)" stateObj={extractedData.v1} searchKey="v1" summaryTitle="GRN Amount" summaryColor="from-green-500 to-emerald-700" />
          <ValidationSection title="Validation 2 (Vendor vs Tally)" stateObj={extractedData.v2} searchKey="v2" summaryTitle="Vendor Invoice Amount" summaryColor="from-blue-500 to-indigo-700" />
          <ValidationSection title="Validation 3 (Tally vs Vendor)" stateObj={extractedData.v3} searchKey="v3" summaryTitle="Tally Amount" summaryColor="from-purple-500 to-fuchsia-700" />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
