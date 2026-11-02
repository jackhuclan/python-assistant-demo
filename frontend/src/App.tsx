import { Route, Routes } from 'react-router-dom'
import Chat from './pages/Chat'
import AdminApp from './pages/admin/AdminApp'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Chat />} />
      <Route path="/admin/*" element={<AdminApp />} />
    </Routes>
  )
}
