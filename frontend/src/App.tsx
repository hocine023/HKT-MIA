import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { UploadPage } from './pages/UploadPage';
import { CRMPage } from './pages/CRMPage';
import { CompliancePage } from './pages/CompliancePage';

function App() {
  const navClass = ({ isActive }: { isActive: boolean }) => 
    `px-5 py-2.5 rounded-lg font-bold text-sm transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 font-sans">
        <nav className="p-4 bg-white shadow-sm border-b flex gap-4 justify-center sticky top-0 z-50">
          <NavLink to="/" className={navClass}>📤 Upload & IA</NavLink>
          <NavLink to="/crm" className={navClass}>🗂️ App CRM </NavLink>
          <NavLink to="/conformite" className={navClass}>⚖️ App Conformité </NavLink>
        </nav>
        
        <main className="pt-8">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/crm" element={<CRMPage />} />
            <Route path="/conformite" element={<CompliancePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;