import React from 'react'
import ReactDOM from 'react-dom/client'
import Routes from './routes'
import './style.css'

// Set up the theme before rendering
const initializeTheme = () => {
  // Check for a stored theme preference
  const storedTheme = localStorage.getItem('theme');
  
  // Always default to dark unless explicitly set to light
  if (storedTheme === 'light') {
    document.documentElement.classList.remove('dark');
    console.log('Theme initialized to: light (from localStorage)');
  } else {
    // Ensure dark mode is set
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
    console.log('Theme initialized to: dark (default)');
  }
};

// Run theme initialization
initializeTheme();

// Set up a listener to detect changes to localStorage from other tabs
window.addEventListener('storage', (event) => {
  if (event.key === 'theme') {
    console.log('Theme changed in another tab to:', event.newValue);
    if (event.newValue === 'light') {
      document.documentElement.classList.remove('dark');
    } else {
      document.documentElement.classList.add('dark');
    }
  }
});

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <Routes />
  </React.StrictMode>,
)