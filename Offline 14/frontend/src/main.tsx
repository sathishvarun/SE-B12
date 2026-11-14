import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// Load translations before any component renders.
import '@/i18n'
import App from '@/App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
