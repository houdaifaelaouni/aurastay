import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import Catalogue from './pages/Catalogue';
import PropertyDetail from './pages/PropertyDetail';
import BookingStatus from './pages/BookingStatus';
import Login from './pages/Login';
import Workspace from './pages/Workspace';
import './App.css';

export default function App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<Catalogue />} />
    <Route path="/saved" element={<Catalogue savedOnly />} />
    <Route path="/stays/:id" element={<PropertyDetail />} />
    <Route path="/booking/:token" element={<BookingStatus />} />
    <Route path="/login" element={<Login />} />
    <Route path="/workspace/*" element={<Workspace />} />
    <Route path="*" element={<Catalogue />} />
  </Routes><Toaster position="bottom-right" richColors /></BrowserRouter>;
}