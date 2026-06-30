import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import Layout from './components/Layout';
import RunRecon from './pages/RunRecon';
import FolderView from './pages/FolderView';

function App() {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <BrowserRouter>
      <Toaster theme={theme} position="top-right" richColors />
      <Routes>
        <Route path="/" element={<Layout theme={theme} toggleTheme={toggleTheme} />}>
          <Route index element={<RunRecon />} />
          <Route path="recon" element={<RunRecon />} />
          <Route path="folder/:id" element={<FolderView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
