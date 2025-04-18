import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './card';
import { Button } from './button';
import { Logger } from '@/utils/logger';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to the console
    Logger.error('Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <Card className="w-full max-w-md mx-auto my-8 border-red-200">
          <CardHeader className="bg-red-50">
            <CardTitle className="text-red-800">Something went wrong</CardTitle>
            <CardDescription className="text-red-600">
              An error occurred in this component
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground mb-4">
              <p className="font-medium text-red-700 mb-2">{this.state.error?.toString()}</p>
              {this.state.errorInfo && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
                    Show stack trace
                  </summary>
                  <pre className="mt-2 p-2 bg-slate-100 rounded-md overflow-auto text-xs">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex justify-end gap-2 border-t pt-4">
            <Button variant="outline" onClick={this.resetError}>
              Try Again
            </Button>
            <Button onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </CardFooter>
        </Card>
      );
    }

    // If no error, render children normally
    return this.props.children;
  }
}

export { ErrorBoundary };