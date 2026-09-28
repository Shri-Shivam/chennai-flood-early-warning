import React from 'react';
import { Link } from 'react-router-dom';

const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">404 - Page Not Found</h1>
        <p className="text-lg text-gray-600 mb-6">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link 
          to="/"
          className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          Return to Homepage
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
