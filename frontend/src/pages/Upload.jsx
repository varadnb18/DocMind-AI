import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { UploadCloud, File, X, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    validateAndSetFile(droppedFile);
  }, []);

  const handleFileInput = (e) => {
    const selectedFile = e.target.files[0];
    validateAndSetFile(selectedFile);
  };

  const validateAndSetFile = (file) => {
    setError('');
    if (file) {
      const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
      ];
      if (validTypes.includes(file.type) || file.name.endsWith('.pdf') || file.name.endsWith('.txt') || file.name.endsWith('.docx')) {
        setFile(file);
      } else {
        setError('Please upload a valid PDF, DOCX, or TXT file.');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_URL}/upload-document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.status === 'success') {
        navigate(`/document/${response.data.document_id}`);
      } else {
        setError('Upload failed. Please try again.');
        setUploading(false);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during upload.');
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">Upload Document</h2>
          <p className="mt-1 text-sm text-gray-500">Upload a PDF, Word, or Text file to start analyzing.</p>
        </div>
        
        <div className="p-6">
          {!file ? (
            <div 
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:bg-gray-50 transition-colors cursor-pointer"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-upload').click()}
            >
              <UploadCloud className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4 flex text-sm text-gray-600 justify-center">
                <span className="relative rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500">
                  <span>Upload a file</span>
                  <input id="file-upload" name="file-upload" type="file" className="sr-only" onChange={handleFileInput} accept=".pdf,.docx,.txt" />
                </span>
                <p className="pl-1">or drag and drop</p>
              </div>
              <p className="text-xs text-gray-500 mt-2">PDF, DOCX, TXT up to 10MB</p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="bg-blue-100 p-3 rounded-full">
                    <File className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                {!uploading && (
                  <button onClick={() => setFile(null)} className="text-gray-400 hover:text-red-500">
                    <X className="h-5 w-5" />
                  </button>
                )}
              </div>
              
              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="animate-spin h-4 w-4" />
                      Processing...
                    </>
                  ) : (
                    'Analyze Document'
                  )}
                </button>
              </div>
            </div>
          )}
          
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm relative">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
