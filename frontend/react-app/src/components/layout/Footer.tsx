import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-800/50 backdrop-blur-sm border-t border-gray-700/50 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center text-gray-500">
          <p className="text-sm">
            SIH26071 Flood Intelligence System &copy; {new Date().getFullYear()}
          </p>
          <p className="text-xs mt-2">
            Scientific limitations apply - see model documentation for details
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
