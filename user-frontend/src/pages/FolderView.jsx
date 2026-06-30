import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { UploadCloud, Trash2, RotateCcw, Search, Download, CheckSquare } from 'lucide-react';
import { apiCall, apiCallForm } from '../api';

export default function FolderView() {
  const { id } = useParams();
  const [folderData, setFolderData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Data lists
  const [masterRows, setMasterRows] = useState([]);
  const [deletedRows, setDeletedRows] = useState([]);
  
  // Selections
  const [selectedMaster, setSelectedMaster] = useState(new Set());
  
  const fileInputRef = useRef(null);

  const fetchFolderData = async () => {
    try {
      setLoading(true);
      // Simulating endpoints for now, as backend routing is still mapped to standard API
      const meta = await apiCall(`/master/${id}`);
      setFolderData(meta.master_file || { folder_id: id, name: `Folder ${id}` });
      
      const rows = await apiCall(`/master/${id}/rows`);
      if (rows.success) setMasterRows(rows.data || []);
      
      const deleted = await apiCall(`/master/${id}/rows/deleted`);
      if (deleted.success) setDeletedRows(deleted.data || []);

    } catch (e) {
      toast.error('Failed to load folder data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFolderData();
    setSelectedMaster(new Set());
  }, [id]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    
    toast.promise(
      apiCallForm(`/uploads/${id}`, formData),
      {
        loading: `Uploading ${file.name}...`,
        success: () => {
          fetchFolderData();
          return `${file.name} uploaded and processed!`;
        },
        error: 'Upload failed'
      }
    );
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
    
    toast.promise(
      apiCall(`/master/${id}/rows/delete`, {
        method: 'POST',
        body: JSON.stringify({
          row_ids: Array.from(selectedMaster)
        })
      }),
      {
        loading: 'Deleting rows...',
        success: (data) => {
          if (!data.success) throw new Error('Deletion failed');
          setSelectedMaster(new Set());
          fetchFolderData();
          return `Successfully deleted ${selectedMaster.size} rows`;
        },
        error: 'Failed to delete rows'
      }
    );
  };

  const handleRestore = async (rowId) => {
    toast.promise(
      apiCall(`/master/${id}/rows/restore`, {
        method: 'POST',
        body: JSON.stringify({ row_ids: [rowId] })
      }),
      {
        loading: 'Restoring row...',
        success: (data) => {
          if (!data.success) {
            // Throw so the error toast handles it, this matches our deduplication rule!
            throw new Error(data.message || 'Data already exist in master file');
          }
          fetchFolderData();
          return 'Row has restored';
        },
        error: (err) => err.message
      }
    );
  };

  if (loading && !folderData) {
    return <div className="p-8 text-gray-500">Loading folder data...</div>;
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 relative">
      <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8 tracking-tight">
        {folderData?.name || `Folder ${id}`}
      </h2>

      {/* Upload Zone */}
      <div 
        onClick={handleUploadClick}
        className="glass-card rounded-2xl p-8 mb-8 border-2 border-dashed border-blue-300 dark:border-blue-900/50 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-all cursor-pointer group flex flex-col items-center justify-center text-center"
      >
        <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
          <UploadCloud size={32} />
        </div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Upload Data File</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">Click to browse or drag and drop files here</p>
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
        <div className="p-6 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center bg-gray-50/50 dark:bg-zinc-900/50">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center">
              <Table2 className="mr-2" size={20} /> Master File Data
            </h3>
            {selectedMaster.size > 0 && (
              <motion.button 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={handleBulkDelete}
                className="flex items-center px-3 py-1.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors"
              >
                <Trash2 size={16} className="mr-1" /> Delete Selected ({selectedMaster.size})
              </motion.button>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input 
                type="text" 
                placeholder="Search..." 
                className="pl-9 pr-4 py-1.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 ring-blue-500"
              />
            </div>
            <button className="flex items-center px-3 py-1.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
              <Download size={16} className="mr-2" /> Export
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-800/50 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3 w-12 text-center">
                  <CheckSquare size={16} className="text-gray-400 inline" />
                </th>
                <th className="px-4 py-3">ID</th>
                {/* Dynamic Headers would go here */}
                <th className="px-4 py-3">Data Preview</th>
              </tr>
            </thead>
            <tbody>
              {masterRows.length === 0 ? (
                <tr>
                  <td colSpan="100%" className="px-4 py-8 text-center italic text-gray-400">No active rows found.</td>
                </tr>
              ) : (
                masterRows.map(row => (
                  <tr key={row._row_id} className="border-b border-gray-100 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3 text-center">
                      <input 
                        type="checkbox" 
                        checked={selectedMaster.has(row._row_id)}
                        onChange={() => toggleMasterSelection(row._row_id)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 dark:bg-zinc-700 dark:border-zinc-600"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium">{row._row_id}</td>
                    <td className="px-4 py-3 truncate max-w-xs">{JSON.stringify(row)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Deleted Rows Preview */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50">
          <h3 className="text-sm font-bold text-gray-600 dark:text-gray-400 flex items-center">
            <Trash2 className="mr-2" size={16} /> Deleted Rows
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-800/50 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2">ID</th>
                <th className="px-4 py-2">Data</th>
                <th className="px-4 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {deletedRows.length === 0 ? (
                <tr>
                  <td colSpan="100%" className="px-4 py-4 text-center italic text-gray-400">No deleted rows.</td>
                </tr>
              ) : (
                deletedRows.map(row => (
                  <tr key={row._row_id} className="border-b border-gray-100 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800/30">
                    <td className="px-4 py-2">{row._row_id}</td>
                    <td className="px-4 py-2 truncate max-w-xs">{JSON.stringify(row)}</td>
                    <td className="px-4 py-2 text-right">
                      <button 
                        onClick={() => handleRestore(row._row_id)}
                        className="text-blue-600 hover:text-blue-800 font-medium text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded transition-colors"
                      >
                        <RotateCcw size={14} className="inline mr-1" /> Restore
                      </button>
                    </td>
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
