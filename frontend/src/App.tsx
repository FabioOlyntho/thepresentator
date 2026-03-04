import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Generate from './pages/Generate';
import JobDetail from './pages/JobDetail';
import Translate from './pages/Translate';
import History from './pages/History';
import BrandKits from './pages/BrandKits';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/generate" element={<Generate />} />
        <Route path="/jobs/:jobId" element={<JobDetail />} />
        <Route path="/translate" element={<Translate />} />
        <Route path="/history" element={<History />} />
        <Route path="/brands" element={<BrandKits />} />
      </Route>
    </Routes>
  );
}
