import React, { useEffect, useState } from 'react';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import { Button } from './button';

export function ThemeToggle() {
  // Check if we have dark mode currently
  const isDarkMode = () => {
    return document.documentElement.classList.contains('dark');
  };

  // Initialize state based on current DOM state
  const [isDark, setIsDark] = useState<boolean>(true); // Default to true (dark)

  // On mount, sync our state with the actual DOM state
  useEffect(() => {
    setIsDark(isDarkMode());
    
    // Log initial state
    console.log("ThemeToggle mounted, current theme:", isDarkMode() ? "dark" : "light");
  }, []);

  const toggleTheme = () => {
    // Toggle the theme directly on the document element
    if (isDark) {
      // Switching to light
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      console.log("Theme toggled to: light");
    } else {
      // Switching to dark
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      console.log("Theme toggled to: dark");
    }
    
    // Update state to match new DOM state (opposite of current state)
    setIsDark(!isDark);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label="Toggle theme"
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="transition-colors duration-300"
    >
      {isDark ? (
        <SunIcon className="h-5 w-5 text-amber-300" />
      ) : (
        <MoonIcon className="h-5 w-5 text-slate-700" />
      )}
      <span className="sr-only">{isDark ? "Light mode" : "Dark mode"}</span>
    </Button>
  );
}