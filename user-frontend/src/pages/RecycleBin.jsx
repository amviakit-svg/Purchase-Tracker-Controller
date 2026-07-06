import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trash2, RotateCcw, CheckSquare, Loader2 } from 'lucide-react';
import { apiCall } from '../api';
import { toast } from 'sonner';

export default function RecycleBin() {
  const [items, setItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await apiCall(`/recycle-bin?t=${Date.now()}`, { skipCache: true, cache: 'no-store' });
      setItems(data?.items || []);
      setSelectedItems(new Set());
    } catch (error) {
      toast.error(error.message || 'Failed to fetch recycle bin');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const toggleSelection = (id) => {
    const newSelection = new Set(selectedItems);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedItems(newSelection);
  };

  const toggleSelectAll = () => {
    if (selectedItems.size === items.length && items.length > 0) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(items.map(i => i.id)));
    }
  };

  const handleRestore = async () => {
    if (selectedItems.size === 0) return;
    try {
      for (const id of selectedItems) {
        const res = await apiCall(`/recycle-bin/${id}/restore`, { method: 'POST' });
        if (res && res.success === false) {
          throw new Error(res.error || res.message || 'Failed to restore item');
        }
      }
      toast.success('Restored selected items');
      fetchItems();
    } catch (error) {
      toast.error(error.message || 'Error restoring items');
      fetchItems();
    }
  };

  const handlePermanentDelete = async () => {
    if (selectedItems.size === 0) return;
    if (!window.confirm('Are you sure you want to permanently delete these items? This cannot be undone.')) {
      return;
    }
    try {
      for (const id of selectedItems) {
        const res = await apiCall(`/recycle-bin/${id}/permanent-delete`, { method: 'DELETE' });
        if (res && res.success === false) {
          throw new Error(res.error || res.message || 'Failed to delete item');
        }
      }
      toast.success('Permanently deleted selected items');
      fetchItems();
    } catch (error) {
      toast.error(error.message || 'Error deleting items');
      fetchItems();
    }
  };

  return (
    <div className="p-8 pb-32 max-w-7xl mx-auto h-full flex flex-col min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
            <Trash2 className="mr-3 text-red-500" size={32} />
            Recycle Bin
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Manage your deleted files and records here.</p>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-8 flex-1 flex flex-col">
        <div className="p-6 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50 flex justify-between items-center shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {selectedItems.size} selected
            </span>
            {selectedItems.size > 0 && (
              <>
                <button 
                  onClick={handleRestore}
                  className="flex items-center px-3 py-1.5 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors border border-green-200 dark:border-green-900/30 ml-2"
                >
                  <RotateCcw size={14} className="mr-1.5" /> Restore
                </button>
                <button 
                  onClick={handlePermanentDelete}
                  className="flex items-center px-3 py-1.5 bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors border border-red-200 dark:border-red-900/30 ml-2"
                >
                  <Trash2 size={14} className="mr-1.5" /> Delete Permanently
                </button>
              </>
            )}
          </div>
        </div>

        <div className="overflow-x-auto flex-1">
          {loading ? (
            <div className="flex justify-center items-center h-48">
              <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
            </div>
          ) : (
            <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
              <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-800/80 dark:text-gray-400 sticky top-0 z-10 shadow-sm">
                <tr>
                  <th className="px-4 py-3 w-12 text-center bg-gray-50 dark:bg-zinc-800">
                    <input 
                      type="checkbox" 
                      checked={items.length > 0 && selectedItems.size === items.length}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 dark:bg-zinc-700 dark:border-zinc-600 cursor-pointer"
                    />
                  </th>
                  <th className="px-4 py-3 bg-gray-50 dark:bg-zinc-800">Entity Name</th>
                  <th className="px-4 py-3 bg-gray-50 dark:bg-zinc-800">Type</th>
                  <th className="px-4 py-3 bg-gray-50 dark:bg-zinc-800">Deleted By</th>
                  <th className="px-4 py-3 bg-gray-50 dark:bg-zinc-800">Deleted At</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-12 text-center text-gray-500">Recycle bin is empty</td>
                  </tr>
                ) : (
                  items.map(item => (
                    <tr key={item.id} className="border-b border-gray-100 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800/30 transition-colors cursor-pointer" onClick={() => toggleSelection(item.id)}>
                      <td className="px-4 py-3 text-center" onClick={e => e.stopPropagation()}>
                        <input 
                          type="checkbox" 
                          checked={selectedItems.has(item.id)}
                          onChange={() => toggleSelection(item.id)}
                          className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 dark:bg-zinc-700 dark:border-zinc-600 cursor-pointer"
                        />
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{item.entity_name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          item.entity_type === 'file' 
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' 
                            : 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300'
                        }`}>
                          {item.entity_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">{item.deleted_by_name || 'System'}</td>
                      <td className="px-4 py-3">{new Date(item.deleted_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </motion.div>
    </div>
  );
}
