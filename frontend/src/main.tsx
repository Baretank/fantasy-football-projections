import React from 'react'
import ReactDOM from 'react-dom/client'
import Routes from './routes'
import './style.css'

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <Routes />
  </React.StrictMode>,
)