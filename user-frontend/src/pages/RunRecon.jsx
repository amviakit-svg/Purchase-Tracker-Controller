import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Play, Download, Table2, List, Loader2, Search, FileSpreadsheet, Clock, Hash } from 'lucide-react';
import { apiCall, apiCallForm } from '../api';

import * as XLSX from 'xlsx';

const idb = {
  db: null,
  async getDb() {
    if (this.db) return this.db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('PurchaseTrackerDB', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('cache');
      req.onsuccess = () => { this.db = req.result; resolve(req.result); };
      req.onerror = () => reject(req.error);
    });
  },
  async get(key) {
    try {
      const db = await this.getDb();
      return new Promise((resolve) => {
        const tx = db.transaction('cache', 'readonly');
        const req = tx.objectStore('cache').get(key);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      });
    } catch (e) { return null; }
  },
  async set(key, val) {
    try {
      const db = await this.getDb();
      return new Promise((resolve) => {
        const tx = db.transaction('cache', 'readwrite');
        tx.objectStore('cache').put(val, key);
        tx.oncomplete = () => resolve();
      });
    } catch (e) {}
  }
};

// Export helper using xlsx for multiple sheets
export const exportToExcel = (data, summaryData, filename) => {
  if (data.length === 0) {
    toast.info('No data to export');
    return;
  }
  
  const wb = XLSX.utils.book_new();
  const wsData = XLSX.utils.json_to_sheet(data);
  XLSX.utils.book_append_sheet(wb, wsData, "Data");
  
  if (summaryData) {
      const wsSummary = XLSX.utils.json_to_sheet([summaryData]);
      XLSX.utils.book_append_sheet(wb, wsSummary, "Summary");
  }
  
  XLSX.writeFile(wb, `${filename}.xlsx`);
};

