import React, { useState, useEffect } from 'react';
import { fileService } from '../services/api';
import './ShareModal.css';

function ShareModal({ fileId, fileName, onClose }) {
  const [password, setPassword] = useState('');
  const [expiresIn, setExpiresIn] = useState('');
  const [shares, setShares] = useState([]);
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadShares();
  }, [fileId]);

  const loadShares = async () => {
    try {
      const sharesData = await fileService.getShares(fileId);
      setShares(sharesData);
    } catch (err) {
      console.error('Failed to load shares:', err);
    }
  };

  const handleCreateShare = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const hours = expiresIn ? parseInt(expiresIn) : null;
      const share = await fileService.createShare(fileId, password, hours);
      setShareUrl(share.share_url);
      setPassword('');
      setExpiresIn('');
      await loadShares();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create share');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDeleteShare = async (shareId) => {
    if (!window.confirm('Are you sure you want to delete this share?')) return;
    
    try {
      await fileService.deleteShare(shareId);
      await loadShares();
      if (shareUrl) setShareUrl('');
    } catch (err) {
      setError('Failed to delete share');
    }
  };

  const formatExpiry = (expiresAt) => {
    if (!expiresAt) return 'Never';
    const date = new Date(expiresAt);
    const now = new Date();
    const diff = date - now;
    
    if (diff < 0) return 'Expired';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    return 'Less than 1 hour';
  };

  return (
    <div className="share-modal-overlay" onClick={onClose}>
      <div className="share-modal" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-header">
          <h2>Share "{fileName}"</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="share-modal-content">
          {error && <div className="error-message">{error}</div>}

          {shareUrl && (
            <div className="share-link-box">
              <p className="share-link-label">🎉 Share link created!</p>
              <div className="share-link-container">
                <input 
                  type="text" 
                  value={shareUrl} 
                  readOnly 
                  className="share-link-input"
                />
                <button 
                  onClick={handleCopyLink} 
                  className="copy-btn"
                >
                  {copied ? '✓ Copied!' : '📋 Copy'}
                </button>
              </div>
            </div>
          )}

          <form onSubmit={handleCreateShare} className="share-form">
            <h3>Create New Share</h3>
            
            <div className="form-group">
              <label>Password (optional)</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Leave empty for no password"
                className="form-input"
              />
              <small>Protect your share with a password</small>
            </div>

            <div className="form-group">
              <label>Expiration (optional)</label>
              <select 
                value={expiresIn} 
                onChange={(e) => setExpiresIn(e.target.value)}
                className="form-select"
              >
                <option value="">Never expires</option>
                <option value="1">1 hour</option>
                <option value="6">6 hours</option>
                <option value="24">24 hours</option>
                <option value="168">7 days</option>
                <option value="720">30 days</option>
              </select>
              <small>Link will expire after this time</small>
            </div>

            <button type="submit" disabled={loading} className="btn-create-share">
              {loading ? 'Creating...' : '🔗 Create Share Link'}
            </button>
          </form>

          {shares.length > 0 && (
            <div className="existing-shares">
              <h3>Active Shares</h3>
              <div className="shares-list">
                {shares.map((share) => (
                  <div key={share.id} className="share-item">
                    <div className="share-info">
                      <div className="share-token">
                        {share.has_password && '🔒 '}
                        {share.share_url}
                      </div>
                      <div className="share-meta">
                        <span>Created: {new Date(share.created_at).toLocaleDateString()}</span>
                        <span>Expires: {formatExpiry(share.expires_at)}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteShare(share.id)}
                      className="btn-delete-share"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ShareModal;
