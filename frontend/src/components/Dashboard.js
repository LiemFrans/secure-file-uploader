import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, fileService } from '../services/api';
import './Dashboard.css';

function Dashboard() {
  const [files, setFiles] = useState([]);
  const [user, setUser] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadUser();
    loadFiles();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
    } catch (err) {
      navigate('/login');
    }
  };

  const loadFiles = async () => {
    try {
      const filesData = await fileService.getFiles();
      setFiles(filesData);
    } catch (err) {
      setError('Failed to load files');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.html')) {
      setSelectedFile(file);
      setError('');
    } else {
      setError('Please select an HTML file');
      setSelectedFile(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setUploading(true);
    setError('');
    try {
      await fileService.uploadFile(selectedFile, isLocked);
      setSelectedFile(null);
      setIsLocked(false);
      document.getElementById('file-input').value = '';
      await loadFiles();
      alert('File uploaded successfully!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleToggleLock = async (fileId, currentLockState) => {
    try {
      await fileService.updateFileLock(fileId, !currentLockState);
      await loadFiles();
    } catch (err) {
      setError('Failed to update lock status');
    }
  };

  const handleDelete = async (fileId) => {
    if (!window.confirm('Are you sure you want to delete this file?')) return;
    
    try {
      await fileService.deleteFile(fileId);
      await loadFiles();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete file');
    }
  };

  const handleView = (fileId) => {
    const url = fileService.getFileUrl(fileId);
    window.open(url, '_blank');
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>HTML Uploader</h1>
        <div className="user-info">
          <span>Welcome, {user?.username}</span>
          <button onClick={handleLogout} className="btn-secondary">Logout</button>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="upload-section">
          <h2>Upload HTML File</h2>
          {error && <div className="error-message">{error}</div>}
          <div className="upload-form">
            <input
              id="file-input"
              type="file"
              accept=".html"
              onChange={handleFileSelect}
              disabled={uploading}
            />
            <div className="lock-checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={isLocked}
                  onChange={(e) => setIsLocked(e.target.checked)}
                  disabled={uploading}
                />
                Lock file (prevent deletion)
              </label>
            </div>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="btn-primary"
            >
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>

        <div className="files-section">
          <h2>Your Files</h2>
          {files.length === 0 ? (
            <p className="no-files">No files uploaded yet</p>
          ) : (
            <div className="files-grid">
              {files.map((file) => (
                <div key={file.id} className="file-card">
                  <div className="file-header">
                    <h3>{file.original_filename}</h3>
                    <span className={`lock-badge ${file.is_locked ? 'locked' : 'unlocked'}`}>
                      {file.is_locked ? '🔒 Locked' : '🔓 Unlocked'}
                    </span>
                  </div>
                  <div className="file-info">
                    <p>Uploaded: {new Date(file.created_at).toLocaleString()}</p>
                  </div>
                  <div className="file-actions">
                    <button onClick={() => handleView(file.id)} className="btn-view">
                      View
                    </button>
                    <button
                      onClick={() => handleToggleLock(file.id, file.is_locked)}
                      className="btn-lock"
                    >
                      {file.is_locked ? 'Unlock' : 'Lock'}
                    </button>
                    <button
                      onClick={() => handleDelete(file.id)}
                      className="btn-delete"
                      disabled={file.is_locked}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
