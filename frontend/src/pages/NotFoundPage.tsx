import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ExclamationTriangleIcon, HomeIcon } from '@heroicons/react/24/outline';

const NotFoundPage: React.FC = () => {
  return (
    <div className="container mx-auto flex items-center justify-center min-h-[70vh]">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center p-8 text-center">
          <ExclamationTriangleIcon className="h-16 w-16 text-yellow-500 mb-6" />
          <h1 className="text-4xl font-bold mb-2">404</h1>
          <h2 className="text-xl mb-4">Page Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The page you are looking for doesn't exist or has been moved.
          </p>
          <Button asChild>
            <Link to="/">
              <HomeIcon className="h-4 w-4 mr-2" />
              Return to Dashboard
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotFoundPage;