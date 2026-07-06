import { useEffect, useState, useRef } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Database, Sun, Moon, Loader2, Bell, FileDown, CheckCircle, XCircle, Info, Trash2 } from 'lucide-react';
import { apiCall } from '../api';

export default function Layout({ theme, toggleTheme }) {
  const [folders, setFolders] = useState([]);
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState(localStorage.getItem('module_id') || '1');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  
  // Notification State
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const notifRef = useRef(null);

  useEffect(() => {
    async function fetchModules() {
      try {
        const data = await apiCall('/local-modules');
        if (data.success && data.modules) {
          setModules(data.modules);
        }
      } catch (err) {
        console.error('Failed to fetch modules', err);
      }
    }
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
    fetchModules();
    fetchFolders();
    fetchNotifications();

    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, [selectedModule]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchNotifications = async () => {
    try {
      const data = await apiCall('/notifications');
      if (data.success && data.notifications) {
        setNotifications(data.notifications);
        setUnreadCount(data.notifications.filter(n => !n.is_read).length);
      }
    } catch(e) {
      console.error(e);
    }
  };

  const markAllRead = async () => {
    try {
      await apiCall('/notifications/read-all', { method: 'POST' });
      setUnreadCount(0);
      setNotifications(notifications.map(n => ({...n, is_read: true})));
    } catch(e) {}
  };

  const markAsRead = async (id) => {
    try {
      await apiCall(`/notifications/${id}/read`, { method: 'POST' });
      setNotifications(notifications.map(n => n.id === id ? {...n, is_read: true} : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch(e) {}
  };

  const getNotificationIcon = (type) => {
    switch(type) {
      case 'duplicate_upload':
      case 'error':
        return <XCircle className="text-red-500 min-w-5 h-5" />;
      case 'upload_success':
      case 'success':
        return <CheckCircle className="text-green-500 min-w-5 h-5" />;
      default:
        return <Info className="text-blue-500 min-w-5 h-5" />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -250 }}
        animate={{ x: 0 }}
        className="w-64 flex flex-col border-r border-gray-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-xl z-20"
      >
        <div className="p-6 pb-4 flex items-center justify-between gap-2">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent whitespace-nowrap">
            User Portal
          </h1>
          
          <div className="relative group">
            <select 
              value={selectedModule} 
              onChange={(e) => {
                const newModule = e.target.value;
                localStorage.setItem('module_id', newModule);
                setSelectedModule(newModule);
                // Hard reload to completely reset state and caches across the app
                window.location.href = '/';
              }}
              className="appearance-none bg-white/40 dark:bg-zinc-800/40 hover:bg-white dark:hover:bg-zinc-800 text-xs font-semibold rounded-full pl-3 pr-7 py-1.5 border border-gray-200/50 dark:border-zinc-700/50 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-700 dark:text-gray-300 shadow-sm transition-all cursor-pointer backdrop-blur-md w-28 truncate"
            >
              {modules.length === 0 && <option value="1">E-Retail</option>}
              {modules.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-gray-500 group-hover:text-blue-500 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
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
              Master Files
            </h2>
          </div>

          {loading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="animate-spin text-gray-400" size={18} />
            </div>
          ) : folders.length === 0 ? (
            <div className="px-3 text-sm text-gray-400">No master files found.</div>
          ) : (
            folders.filter(f => f.parent_id === folders.find(r => r.name === 'Root')?.id && f.name !== 'Uploads').map((folder) => (
              <NavLink
                key={folder.id}
                to={`/folder/${folder.id}`}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors text-sm ${
                    isActive
                      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 font-medium border border-purple-200 dark:border-purple-800/50'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                  }`
                }
              >
                <Database size={16} />
                <span className="truncate leading-tight font-medium">{folder.name.replace('Validation', '').replace('Folder', '').replace('-', '').trim()} Master</span>
              </NavLink>
            ))
          )}
        </nav>

        {/* Footer / Theme Toggle */}
        <div className="p-4 border-t border-gray-200 dark:border-zinc-800 space-y-2">
          <NavLink
            to="/recycle-bin"
            className={({ isActive }) =>
              `flex w-full items-center justify-between px-3 py-2 text-sm rounded-lg transition-colors ${
                isActive
                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
              }`
            }
          >
            <span className="font-medium">Recycle Bin</span>
            <Trash2 size={16} />
          </NavLink>
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
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        
        {/* Top Floating Header for Notifications */}
        <div className="absolute top-8 right-8 z-50">
           <div className="relative" ref={notifRef}>
             <button 
               onClick={() => setShowNotifications(!showNotifications)}
               className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-zinc-800 transition-colors relative text-gray-600 dark:text-gray-300"
             >
               <Bell size={20} />
               {unreadCount > 0 && (
                 <span className="absolute top-1.5 right-2 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-zinc-50 dark:border-zinc-950"></span>
               )}
             </button>

             <AnimatePresence>
               {showNotifications && (
                 <motion.div 
                   initial={{ opacity: 0, y: 10, scale: 0.95 }}
                   animate={{ opacity: 1, y: 0, scale: 1 }}
                   exit={{ opacity: 0, y: 10, scale: 0.95 }}
                   className="absolute right-0 mt-2 w-80 max-h-[32rem] overflow-hidden bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-zinc-800 flex flex-col z-50"
                 >
                   <div className="p-4 border-b border-gray-100 dark:border-zinc-800 flex justify-between items-center bg-gray-50/50 dark:bg-zinc-900/50">
                     <h3 className="font-bold text-gray-900 dark:text-white">Notifications</h3>
                     {unreadCount > 0 && (
                       <button onClick={markAllRead} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                         Mark all read
                       </button>
                     )}
                   </div>
                   
                   <div className="overflow-y-auto flex-1 p-2">
                     {notifications.length === 0 ? (
                       <div className="p-4 text-center text-sm text-gray-500">No new notifications.</div>
                     ) : (
                       notifications.map(notif => (
                         <div 
                           key={notif.id} 
                           onClick={() => !notif.is_read && markAsRead(notif.id)}
                           className={`p-3 mb-1 rounded-xl transition-colors cursor-pointer flex gap-3 ${notif.is_read ? 'opacity-70 hover:bg-gray-50 dark:hover:bg-zinc-800/50' : 'bg-blue-50/50 dark:bg-blue-900/20 hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
                         >
                           <div className="pt-0.5">
                             {getNotificationIcon(notif.type)}
                           </div>
                           <div className="flex-1 min-w-0">
                             <p className="text-sm text-gray-800 dark:text-gray-200 break-words">{notif.message}</p>
                             <span className="text-xs text-gray-400 mt-1 block">
                               {new Date(notif.created_at).toLocaleString()}
                             </span>
                             {notif.type === 'duplicate_upload' && notif.link && (
                               <a 
                                 href={notif.link}
                                 target="_blank"
                                 rel="noreferrer"
                                 className="mt-2 inline-flex items-center space-x-1 px-2.5 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 text-xs font-medium rounded-md hover:bg-red-200 transition-colors"
                                 onClick={e => e.stopPropagation()}
                               >
                                 <FileDown size={14} />
                                 <span>Download Original File</span>
                               </a>
                             )}
                           </div>
                         </div>
                       ))
                     )}
                   </div>
                 </motion.div>
               )}
             </AnimatePresence>
           </div>
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-hidden flex flex-col bg-gray-50/50 dark:bg-[#0a0a0a]">
          <Outlet context={{ theme, folders, fetchNotifications }} />
        </main>
      </main>
    </div>
  );
}
