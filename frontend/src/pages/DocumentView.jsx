import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Send, Bot, User, Loader2, Sparkles, BookOpen } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function DocumentView() {
  const { id } = useParams();
  const [query, setQuery] = useState('');
  const [chat, setChat] = useState([]);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [historyRes, summaryRes] = await Promise.allSettled([
          axios.get(`${API_URL}/documents/${id}/history`),
          axios.get(`${API_URL}/documents/${id}/summary`)
        ]);

        if (historyRes.status === 'fulfilled' && Array.isArray(historyRes.value.data)) {
          setChat(historyRes.value.data);
        }
        if (summaryRes.status === 'fulfilled' && summaryRes.value.data?.summary) {
          setSummary(summaryRes.value.data.summary);
        }
      } catch (error) {
        console.error("Failed to load document data:", error);
      }
    };
    fetchData();
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = query.trim();
    setQuery('');
    setChat(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/query`, {
        query: userMessage,
        top_k: 5,
        document_id: parseInt(id)
      });
      
      setChat(prev => [...prev, { 
        role: 'bot', 
        content: response.data.answer,
        provider: response.data.provider_used,
        sources: response.data.sources 
      }]);
    } catch (error) {
      console.error(error);
      setChat(prev => [...prev, { role: 'bot', content: "Sorry, I encountered an error while processing your query.", error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center gap-3">
        <BookOpen className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-gray-800">Document Q&A</h2>
        <span className="text-xs bg-white border border-gray-200 px-2 py-1 rounded-full text-gray-500">Doc ID: {id}</span>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {summary && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-5 text-sm text-gray-700 shadow-sm">
            <div className="flex items-center gap-2 font-semibold text-blue-900 mb-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Document Overview</span>
              <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-normal ml-auto">Pre-Computed</span>
            </div>
            <p className="whitespace-pre-wrap leading-relaxed text-gray-700">{summary}</p>
          </div>
        )}

        {chat.length === 0 && !summary ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
            <Sparkles className="w-12 h-12 text-blue-300" />
            <p className="text-lg font-medium">Ask anything about this document!</p>
            <p className="text-sm">Try asking for a summary or specific details.</p>
          </div>
        ) : (
          chat.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[80%] gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-green-100 text-green-600'}`}>
                  {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>
                
                {/* Message Bubble */}
                <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`px-5 py-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-gray-100 text-gray-800 rounded-tl-none'} ${msg.error ? 'bg-red-50 text-red-600 border border-red-200' : ''}`}>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  </div>
                  
                  {/* Sources / Provider Info */}
                  {msg.role === 'bot' && !msg.error && (
                    <div className="mt-2 flex flex-col gap-1 w-full">
                      <p className="text-[10px] text-gray-400 font-medium">
                        Generated by: <span className="text-gray-500">{msg.provider}</span>
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="flex gap-4 max-w-[80%]">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
              <div className="px-5 py-3 rounded-2xl rounded-tl-none bg-gray-100 flex items-center gap-2 text-gray-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={handleQuery} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            placeholder="Ask a question..."
            className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
