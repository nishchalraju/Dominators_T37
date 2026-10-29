import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { KeyedActiveCase } from './components/providers/KeyedActiveCase'
import { AuthProvider } from './components/providers/AuthProvider'
import { MetaProvider } from './components/providers/MetaProvider'
import { ToastProvider } from './components/providers/ToastProvider'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <MetaProvider>
          <AuthProvider>
            <KeyedActiveCase>
              <App />
            </KeyedActiveCase>
          </AuthProvider>
        </MetaProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
)
