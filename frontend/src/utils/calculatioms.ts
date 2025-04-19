/**
 * Utility functions for various calculations used throughout the application
 */

/**
 * Determines the current fantasy football season year
 * - If we're in or after September, we're projecting for next year's season
 * - Otherwise we're projecting for the current year
 * This accounts for the NFL season schedule where the draft happens in April/May
 * but the season runs from September to January of the following year
 */
export const getCurrentSeasonYear = (): number => {
  const currentDate = new Date();
  let seasonYear = currentDate.getFullYear();
  
  // If we're past August (month 8 when 0-indexed), we're projecting for next season
  if (currentDate.getMonth() >= 8) {
    seasonYear += 1;
  }
  
  return seasonYear;
};

/**
 * Calculate fantasy points in half-PPR format
 * @param stats Object containing player statistics
 */
export const calculateHalfPPR = (stats: Record<string, number>): number => {
  let points = 0;
  
  // Passing points
  points += (stats.pass_yards || 0) * 0.04; // 1 point per 25 yards
  points += (stats.pass_td || 0) * 4;       // 4 points per TD
  points -= (stats.interceptions || 0) * 2; // -2 points per INT
  
  // Rushing points
  points += (stats.rush_yards || 0) * 0.1;  // 1 point per 10 yards
  points += (stats.rush_td || 0) * 6;       // 6 points per TD
  
  // Receiving points
  points += (stats.receptions || 0) * 0.5;  // 0.5 points per reception (half PPR)
  points += (stats.rec_yards || 0) * 0.1;   // 1 point per 10 yards
  points += (stats.rec_td || 0) * 6;        // 6 points per TD
  
  // Deductions
  points -= (stats.fumbles_lost || 0) * 2;  // -2 points per fumble lost
  
  return Math.round(points * 10) / 10; // Round to 1 decimal place
};

/**
 * Calculate percent change between two values
 * @param newValue The new value
 * @param oldValue The original value
 * @returns Percentage change as a number (not multiplied by 100)
 */
export const percentChange = (newValue: number, oldValue: number): number => {
  // Ensure we have valid numbers
  if (newValue === null || newValue === undefined) newValue = 0;
  if (oldValue === null || oldValue === undefined) oldValue = 0;
  if (oldValue === 0) return 0;
  
  return ((newValue - oldValue) / oldValue);
};