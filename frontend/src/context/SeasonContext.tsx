import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentSeasonYear } from '@/utils/calculatioms';

type SeasonContextType = {
  season: number;
  setSeason: (season: number) => void;
  availableSeasons: number[];
};

const SeasonContext = createContext<SeasonContextType | undefined>(undefined);

export const SeasonProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Get the current season year from our utility function
  const currentSeasonYear = getCurrentSeasonYear();
  
  // Try to load from localStorage, fall back to current season
  const [season, setSeasonState] = useState<number>(() => {
    const savedSeason = localStorage.getItem('selectedSeason');
    return savedSeason ? parseInt(savedSeason, 10) : currentSeasonYear;
  });
  
  // Define available seasons (current season and a few years back)
  const [availableSeasons, setAvailableSeasons] = useState<number[]>([
    currentSeasonYear - 2,
    currentSeasonYear - 1,
    currentSeasonYear,
  ]);
  
  // Save to localStorage when season changes
  const setSeason = (newSeason: number) => {
    setSeasonState(newSeason);
    localStorage.setItem('selectedSeason', newSeason.toString());
  };
  
  // The context value
  const contextValue: SeasonContextType = {
    season,
    setSeason,
    availableSeasons,
  };
  
  return (
    <SeasonContext.Provider value={contextValue}>
      {children}
    </SeasonContext.Provider>
  );
};

// Custom hook to use the season context
export const useSeason = (): SeasonContextType => {
  const context = useContext(SeasonContext);
  if (context === undefined) {
    throw new Error('useSeason must be used within a SeasonProvider');
  }
  return context;
};