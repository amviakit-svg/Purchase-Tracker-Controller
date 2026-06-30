import { useEffect, useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LayoutDashboard, Folder, Sun, Moon, Loader2 } from 'lucide-react';
import { apiCall } from '../api';

export default function Layout({ theme, toggleTheme }) {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchFolders() {
      try {
        const data = await apiCall('/folders');
        if (data.success && data.folders) {
          setFolders(data.folders);
        }
      } catch (err) {
        console.error('Failed to fetch folders', err);
      } finally {
        setLoading(false);
      }
    }
    fetchFolders();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -250 }}
        animate={{ x: 0 }}
        className="w-64 flex flex-col border-r border-gray-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-xl"
      >
        <div className="p-6">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            User Portal
          </h1>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-2 space-y-1">
          <NavLink
            to="/recon"
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
              }`
            }
          >
            <LayoutDashboard size={18} />
            <span>Run Recon</span>
          </NavLink>

          <div className="pt-6 pb-2">
            <h2 className="text-xs font-semibold text-gray-400 dark:text-zinc-500 uppercase tracking-wider px-3">
              Folders
            </h2>
          </div>

          {loading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="animate-spin text-gray-400" size={18} />
            </div>
          ) : folders.length === 0 ? (
            <div className="px-3 text-sm text-gray-400">No folders available</div>
          ) : (
            folders.map((folder) => (
              <NavLink
                key={folder.id}
                to={`/folder/${folder.id}`}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                    isActive
                      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 font-medium'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                  }`
                }
              >
                <Folder size={16} />
                <span className="truncate">{folder.name}</span>
              </NavLink>
            ))
          )}
        </nav>

        {/* Footer / Theme Toggle */}
        <div className="p-4 border-t border-gray-200 dark:border-zinc-800">
          <button
            onClick={toggleTheme}
            className="flex w-full items-center justify-between px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <span className="font-medium">Theme</span>
            {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-0">
        <Outlet />
      </main>
    </div>
  );
}
