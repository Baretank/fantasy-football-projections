import React from 'react'
import ReactDOM from 'react-dom/client'
import ProjectionApp from './ProjectionApp'
import './style.css'

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <ProjectionApp />
  </React.StrictMode>,
)