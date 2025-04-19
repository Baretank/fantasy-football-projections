import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSeason } from '@/context/SeasonContext';
import { Label } from '@/components/ui/label';

interface SeasonSelectorProps {
  label?: string;
  className?: string;
}

export const SeasonSelector: React.FC<SeasonSelectorProps> = ({ 
  label = "Season", 
  className = "" 
}) => {
  const { season, setSeason, availableSeasons } = useSeason();

  return (
    <div className={`space-y-2 ${className}`}>
      {label && <Label>{label}</Label>}
      <Select 
        value={season.toString()} 
        onValueChange={(value) => setSeason(parseInt(value, 10))}
      >
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="Season" />
        </SelectTrigger>
        <SelectContent>
          {availableSeasons.map((year) => (
            <SelectItem key={year} value={year.toString()}>
              {year}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};

export default SeasonSelector;