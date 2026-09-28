import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0">
              <img 
                className="h-8 w-8 sm:h-10 sm:w-10"
                src="/assets/logo.png" 
                alt="SIH26071 Flood Intelligence"
              />
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <a 
                  href="#" 
                  className="px-3 py-2 rounded-md text-sm font-medium text-gray-400 hover:text-white hover:bg-gray-700"
                >
                  Dashboard
                </a>
                <a 
                  href="#" 
                  className="px-3 py-2 rounded-md text-sm font-medium text-gray-400 hover:text-white hover:bg-gray-700"
                >
                  About
                </a>
              </div>
            </div>
          </div>
          <div className="flex items-center">
            <div className="ml-4 flex items-center md:ml-6">
              <span className="text-sm text-gray-400">
                Last updated: {/* Will be populated from API */}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
