import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { FileText, Calendar, Database, Search, Trash2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e, docId) => {
    e.preventDefault();
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await axios.delete(`${API_URL}/documents/${docId}`);
      fetchDocuments();
    } catch (error) {
      console.error('Failed to delete document:', error);
      alert('Failed to delete document');
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Your Documents</h1>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            placeholder="Search documents..."
          />
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <Database className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by uploading a new document.</p>
          <div className="mt-6">
            <Link to="/upload" className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
              Upload Document
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <Link key={doc.id} to={`/document/${doc.id}`} className="bg-white overflow-hidden shadow-sm rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer block">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <FileText className="h-8 w-8 text-blue-500" />
                  </div>
                  <div className="ml-4 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">{doc.filename}</dt>
                      <dd>
                        <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                          <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-[10px] uppercase font-bold">{doc.file_type}</span>
                          <span>•</span>
                          <span>{formatSize(doc.file_size)}</span>
                        </div>
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-5 py-3 text-xs text-gray-500 flex items-center justify-between border-t border-gray-100">
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {new Date(doc.upload_time).toLocaleDateString()}
                </div>
                <button 
                  onClick={(e) => handleDelete(e, doc.id)}
                  className="text-red-500 hover:text-red-700 p-1 hover:bg-red-100 rounded transition-colors"
                  title="Delete Document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
