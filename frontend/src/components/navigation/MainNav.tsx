import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { 
  ChartBarIcon,
  UserGroupIcon,
  AdjustmentsHorizontalIcon,
  DocumentDuplicateIcon,
  BuildingLibraryIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrophyIcon
} from '@heroicons/react/24/outline';

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
  description?: string;
}

const navigation: NavItem[] = [
  {
    name: 'Dashboard',
    href: '/',
    icon: <ChartBarIcon className="h-5 w-5" />,
    description: 'Overview and analytics'
  },
  {
    name: 'Players',
    href: '/players',
    icon: <UserGroupIcon className="h-5 w-5" />,
    description: 'Player projections and stats'
  },
  {
    name: 'Scenarios',
    href: '/scenarios',
    icon: <DocumentDuplicateIcon className="h-5 w-5" />,
    description: 'What-if scenarios'
  },
  {
    name: 'Teams',
    href: '/teams',
    icon: <BuildingLibraryIcon className="h-5 w-5" />,
    description: 'Team-level adjustments'
  },
  {
    name: 'Draft Tool',
    href: '/draft',
    icon: <TrophyIcon className="h-5 w-5" />,
    description: 'NFL Draft Day operations'
  },
  {
    name: 'Compare',
    href: '/compare',
    icon: <ArrowPathIcon className="h-5 w-5" />,
    description: 'Side-by-side comparisons'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: <Cog6ToothIcon className="h-5 w-5" />,
    description: 'Application settings'
  }
];

interface MainNavProps {
  currentPath: string;
}

const MainNav: React.FC<MainNavProps> = ({ currentPath }) => {
  return (
    <nav className="flex flex-col space-y-1">
      {navigation.map((item) => {
        const isActive = currentPath === item.href || 
          (item.href !== '/' && currentPath.startsWith(item.href));
          
        return (
          <Link 
            key={item.name}
            to={item.href}
            className={`
              flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium
              ${isActive 
                ? 'bg-primary text-primary-foreground' 
                : 'hover:bg-muted text-foreground/70 hover:text-foreground'}
            `}
          >
            {item.icon}
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
};

export default MainNav;