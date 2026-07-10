import { Link } from "react-router-dom";
import { BrainCircuit, Upload, Library, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" className="flex-shrink-0 flex items-center gap-2">
              <BrainCircuit className="h-8 w-8 text-blue-600" />
              <span className="font-bold text-xl tracking-tight text-gray-900">
                DocMind AI
              </span>
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/"
                  className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1"
                >
                  <Library className="w-4 h-4" /> Documents
                </Link>
                <Link
                  to="/upload"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-1 transition-colors"
                >
                  <Upload className="w-4 h-4" /> Upload
                </Link>
                <button
                  onClick={logout}
                  className="text-gray-500 hover:text-red-600 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1 transition-colors ml-4 border-l border-gray-200"
                >
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              </>
            ) : (
              <div className="flex items-center gap-4">
                <Link to="/login" className="text-gray-600 hover:text-blue-600 font-medium text-sm">
                  Log in
                </Link>
                <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
