import { useState, useEffect, useRef } from 'react';
import { useParams, useOutletContext } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { UploadCloud, Trash2, RotateCcw, Search, Download, CheckSquare, Table2, FileSpreadsheet, Loader2, Database } from 'lucide-react';
import { apiCall, apiCallForm } from '../api';

export default function FolderView() {
  const { id } = useParams();
  const { fetchNotifications, folders } = useOutletContext() || {};
  const [folderData, setFolderData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Data lists
  const [masterRows, setMasterRows] = useState([]);
  const [deletedRows, setDeletedRows] = useState([]);
  const [columns, setColumns] = useState([]);
  
  // Selections
  const [selectedMaster, setSelectedMaster] = useState(new Set());
  
  const fileInputRef = useRef(null);
  const searchInputRef = useRef(null);

  const fetchFolderData = async (query = '') => {
    try {
      setLoading(true);
      const meta = await apiCall(`/master/${id}`);
      setFolderData(meta.master || { folder_id: id });
      
      const searchParam = query ? `&search=${encodeURIComponent(query)}` : '';
      const rows = await apiCall(`/master/${id}/preview?limit=100${searchParam}`);
      if (rows.success && rows.data) {
        setMasterRows(rows.data);
        if (rows.data.length > 0) {
           const cols = Object.keys(rows.data[0]).filter(k => k !== '_row_fp' && k !== '_deleted_at');
           setColumns(cols); // Show all columns
        }
      }
      
      const deleted = await apiCall(`/master/${id}/rows/deleted`);
      if (deleted.success) setDeletedRows(deleted.data || []);

    } catch (e) {
      toast.error('Failed to load master data');
    } finally {
      setLoading(false);
    }
  };

  // When folder ID changes, reset selections and search
  useEffect(() => {
    setSearchTerm('');
    if (searchInputRef.current) searchInputRef.current.value = '';
    setSelectedMaster(new Set());
  }, [id]);

  // Debounced search effect handles both the initial load and all typing/pasting
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchFolderData(searchTerm);
    }, 400); // 400ms debounce
    return () => clearTimeout(timer);
  }, [searchTerm, id]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder_id', id);
    
    // Create an object URL in case it fails and we need to let the user download the failed file
    const fileObjectURL = URL.createObjectURL(file);
    
    const uploadProcess = async () => {
      try {
        const res = await apiCallForm('/upload', formData);
        
        // Handle soft errors returned as 200 OK
        if (res && res.success === false && res.error_code === 'file_exists') {
          // Use a non-blocking toast for replacement
          toast.warning("File already exists", {
            description: res.reason || 'A file with this name is already in the folder.',
            duration: 10000,
            action: {
              label: "Replace File",
              onClick: () => {
                const retryFormData = new FormData();
                retryFormData.append('file', file);
                retryFormData.append('folder_id', id);
                retryFormData.append('replace', 'true');
                
                toast.promise(apiCallForm('/upload', retryFormData), {
                  loading: 'Replacing file...',
                  success: () => {
                    fetchFolderData();
                    if (fetchNotifications) fetchNotifications();
                    return "File replaced successfully!";
                  },
                  error: (err) => err.message || "Failed to replace file"
                });
              }
            },
            cancel: {
              label: "Cancel",
              onClick: () => toast.info("Upload cancelled")
            }
          });
          // Throw a silent error so the outer promise toast doesn't show a red failure
          throw new Error('SILENT_CONFLICT');
        }

        // If another type of soft error occurred
        if (res && res.success === false) {
          throw new Error(res.message || res.reason || 'Failed to upload file');
        }

        return res;
      } catch (err) {
        // Handle hard HTTP errors (like 500)
        if (err.message === 'SILENT_CONFLICT') throw err;
        throw err;
      }
    };

    toast.promise(uploadProcess(), {
      loading: `Uploading and checking rules for ${file.name}...`,
      success: () => {
        fetchFolderData();
        if (fetchNotifications) fetchNotifications();
        if (fileInputRef.current) fileInputRef.current.value = '';
        return `${file.name} successfully verified and saved to master!`;
      },
      error: (err) => {
        if (fileInputRef.current) fileInputRef.current.value = '';
        if (err.message === 'SILENT_CONFLICT') {
          return 'Please confirm replacement in the notification popup.';
        }
        if (fetchNotifications) fetchNotifications();
        return `Upload rejected: ${err.message}`;
      }
    });

    e.target.value = null; // Reset input
  };

  const toggleMasterSelection = (rowId) => {
    const newSet = new Set(selectedMaster);
    if (newSet.has(rowId)) newSet.delete(rowId);
    else newSet.add(rowId);
    setSelectedMaster(newSet);
  };

  const handleBulkDelete = async () => {
    if (selectedMaster.size === 0) return;
    
    const formData = new FormData();
    formData.append('fingerprints', JSON.stringify(Array.from(selectedMaster)));
    
    toast.promise(
      apiCallForm(`/master/${id}/rows/delete`, formData),
      {
        loading: 'Deleting rows...',
        success: (res) => {
          if (!res.success) throw new Error(res.error || 'Failed to delete rows');
          fetchFolderData();
          setSelectedMaster(new Set());
          return 'Rows deleted successfully';
        },
        error: (err) => err.message
      }
    );
  };

  const handleRestore = async (rowFp) => {
    const formData = new FormData();
    formData.append('fingerprints', JSON.stringify([rowFp]));
    
    toast.promise(
      apiCallForm(`/master/${id}/rows/restore`, formData),
      {
        loading: 'Restoring row...',
        success: (res) => {
          if (!res.success) {
            throw new Error(res.error || res.message || 'Data already exist in master file');
          }
          fetchFolderData();
          return 'Row restored successfully';
        },
        error: (err) => err.message
      }
    );
  };

  const exportToExcel = (data, filename) => {
    if (data.length === 0) {
      toast.info('No data to export');
      return;
    }
    // Create a copy of the data without system/meta columns for export
    const exportData = data.map(row => {
      const newRow = { ...row };
      delete newRow._row_fp;
      delete newRow._deleted_at;
      return newRow;
    });

    const headers = Object.keys(exportData[0]);
    const csvContent = [
      headers.join(','),
      ...exportData.map(row => headers.map(h => `"${String(row[h] || '').replace(/"/g, '""')}"`).join(','))
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

  if (loading && !folderData) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="flex flex-col items-center text-gray-500">
           <Loader2 className="animate-spin w-8 h-8 mb-4" />
           <p>Loading Master Data...</p>
        </div>
      </div>
    );
  }

  const folderNameFromContext = folders?.find(f => f.id === parseInt(id))?.name;
  const masterName = (folderNameFromContext || folderData?.name || `Folder ${id}`).replace('Validation', '').replace('Folder', '').replace('-', '').trim();

  return (
    <div className="flex-1 overflow-y-auto p-8 relative">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight flex items-center">
          <Database className="mr-3 text-purple-500" size={32} />
          {masterName} Master File
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mt-2">Manage synced master data, upload new files, and restore deleted records.</p>
      </div>

      {/* Upload Zone */}
      <div 
        onClick={handleUploadClick}
        className="glass-card rounded-2xl p-8 mb-8 border-2 border-dashed border-blue-300 dark:border-blue-900/50 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-all cursor-pointer group flex flex-col items-center justify-center text-center"
      >
        <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm">
          <UploadCloud size={32} />
        </div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Upload to {masterName}</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
          Click to browse or drag and drop files here. Files will undergo deduplication and rule checks automatically.
        </p>
        <input 
          type="file" 
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden" 
          accept=".csv,.xlsx,.xls"
        />
      </div>

      {/* Master Data Preview */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-8">
        <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
            <div className="flex items-center space-x-4">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center">
                <Table2 className="mr-2" size={20} /> Master Data Preview
              </h3>
              {selectedMaster.size > 0 && (
                <motion.button 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  onClick={handleBulkDelete}
                  className="flex items-center px-3 py-1.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors shadow-sm"
                >
                  <Trash2 size={16} className="mr-1" /> Delete Selected ({selectedMaster.size})
                </motion.button>
              )}
            </div>

            <div className="flex items-center space-x-3 w-full md:w-auto">
              <div className="relative flex-1 md:flex-none">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input 
                  type="text" 
                  ref={searchInputRef}
                  defaultValue={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search..." 
                  className="w-full pl-9 pr-4 py-1.5 bg-white dark:bg-zinc-900 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 ring-blue-500 shadow-sm"
                />
              </div>
              <button 
                onClick={() => exportToExcel(masterRows, `${masterName}_Master`)}
                className="flex items-center px-3 py-1.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
              >
                <FileSpreadsheet size={16} className="mr-2 text-green-600 dark:text-green-500" /> Export Excel
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-800/80 dark:text-gray-400 sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="px-4 py-3 w-12 text-center bg-gray-50 dark:bg-zinc-800">
                  <CheckSquare size={16} className="text-gray-400 inline" />
                </th>
                <th className="px-4 py-3 bg-gray-50 dark:bg-zinc-800">ID</th>
                {columns.map(c => {
                  const isSystem = folderData?.columns?.system_columns?.includes(c);
                  return (
                    <th key={c} className={`px-4 py-3 whitespace-nowrap ${isSystem ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-800 dark:text-indigo-300 border-l border-indigo-200 dark:border-indigo-800/50' : 'bg-gray-50 dark:bg-zinc-800'}`}>
                      {c}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {masterRows.length === 0 ? (
                <tr>
                  <td colSpan="100%" className="px-4 py-12 text-center italic text-gray-400">No active rows found in this Master File.</td>
                </tr>
              ) : (
                masterRows.map(row => (
                  <tr key={row._row_fp} className="border-b border-gray-100 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3 text-center">
                      <input 
                        type="checkbox" 
                        checked={selectedMaster.has(row._row_fp)}
                        onChange={() => toggleMasterSelection(row._row_fp)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 dark:bg-zinc-700 dark:border-zinc-600"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium">{row._row_fp}</td>
                    {columns.map(c => {
                      const isSystem = folderData?.columns?.system_columns?.includes(c);
                      return (
                        <td key={c} className={`px-4 py-3 truncate max-w-[150px] ${isSystem ? 'bg-indigo-50/40 dark:bg-indigo-900/10 border-l border-indigo-100 dark:border-indigo-800/30 font-medium' : ''}`} title={row[c]}>
                          {row[c]}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Deleted Rows Preview */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card rounded-2xl overflow-hidden mb-12">
        <div className="p-4 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50 flex justify-between items-center">
          <h3 className="text-sm font-bold text-gray-600 dark:text-gray-400 flex items-center">
            <Trash2 className="mr-2" size={16} /> Deleted Rows
          </h3>
          {deletedRows.length > 0 && (
             <button 
               onClick={() => exportToExcel(deletedRows, `${masterName}_Deleted`)}
               className="flex items-center px-2 py-1 text-xs font-medium bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded text-gray-600 dark:text-gray-400 hover:bg-gray-50 transition-colors"
             >
               <FileSpreadsheet size={14} className="mr-1 text-green-600" /> Export
             </button>
          )}
        </div>
        <div className="overflow-x-auto max-h-64">
          <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-800/80 dark:text-gray-400 sticky top-0 shadow-sm">
              <tr>
                <th className="px-4 py-2 bg-gray-50 dark:bg-zinc-800">Action</th>
                <th className="px-4 py-2 bg-gray-50 dark:bg-zinc-800">Deleted At</th>
                {columns.map(c => {
                  const isSystem = folderData?.columns?.system_columns?.includes(c);
                  return (
                    <th key={c} className={`px-4 py-2 whitespace-nowrap ${isSystem ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-800 dark:text-indigo-300 border-l border-indigo-200 dark:border-indigo-800/50' : 'bg-gray-50 dark:bg-zinc-800'}`}>
                      {c}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {deletedRows.length === 0 ? (
                <tr>
                  <td colSpan="100%" className="px-4 py-8 text-center italic text-gray-400">No deleted rows.</td>
                </tr>
              ) : (
                deletedRows.map(row => (
                  <tr key={row._row_fp} className="border-b border-gray-100 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800/30">
                    <td className="px-4 py-2">
                      <button 
                        onClick={() => handleRestore(row._row_fp)}
                        className="text-blue-600 hover:text-blue-800 font-medium text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded transition-colors"
                      >
                        <RotateCcw size={14} className="inline mr-1" /> Restore
                      </button>
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-xs">
                      {row._deleted_at ? new Date(row._deleted_at).toLocaleString() : 'N/A'}
                    </td>
                    {columns.map(c => {
                      const isSystem = folderData?.columns?.system_columns?.includes(c);
                      return (
                        <td key={c} className={`px-4 py-2 truncate max-w-[150px] ${isSystem ? 'bg-indigo-50/40 dark:bg-indigo-900/10 border-l border-indigo-100 dark:border-indigo-800/30 font-medium' : ''}`} title={row[c]}>
                          {row[c]}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