export default function RunRecon() {
  const [running, setRunning] = useState(false);
  const [folders, setFolders] = useState([]);
  
  
  const [dynamicFilters, setDynamicFilters] = useState([]);
  const [dynamicCards, setDynamicCards] = useState([]);
  
  useEffect(() => {
      const loadSettings = async () => {
          try {
              const resF = await apiCall('/settings/filters');
              if (resF && resF.filters) setDynamicFilters(resF.filters.filter(f => f.is_active));
              const resC = await apiCall('/settings/cards');
              if (resC && resC.cards) setDynamicCards(resC.cards.filter(c => c.is_active));
          } catch(e) { console.error('Failed to load settings', e); }
      };
      loadSettings();
  }, []);

  const [filters, setFilters] = useState({
    period: '',
    orderId: '',
    matchPercentage: 'any'
  });

  const moduleId = localStorage.getItem('module_id') || "1";
  
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
    const loadCachedFirst = async () => {
      const cached = await idb.get(`extractedData_${moduleId}`);
      if (cached) {
        setExtractedData(cached);
      }
      // Fetch fresh data quietly in background
      loadHistoricalData();
    };
    loadCachedFirst();
  }, [moduleId]);

  // Helper to update state and cache simultaneously
  const updateExtractedData = (updater) => {
    setExtractedData((prev) => {
       const next = typeof updater === 'function' ? updater(prev) : updater;
       idb.set(`extractedData_${moduleId}`, next);
       return next;
    });
  };

  const loadHistoricalData = async () => {
     try {
       const vids = [1, 2, 3];
       const results = await Promise.all(vids.map(async (vid) => {
          try {
             const res = await apiCall(`/processed/files?validation_id=${vid}&t=${Date.now()}`, { skipCache: true });
             if (res.success && res.files && res.files.length > 0) {
                const latestFile = res.files[0];
                const preview = await apiCall(`/processed/${latestFile.id}/preview`);
                return { vid, payload: { data: preview, file: latestFile, error: null } };
             } else {
                return { vid, payload: { data: null, file: null, error: null, isEmpty: true } };
             }
          } catch(e) {
             console.error(`Error loading preview for V${vid}`, e);
             return { vid, payload: { data: null, file: null, error: 'Failed to load historical data' } };
          }
       }));
       
       updateExtractedData(prev => {
          const next = { ...prev };
          results.forEach(r => { 
             // Only update if we successfully fetched new data or confirmed it's empty
             if (r.payload.data || r.payload.isEmpty || r.payload.error) {
                 next[`v${r.vid}`] = r.payload; 
             }
          });
          return next;
       });
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
          const status = await apiCall(`/process/status?t=${Date.now()}`, { skipCache: true });
          
          if (status.status !== 'processing' || status.status === 'error') {
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
              const res = await apiCall(`/processed/files?validation_id=${vid}&t=${Date.now()}`, { skipCache: true });
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
    // Phase 1 prep for Validation 2 (Matches Admin Portal)
    if (vid === 2) {
      toast.loading(`Validation ${vid}: Preparing Phase 1...`, { id: `prep-${vid}` });
      try {
        const p1Data = await apiCall(`/rules/1?validation_id=${vid}`);
        if (!p1Data.success || !p1Data.rules || p1Data.rules.length === 0) {
            throw new Error("No Phase 1 rule found. Please configure in Admin.");
        }
        
        const p1Rule = p1Data.rules[p1Data.rules.length - 1];
        let p1Config = JSON.parse(p1Rule.config);
        
        const generateForm = new FormData();
        generateForm.append('file_id', p1Config.file_id);
        generateForm.append('sheet_name', p1Config.sheet_name);
        generateForm.append('column_name', p1Config.column);
        generateForm.append('header_row', 1);
        generateForm.append('fields', JSON.stringify(p1Config.fields || []));
        generateForm.append('validation_id', vid);

        const genData = await apiCallForm('/primary/generate', generateForm);
        if (!genData || !genData.success) {
            throw new Error('Failed to generate primary data.');
        }

        p1Config.primary_file = genData.primary_file;
        p1Config.total_unique = genData.total_unique;
        
        const updateForm = new FormData();
        updateForm.append('phase', 1);
        updateForm.append('config', JSON.stringify(p1Config));
        updateForm.append('validation_id', vid);
        
        const updateData = await apiCallForm('/rules', updateForm);
        if (!updateData || !updateData.success) {
            throw new Error('Failed to update Phase 1 rule.');
        }
        toast.success(`Validation ${vid}: Phase 1 Prepared`, { id: `prep-${vid}` });
      } catch (e) {
        toast.error(`Validation ${vid} Prep Failed: ${e.message}`, { id: `prep-${vid}` });
        throw e;
      }
    }

    toast.loading(`Validation ${vid} rules processing...`, { id: `proc-${vid}` });
    const formData = new FormData();
    formData.append('validation_id', vid);
    formData.append('force', 'false');
    
    let customFilename;
    if (vid === 1) customFilename = `Validation 1 - (GRN vs Vendor Invoice)`;
    else if (vid === 3) customFilename = `Validation 3 - (Tally vs Vendor Invoice)`;
    else customFilename = `Validation 2 - (Vendor Invoice vs Tally)`;
    formData.append('custom_filename', customFilename);

    try {
      const startData = await apiCallForm('/process', formData);
      if (startData.type === 'validation_warning') {
         throw new Error(`Missing columns: ${startData.missing_columns.join(', ')}`);
      }
      if (!startData.success) {
         throw new Error(startData.message || 'Failed to start processing');
      }

      const resultFiles = await pollProcessStatus(vid);
      if (resultFiles.length === 0) {
         throw new Error(`No output files generated.`);
      }
      toast.success(`Validation ${vid} processing success`, { id: `proc-${vid}` });

      toast.loading(`Validation ${vid} syncing...`, { id: `sync-${vid}` });
      const latestFile = resultFiles[0];
      const preview = await apiCall(`/processed/${latestFile.id}/preview`);
      toast.success(`Validation ${vid} sync success`, { id: `sync-${vid}` });
      return { data: preview, file: latestFile };
    } catch (e) {
      toast.error(`Validation ${vid} reject status: ${e.message}`, { id: `proc-${vid}` });
      throw e;
    }
  };

  const handleRunRecon = async () => {
    if (running) return;
    setRunning(true);
    updateExtractedData({ 
       v1: { data: null, file: null, error: null }, 
       v2: { data: null, file: null, error: null }, 
       v3: { data: null, file: null, error: null } 
    });
    
    let errCount = 0;
    
    try {
      const v1 = await runValidation(1);
      updateExtractedData(prev => ({ ...prev, v1: { ...v1, error: null } }));
    } catch (e) {
      errCount++;
      updateExtractedData(prev => ({ ...prev, v1: { data: null, file: null, error: e.message } }));
    }

    try {
      const v2 = await runValidation(2);
      updateExtractedData(prev => ({ ...prev, v2: { ...v2, error: null } }));
    } catch (e) {
      errCount++;
      updateExtractedData(prev => ({ ...prev, v2: { data: null, file: null, error: e.message } }));
    }

    try {
      const v3 = await runValidation(3);
      updateExtractedData(prev => ({ ...prev, v3: { ...v3, error: null } }));
    } catch (e) {
      errCount++;
      updateExtractedData(prev => ({ ...prev, v3: { data: null, file: null, error: e.message } }));
    }
    
    setRunning(false);
    if (errCount === 3) {
       toast.error("All validations failed.");
    } else if (errCount > 0) {
       toast.warning("Reconciliation finished with some errors.");
    } else {
       toast.success("All validations processed and synced successfully!");
    }
  };

    const ValidationSection = ({ title, stateObj, searchKey, summaryTitle, summaryColor, isRunning }) => {
        const [processedData, setProcessedData] = useState(null);

        const formatCellData = (cell, header) => {
            return cell;
        };

        const moduleId = localStorage.getItem('module_id') || "1";
    const cacheKey = `processedData_${moduleId}_${searchKey}`;

    const [view, setView] = useState('preview');
    const [dbLoaded, setDbLoaded] = useState(false);
    
    useEffect(() => {
       async function load() {
           const c = await idb.get(cacheKey);
           if (c) setProcessedData(c);
           setDbLoaded(true);
       }
       load();
    }, [cacheKey]);

    const [isProcessing, setIsProcessing] = useState(false);
    const [rowLimit, setRowLimit] = useState(10);
    const [localSearch, setLocalSearch] = useState(searchTerms[searchKey] || '');
    
    useEffect(() => {
        setLocalSearch(searchTerms[searchKey] || '');
    }, [searchTerms[searchKey]]);

    useEffect(() => {
       if (!stateObj || !stateObj.data || !stateObj.data.sections) {
           setProcessedData(null);
           return;
       }
       
       setIsProcessing(true);
       
       const workerCode = `
         self.onmessage = function(e) {
           const { dataObj, filters, searchTerm, limit } = e.data;
           
           let totalRecords = 0;
           let totalAmount = 0;
           let processedSections = [];

           dataObj.sections.forEach(sec => {
               totalRecords += sec.data.length;
               const amountIdx = sec.headers.findIndex(h => h.toLowerCase().includes('amount') || h.toLowerCase().includes('total'));
               if (amountIdx >= 0) {
                  sec.data.forEach(row => {
                      const val = parseFloat(String(row[amountIdx]).replace(/,/g, ''));
                      if (!isNaN(val)) totalAmount += val;
                  });
               }

               const lowerOrderId = filters.orderId ? filters.orderId.toLowerCase() : '';
               const lowerSearch = searchTerm ? searchTerm.toLowerCase() : '';
               const varIndex = filters.matchPercentage !== 'any' 
                 ? sec.headers.findIndex(h => String(h).toLowerCase().includes('variance') || String(h).toLowerCase().includes('diff'))
                 : -1;

               const filteredData = sec.data.filter(row => {
                  if (lowerOrderId && !row.some(cell => String(cell).toLowerCase().includes(lowerOrderId))) return false;
                  if (lowerSearch && !row.some(cell => String(cell).toLowerCase().includes(lowerSearch))) return false;
                  if (varIndex >= 0) {
                     const val = parseFloat(String(row[varIndex]).replace(/,/g, ''));
                     if (!isNaN(val)) {
                         if (filters.matchPercentage === '100' && Math.abs(val) > 0.01) return false;
                         if (filters.matchPercentage === '90' && Math.abs(val) > (0.1 * 100)) return false; 
                     }
                  }
                  return true;
               });

               processedSections.push({
                   name: sec.name,
                   headers: sec.headers,
                   filteredCount: filteredData.length,
                   dataPreview: filteredData.slice(0, limit)
               });
           });

           self.postMessage({ 
               totalRecords, 
               totalAmount, 
               processedSections,
               summary_sections: dataObj.summary_sections || []
           });
         };
       `;
       const blob = new Blob([workerCode], {type: 'application/javascript'});
       const worker = new Worker(URL.createObjectURL(blob));
       
       worker.onmessage = (e) => {
           setProcessedData(e.data);
           idb.set(cacheKey, e.data);
           setIsProcessing(false);
           worker.terminate();
       };
       
       worker.postMessage({
           dataObj: stateObj.data,
           filters: filters,
           searchTerm: searchTerms[searchKey] || '',
           limit: parseInt(rowLimit, 10) || 50
       });
       
       return () => worker.terminate();
    }, [stateObj, filters, searchTerms[searchKey], rowLimit]);

    if (!stateObj || (!stateObj.data && !stateObj.error && !stateObj.isEmpty)) {
        if (!isRunning) {
            return (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-sm animate-pulse">
                <div className="h-16 bg-gray-100 dark:bg-zinc-800 border-b border-gray-200 dark:border-zinc-700 flex justify-between items-center px-6">
                   <div className="h-6 w-48 bg-gray-200 dark:bg-zinc-700 rounded"></div>
                </div>
                <div className="h-64 bg-gray-50/50 dark:bg-zinc-900/30"></div>
              </motion.div>
            );
        }
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
                <span className="text-gray-500 dark:text-gray-400 font-medium mt-4">Running Validation...</span>
            </div>
          </motion.div>
        );
    }
    
    const isActuallyEmpty = (stateObj.isEmpty && !stateObj.error) || 
        (stateObj.data && (!stateObj.data.sections || stateObj.data.sections.length === 0 || stateObj.data.sections.every(s => !s.data || s.data.length === 0)));
    if (isActuallyEmpty) {
        return (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-md">
            <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gradient-to-r from-gray-50 to-white dark:from-zinc-900/50 dark:to-zinc-800/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <h3 className="text-xl font-bold text-gray-500 dark:text-gray-400 flex items-center">
                <Table2 className="mr-3 text-gray-400" size={24} /> {title}
              </h3>
            </div>
            <div className="p-16 flex flex-col justify-center items-center text-center">
                <div className="bg-gray-100 dark:bg-zinc-800/50 p-4 rounded-full mb-4">
                   <Table2 className="w-8 h-8 text-gray-400" />
                </div>
                <h4 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">No Data Available</h4>
                <span className="text-gray-500 dark:text-gray-400 font-medium max-w-md">No source file available or processed output found. The validation may not have been run or the source files were deleted.</span>
            </div>
          </motion.div>
        );
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
    
    const dataObj = stateObj.data;

    if (!dbLoaded) return null;
    
    if (!processedData && isProcessing) {
        return (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-md">
            <div className="p-6 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center gap-4">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center opacity-50">
                <Table2 className="mr-3 text-blue-500" size={24} /> {title}
              </h3>
            </div>
            <div className="p-16 flex flex-col justify-center items-center">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, ease: 'linear', duration: 1 }}>
                  <Loader2 className="w-8 h-8 text-blue-500 mb-4" />
                </motion.div>
                <span className="text-gray-500 dark:text-gray-400 font-medium mt-4">Loading saved data...</span>
            </div>
          </motion.div>
        );
    }
    
    if (!processedData) return null;

    const { totalRecords, totalAmount, processedSections } = processedData;
    
    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-12 shadow-md">
        <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gradient-to-r from-gray-50 to-white dark:from-zinc-900/50 dark:to-zinc-800/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex flex-col">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
              <Table2 className="mr-3 text-blue-500" size={24} /> {title}
            </h3>
            {stateObj.file && (
              <div className="flex items-center text-green-600 dark:text-green-500 font-medium text-sm mt-1">
                <Clock size={14} className="mr-1" /> Last Updated: {stateObj.file.created_at} UTC
              </div>
            )}
          </div>
          <div className="flex items-center space-x-3 w-full md:w-auto">
            <button 
              onClick={() => {
                 if (stateObj.file && stateObj.file.id) {
                     window.open(`http://localhost:5000/api/processed/${stateObj.file.id}/download`, '_blank');
                 } else {
                     toast.error('File not available for download');
                 }
              }}
              className="flex items-center px-4 py-2 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
              title="Download Excel File (includes Summary sheet)"
            >
              <FileSpreadsheet size={16} className="mr-2 text-green-600 dark:text-green-500" /> Export
            </button>
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
                  <Hash className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                  <input 
                    type="number" 
                    value={rowLimit}
                    onChange={(e) => setRowLimit(e.target.value)}
                    placeholder="Rows..." 
                    title="Number of rows to display"
                    className="w-24 pl-9 pr-2 py-2 bg-white dark:bg-zinc-900 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 ring-blue-500 shadow-sm"
                  />
                </div>
                <div className="relative flex-1 md:flex-none">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                  <input 
                    type="text" 
                    value={localSearch}
                    onChange={(e) => setLocalSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        setSearchTerms(prev => ({ ...prev, [searchKey]: localSearch }));
                      }
                    }}
                    placeholder="Search (Press Enter)..." 
                    className="w-full pl-9 pr-4 py-2 bg-white dark:bg-zinc-900 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 ring-blue-500 shadow-sm"
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {view === 'summary' ? (
           <div className="p-0">
             {(() => {
                const summaryList = stateObj?.data?.summary_sections || processedData?.summary_sections || stateObj?.data?.data?.summary_sections || [];
                if (summaryList.length > 0) {
                  return summaryList.map((section, idx) => (
                    <div key={idx} className="mb-0">
                   <div className="px-6 py-3 bg-gray-100/50 dark:bg-zinc-800/80 font-semibold text-gray-700 dark:text-gray-300 border-y border-gray-200 dark:border-zinc-700">
                     <span>{section.name}</span>
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
                         {section.data.map((row, i) => (
                           <tr key={i} className="bg-white dark:bg-transparent hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-200 group">
                             {row.map((cell, j) => (
                               <td key={j} className="px-6 py-4 whitespace-nowrap group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors">{formatCellData(cell, section.headers[j])}</td>
                             ))}
                           </tr>
                         ))}
                       </tbody>
                     </table>
                   </div>
                 </div>
               ));
              } else {
                return (
                  <div className="p-8 bg-gray-50/50 dark:bg-zinc-900/30">
                    <div className="glass-card rounded-xl p-8 max-w-sm mx-auto shadow-sm border border-gray-100 dark:border-zinc-800 relative overflow-hidden group">
                      <div className={`absolute top-0 right-0 w-32 h-32 bg-current opacity-[0.03] rounded-bl-full transform translate-x-8 -translate-y-8 transition-transform group-hover:scale-110 ${summaryColor}`}></div>
                      <h4 className="text-gray-500 dark:text-gray-400 font-medium mb-2">{summaryTitle}</h4>
                      <div className={`text-4xl font-bold tracking-tight ${summaryColor}`}>
                        {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(totalAmount || 0)}
                      </div>
                      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-zinc-800 flex justify-between items-center text-sm">
                        <span className="text-gray-500 dark:text-gray-400">Total Records</span>
                        <span className="font-semibold text-gray-900 dark:text-white bg-gray-100 dark:bg-zinc-800 px-3 py-1 rounded-full">{totalRecords?.toLocaleString() || 0}</span>
                      </div>
                    </div>
                  </div>
                );
              }
            })()}
           </div>
        ) : (
        <div className="p-0">
          {processedSections.map((section, idx) => {
            if (section.filteredCount === 0) return null;

            return (
              <div key={idx} className="mb-0">
                <div className="px-6 py-3 bg-gray-100/50 dark:bg-zinc-800/80 font-semibold text-gray-700 dark:text-gray-300 border-y border-gray-200 dark:border-zinc-700 flex justify-between items-center">
                  <span>{section.name}</span>
                  <span className="text-xs px-2 py-1 bg-white dark:bg-zinc-900 rounded-full border border-gray-200 dark:border-zinc-700 text-gray-500">{section.filteredCount} records</span>
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
                      {section.dataPreview.map((row, i) => (
                        <tr key={i} className="bg-white dark:bg-transparent hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-200 group">
                          {row.map((cell, j) => (
                            <td key={j} className="px-6 py-4 whitespace-nowrap group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors">{formatCellData(cell, section.headers[j])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {section.filteredCount > rowLimit && (
                    <div className="px-6 py-4 bg-gray-50 dark:bg-zinc-800/50 text-center border-t border-gray-200 dark:border-zinc-700 text-sm text-gray-500">
                      Showing first {rowLimit} of {section.filteredCount} records. Please download the file to view all records.
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
    <div className="flex flex-col h-full bg-transparent overflow-y-auto p-8 relative">
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
          {dynamicFilters.map((f, i) => {
            const isPeriod = f.field_name === 'Period';
            const isOrderId = f.field_name === 'Order ID';
            const isVariance = f.field_name === 'Variance';
            const key = isPeriod ? 'period' : isOrderId ? 'orderId' : isVariance ? 'matchPercentage' : 'dyn_' + f.id;
            
            let inputElement = null;
            if (f.filter_type === 'Dropdown' && isPeriod) {
                inputElement = (
                    <select 
                        key={f.id}
                        className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300"
                        value={filters.period || ''}
                        onChange={e => setFilters({...filters, period: e.target.value})}
                    >
                        <option value="">Period (All)</option>
                        {folders.map(folder => <option key={folder.id} value={folder.id}>{folder.name}</option>)}
                    </select>
                );
            } else if (f.filter_type === 'Dropdown' && isVariance) {
                inputElement = (
                    <select 
                        key={f.id}
                        className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 text-gray-700 dark:text-gray-300"
                        value={filters.matchPercentage || 'any'}
                        onChange={e => setFilters({...filters, matchPercentage: e.target.value})}
                    >
                        <option value="any">Variance (Any)</option>
                        <option value="100">Exact Match (0 Variance)</option>
                        <option value="90">Minor Variance (≤ 10%)</option>
                    </select>
                );
            } else if (f.filter_type === 'Search' || f.filter_type === 'Text') {
                inputElement = (
                    <input 
                        key={f.id}
                        type="text" 
                        placeholder={f.field_name + '...'} 
                        value={filters[key] || ''}
                        onChange={e => setFilters({...filters, [key]: e.target.value})}
                        className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 w-40 text-gray-700 dark:text-gray-300"
                    />
                );
            } else {
                // Generic text for anything else
                inputElement = (
                    <input 
                        key={f.id}
                        type="text" 
                        placeholder={f.field_name + '...'} 
                        value={filters[key] || ''}
                        onChange={e => setFilters({...filters, [key]: e.target.value})}
                        className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 w-40 text-gray-700 dark:text-gray-300"
                    />
                );
            }

            return (
                <React.Fragment key={'frag_'+f.id}>
                    {inputElement}
                    {i < dynamicFilters.length - 1 && <div className="h-4 w-px bg-gray-300 dark:bg-zinc-700 mx-1"></div>}
                </React.Fragment>
            );
          })}
          {dynamicFilters.length > 0 && <div className="h-4 w-px bg-gray-300 dark:bg-zinc-700 mx-1"></div>}
          <div className="relative">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
             <input 
                 type="text" 
                 placeholder="Global Find..." 
                 value={filters.orderId || ''}
                 onChange={e => setFilters({...filters, orderId: e.target.value})}
                 className="bg-transparent border border-gray-200 dark:border-zinc-700 rounded-lg pl-8 pr-3 py-1.5 text-sm outline-none focus:ring-2 ring-blue-500 w-48 text-gray-700 dark:text-gray-300"
             />
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {dynamicCards.length > 0 && (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {dynamicCards.map((card, i) => {
            const isGRN = card.card_name.includes('GRN');
            const isVendor = card.card_name.includes('Vendor');
            const isTally = card.card_name.includes('Tally');
            
            let amount = '₹0.00';
            let count = 0;
            let color = 'from-gray-500 to-gray-700';
            
            if (isGRN) color = 'from-green-500 to-emerald-700';
            else if (isVendor) color = 'from-blue-500 to-indigo-700';
            else if (isTally) color = 'from-purple-500 to-fuchsia-700';
            else {
                const colors = ['from-teal-500 to-teal-700', 'from-rose-500 to-rose-700', 'from-amber-500 to-amber-700'];
                color = colors[i % colors.length];
            }

            return (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                key={card.id} 
                className="glass-card rounded-2xl p-6 relative overflow-hidden group"
              >
                <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${color} opacity-10 rounded-bl-full transition-transform group-hover:scale-110`} />
                <h3 className="text-gray-500 dark:text-gray-400 font-medium mb-2">{card.card_name}</h3>
                <div className="text-4xl font-bold text-gray-900 dark:text-white mb-1">{amount}</div>
                <div className="text-sm text-gray-400">{count} {card.sub_calc || ''}</div>
              </motion.div>
            );
        })}
      </div>
      )}

      {/* Main Action Button */}
      <div className="flex justify-center mb-10">
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
          <span>{running ? 'Processing All Validations...' : 'Run Validation'}</span>
        </motion.button>
      </div>

      {/* Extracted Data Views */}
      <AnimatePresence>
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <ValidationSection title="Validation 1 (GRN vs Vendor)" stateObj={extractedData.v1} searchKey="v1" summaryTitle="GRN Amount" summaryColor="from-green-500 to-emerald-700" isRunning={running} />
          <ValidationSection title="Validation 2 (Vendor vs Tally)" stateObj={extractedData.v2} searchKey="v2" summaryTitle="Vendor Invoice Amount" summaryColor="from-blue-500 to-indigo-700" isRunning={running} />
          <ValidationSection title="Validation 3 (Tally vs Vendor)" stateObj={extractedData.v3} searchKey="v3" summaryTitle="Tally Amount" summaryColor="from-purple-500 to-fuchsia-700" isRunning={running} />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
