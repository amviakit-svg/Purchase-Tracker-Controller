import { useState, useEffect, useRef } from 'react';
import { useParams, useOutletContext } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { UploadCloud, Trash2, RotateCcw, Search, Download, CheckSquare, Table2, FileSpreadsheet, Loader2, Database, Eye, X } from 'lucide-react';
import { apiCall, apiCallForm, API_BASE_URL } from '../api';

export default function FolderView() {
  const { id } = useParams();
  const { fetchNotifications, folders } = useOutletContext() || {};
  const [folderData, setFolderData] = useState(() => {
    try { const c = localStorage.getItem(`folderData_${id}`); if (c) return JSON.parse(c); } catch(e) {}
    return null;
  });

  const [files, setFiles] = useState([]);
  const syncPollingRef = useRef(null);
  
  const [masterRows, setMasterRows] = useState(() => {
    try { const c = localStorage.getItem(`masterRows_${id}`); if (c) return JSON.parse(c); } catch(e) {}
    return [];
  });
  
  const [deletedRows, setDeletedRows] = useState(() => {
    try { const c = localStorage.getItem(`deletedRows_${id}`); if (c) return JSON.parse(c); } catch(e) {}
    return [];
  });
  
  const [columns, setColumns] = useState(() => {
    try { const c = localStorage.getItem(`columns_${id}`); if (c) return JSON.parse(c); } catch(e) {}
    return [];
  });
  
  const [loading, setLoading] = useState(!localStorage.getItem(`masterRows_${id}`));
  const [searchTerm, setSearchTerm] = useState('');
  
  // Selections
  const [selectedMaster, setSelectedMaster] = useState(new Set());
  
  const fileInputRef = useRef(null);
  const searchInputRef = useRef(null);

  // File Details Modal State
  const [isFileDetailsModalOpen, setIsFileDetailsModalOpen] = useState(false);
  const [selectedFileDetails, setSelectedFileDetails] = useState(null);

  const handleViewFile = async (fileId) => {
    try {
      const data = await apiCall(`/files/${fileId}/details`);
      setSelectedFileDetails(data?.file?.sheets_detail || []);
      setIsFileDetailsModalOpen(true);
    } catch (err) {
      toast.error('Failed to load file details');
    }
  };

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm("Are you sure you want to delete this uploaded file?")) return;
    try {
      await apiCall(`/files/${fileId}`, { method: 'DELETE' });
      toast.success("File deleted successfully");
      fetchFiles();
    } catch (err) {
      toast.error(err.message || "Failed to delete file");
    }
  };

  const fetchFolderData = async (query = '') => {
    try {
      setLoading(true);
      const meta = await apiCall(`/master/${id}`);
      const newFolderData = meta.master || { folder_id: id };
      setFolderData(newFolderData);
      try { localStorage.setItem(`folderData_${id}`, JSON.stringify(newFolderData)); } catch(e) {}
      
      const searchParam = query ? `&search=${encodeURIComponent(query)}` : '';
      const rows = await apiCall(`/master/${id}/preview?limit=100${searchParam}`);
      if (rows.success && rows.data) {
        setMasterRows(rows.data);
        try { localStorage.setItem(`masterRows_${id}`, JSON.stringify(rows.data)); } catch(e) {}
        
        if (rows.data.length > 0) {
           const cols = Object.keys(rows.data[0]).filter(k => k !== '_row_fp' && k !== '_deleted_at');
           setColumns(cols);
           try { localStorage.setItem(`columns_${id}`, JSON.stringify(cols)); } catch(e) {}
        }
      }
      
      const deleted = await apiCall(`/master/${id}/rows/deleted`);
      if (deleted.success) {
          const dRows = deleted.data || [];
          setDeletedRows(dRows);
          try { localStorage.setItem(`deletedRows_${id}`, JSON.stringify(dRows)); } catch(e) {}
      }

    } catch (e) {
      toast.error('Failed to load master data');
    } finally {
      setLoading(false);
    }
  };

  const fetchFiles = async () => {
    try {
      const data = await apiCall(`/files/${id}`);
      if (data && data.success) {
        setFiles(data.files);
        // Polling logic
        const needsPolling = data.files.some(f => f.sync_status === 'in_processing' || f.sync_status === 'pending');
        if (needsPolling) {
           if (!syncPollingRef.current) {
               syncPollingRef.current = setInterval(fetchFiles, 2000);
           }
        } else {
           if (syncPollingRef.current) {
               clearInterval(syncPollingRef.current);
               syncPollingRef.current = null;
           }
        }
      }
    } catch (e) {
      console.error("Failed to load files", e);
    }
  };

  useEffect(() => {
    return () => {
      if (syncPollingRef.current) clearInterval(syncPollingRef.current);
    };
  }, []);

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
      fetchFiles();
    }, 400); // 400ms debounce
    return () => clearTimeout(timer);
  }, [searchTerm, id]);

  const forceRetrySync = async (fileId) => {
    if (!window.confirm("Are you sure you want to force this file to retry syncing?")) return;
    try {
        toast.info("Scheduling file for sync...");
        const res = await apiCall(`/files/${fileId}/retry-sync`, { method: 'POST' });
        if (res && res.success) {
            toast.success("File scheduled for sync.");
            fetchFiles();
        } else {
            toast.error(res ? res.error : "Failed to retry sync");
        }
    } catch (e) {
        toast.error("Error: " + e.message);
    }
  };

  const getSyncStatusBadge = (file) => {
      if (!file.sync_status || file.sync_status === 'pending') {
          return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full flex items-center space-x-1" title="Pending Sync"><span>Pending</span></span>;
      }
      if (file.sync_status === 'in_processing') {
          return <button onClick={(e) => { e.stopPropagation(); forceRetrySync(file.id); }} className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full flex items-center space-x-1 cursor-pointer hover:bg-yellow-200 transition-colors border border-yellow-200 shadow-sm" title="Syncing... Click to force retry if stuck"><Loader2 size={12} className="animate-spin" /><span>Syncing...</span></button>;
      }
      if (file.sync_status === 'synced') {
          return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full flex items-center space-x-1" title="Synced to Master File"><span>Synced</span></span>;
      }
      if (file.sync_status === 'rejected') {
          const err = (file.sync_error || "Unknown Error");
          return <button onClick={(e) => { e.stopPropagation(); forceRetrySync(file.id); }} className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full flex items-center space-x-1 cursor-pointer hover:bg-red-200 transition-colors border border-red-200 shadow-sm" title={`Sync Failed: ${err} - Click to retry`}><span>Rejected - Retry ⟳</span></button>;
      }
      return null;
  };

  const getSyncStatusMessage = (file) => {
      if (!file.sync_status || file.sync_status === 'pending') return 'Pending Sync';
      if (file.sync_status === 'in_processing') return 'Syncing...';
      if (file.sync_status === 'synced') return 'Synced to Master File';
      if (file.sync_status === 'rejected') return `Sync Failed: ${file.sync_error || "Unknown Error"}`;
      return '';
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (!selectedFiles.length) return;

    for (const file of selectedFiles) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('folder_id', id);
        
        const uploadProcess = async () => {
          try {
            const res = await apiCallForm('/upload', formData);
            
            // Handle soft errors returned as 200 OK
            if (res && res.success === false && res.error_code === 'file_exists') {
              // Use a non-blocking toast for replacement
              toast.warning(`File already exists: ${file.name}`, {
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
                      loading: `Replacing ${file.name}...`,
                      success: () => {
                        fetchFolderData();
                        fetchFiles();
                        if (fetchNotifications) fetchNotifications();
                        return `${file.name} replaced successfully!`;
                      },
                      error: (err) => err.message || `Failed to replace ${file.name}`
                    });
                  }
                },
                cancel: {
                  label: "Cancel",
                  onClick: () => toast.info(`Upload cancelled for ${file.name}`)
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
          success: (res) => {
            fetchFolderData();
            fetchFiles();
            if (fetchNotifications) fetchNotifications();
            return `${file.name} successfully verified and saved to master!`;
          },
          error: (err) => {
            if (err.message === 'SILENT_CONFLICT') {
              return `Please confirm replacement for ${file.name}.`;
            }
            if (fetchNotifications) fetchNotifications();
            return `Upload rejected for ${file.name}: ${err.message}`;
          }
        });
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const toggleMasterSelection = (rowId) => {
    const newSet = new Set(selectedMaster);
    if (newSet.has(rowId)) newSet.delete(rowId);
    else newSet.add(rowId);
    setSelectedMaster(newSet);
  };

  const toggleSelectAllMaster = () => {
    if (masterRows.length > 0 && selectedMaster.size === masterRows.length) {
      setSelectedMaster(new Set());
    } else {
      setSelectedMaster(new Set(masterRows.map(r => r._row_fp)));
    }
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* Upload Zone */}
        <div 
          onClick={handleUploadClick}
          className="glass-card rounded-2xl p-8 border-2 border-dashed border-blue-300 dark:border-blue-900/50 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-all cursor-pointer group flex flex-col items-center justify-center text-center h-[300px]"
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
            multiple
          />
        </div>

        {/* File Manager */}
        <div className="glass-card rounded-2xl flex flex-col h-[300px]">
          <div className="p-4 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50 shrink-0">
            <h3 className="text-sm font-bold text-gray-900 dark:text-white flex items-center">
               File Manager
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {files.length === 0 ? (
               <p className="text-gray-500 text-sm text-center py-8">No files uploaded yet</p>
            ) : (
               files.map(file => {
                   const formatFileSize = (bytes) => {
                       if (bytes === 0) return '0 Bytes';
                       const k = 1024;
                       const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                       const i = Math.floor(Math.log(bytes) / Math.log(k));
                       return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
                   };
                   const rowsInfo = (file.rejected_artefact_rows != null && file.rejected_artefact_total != null)
                     ? ` (${file.rejected_artefact_rows}/${file.rejected_artefact_total} rows flagged)`
                     : '';
                   const host = API_BASE_URL.replace('/api', '');
                   const fullDownloadUrl = file.rejected_download_url 
                        ? (file.rejected_download_url.startsWith('http') 
                            ? file.rejected_download_url 
                            : `${host}${file.rejected_download_url}`)
                        : '';

                   return (
                     <div key={file.id} className="file-row flex flex-col space-y-2 p-3 rounded-lg border border-gray-100 dark:border-zinc-800 hover:border-gray-200 dark:hover:border-zinc-700 transition-all bg-white dark:bg-zinc-900/50">
                        <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{file.original_name}</p>
                                <div className="flex flex-wrap items-center gap-2 mt-1">
                                    <p className="text-xs text-gray-500">{formatFileSize(file.size)} • {file.sheet_count} sheets</p>
                                    {getSyncStatusBadge(file)}
                                </div>
                                <p className="text-xs text-gray-400 mt-1">Uploaded by: {file.uploaded_by_name || 'System'}</p>
                                <p className="text-xs text-gray-500 mt-0.5 truncate" title={getSyncStatusMessage(file)}>Status Info: {getSyncStatusMessage(file)}</p>
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          {file.rejected_artefact_id && file.rejected_download_url && (
                              <a href={fullDownloadUrl} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center space-x-1 px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors w-fit">
                                  <Download size={14} />
                                  <span>Download Rejected Rows {rowsInfo}</span>
                              </a>
                          )}
                          <button onClick={() => handleViewFile(file.id)} className="inline-flex items-center justify-center space-x-1 px-3 py-1.5 text-xs font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded-lg border border-blue-200 dark:border-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors w-fit">
                            <Eye size={14} />
                            <span>View Details</span>
                          </button>
                          <button onClick={() => handleDeleteFile(file.id)} className="inline-flex items-center justify-center space-x-1 px-3 py-1.5 text-xs font-medium bg-gray-50 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 rounded-lg border border-gray-200 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors w-fit">
                            <Trash2 size={14} />
                            <span>Delete</span>
                          </button>
                        </div>
                     </div>
                   );
               })
            )}
          </div>
        </div>
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
                  <input 
                    type="checkbox" 
                    checked={masterRows.length > 0 && selectedMaster.size === masterRows.length}
                    onChange={toggleSelectAllMaster}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 dark:bg-zinc-700 dark:border-zinc-600 cursor-pointer"
                  />
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

      {/* File Details Modal */}
      <AnimatePresence>
        {isFileDetailsModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-card rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]"
            >
              <div className="px-6 py-4 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50 flex justify-between items-center shrink-0">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center">
                  <FileSpreadsheet className="mr-2 text-blue-500" size={20} /> File Details
                </h3>
                <button
                  onClick={() => setIsFileDetailsModalOpen(false)}
                  className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 dark:hover:bg-zinc-800 transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-6 overflow-y-auto">
                {selectedFileDetails && selectedFileDetails.length > 0 ? (
                  <div className="grid gap-4">
                    {selectedFileDetails.map((sheet, i) => (
                      <div key={i} className="flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-zinc-800 bg-white dark:bg-zinc-900/50">
                        <div className="font-medium text-gray-900 dark:text-white">{sheet.name}</div>
                        <div className="flex space-x-6 text-sm text-gray-500 dark:text-gray-400">
                          <span className="flex flex-col items-center">
                            <span className="font-bold text-gray-700 dark:text-gray-300">{sheet.rows}</span>
                            <span>Rows</span>
                          </span>
                          <span className="flex flex-col items-center">
                            <span className="font-bold text-gray-700 dark:text-gray-300">{sheet.columns}</span>
                            <span>Columns</span>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No details available.</p>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
