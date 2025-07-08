// Example: Using dynamic environment variables in a React frontend

import React, { useState } from 'react';

// Configuration component for environment variables
const EnvConfigModal = ({ isOpen, onClose, onSave, currentConfig }) => {
  const [config, setConfig] = useState(currentConfig || {});

  const handleSave = () => {
    onSave(config);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal">
      <div className="modal-content">
        <h2>Configure Environment Variables</h2>
        
        <div className="form-group">
          <label>Arize Space ID:</label>
          <input
            type="text"
            value={config.ARIZE_SPACE_ID || ''}
            onChange={(e) => setConfig({...config, ARIZE_SPACE_ID: e.target.value})}
            placeholder="Leave empty to use default"
          />
        </div>

        <div className="form-group">
          <label>Arize Model ID:</label>
          <input
            type="text"
            value={config.ARIZE_MODEL_ID || ''}
            onChange={(e) => setConfig({...config, ARIZE_MODEL_ID: e.target.value})}
            placeholder="Leave empty to use default"
          />
        </div>

        <div className="form-group">
          <label>Arize API Key:</label>
          <input
            type="password"
            value={config.ARIZE_API_KEY || ''}
            onChange={(e) => setConfig({...config, ARIZE_API_KEY: e.target.value})}
            placeholder="Leave empty to use default"
          />
        </div>

        <div className="form-group">
          <label>OpenAI API Key:</label>
          <input
            type="password"
            value={config.OPENAI_API_KEY || ''}
            onChange={(e) => setConfig({...config, OPENAI_API_KEY: e.target.value})}
            placeholder="Leave empty to use default"
          />
        </div>

        <div className="button-group">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSave} className="primary">Save</button>
        </div>
      </div>
    </div>
  );
};

// Main chat component
const ChatComponent = () => {
  const [message, setMessage] = useState('');
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [envConfig, setEnvConfig] = useState({});
  const [showConfig, setShowConfig] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'https://your-cloud-run-url';

  const sendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    const userMessage = message;
    setMessage('');

    try {
      // Build request payload
      const payload = {
        message: userMessage,
        session_id: sessionStorage.getItem('session_id') || undefined
      };

      // Add environment overrides if configured
      const activeEnvVars = Object.entries(envConfig)
        .filter(([_, value]) => value && value.trim())
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});

      if (Object.keys(activeEnvVars).length > 0) {
        payload.env_overrides = activeEnvVars;
      }

      // Send request
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Store session ID for future requests
      if (data.session_id) {
        sessionStorage.setItem('session_id', data.session_id);
      }

      // Add to responses
      setResponses([...responses, {
        user: userMessage,
        assistant: data.response,
        sources: data.sources,
        timestamp: new Date()
      }]);

    } catch (error) {
      console.error('Error sending message:', error);
      setResponses([...responses, {
        user: userMessage,
        assistant: `Error: ${error.message}`,
        error: true,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>Arize Chatbot</h1>
        <button 
          onClick={() => setShowConfig(true)}
          className="config-button"
          title="Configure environment variables"
        >
          ⚙️ Configure
        </button>
      </div>

      {/* Display active configuration */}
      {Object.keys(envConfig).some(key => envConfig[key]) && (
        <div className="config-indicator">
          Using custom environment configuration
        </div>
      )}

      <div className="chat-messages">
        {responses.map((resp, idx) => (
          <div key={idx} className="message-pair">
            <div className="user-message">
              <strong>You:</strong> {resp.user}
            </div>
            <div className={`assistant-message ${resp.error ? 'error' : ''}`}>
              <strong>Assistant:</strong> {resp.assistant}
              {resp.sources && (
                <div className="sources">
                  <em>Sources: {resp.sources.join(', ')}</em>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask a question..."
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>

      <EnvConfigModal
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        onSave={setEnvConfig}
        currentConfig={envConfig}
      />
    </div>
  );
};

// Example usage in a multi-tenant application
class MultiTenantChatService {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
  }

  async sendMessageForTenant(tenantId, message, sessionId) {
    // Get tenant-specific configuration from your backend or storage
    const tenantConfig = await this.getTenantConfig(tenantId);
    
    const payload = {
      message: message,
      session_id: sessionId,
      env_overrides: {
        ARIZE_SPACE_ID: tenantConfig.arizeSpaceId,
        ARIZE_MODEL_ID: tenantConfig.arizeModelId,
        ARIZE_API_KEY: tenantConfig.arizeApiKey,
        OPENAI_API_KEY: tenantConfig.openaiApiKey
      }
    };

    const response = await fetch(`${this.apiUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': tenantId // For additional security/logging
      },
      body: JSON.stringify(payload)
    });

    return response.json();
  }

  async getTenantConfig(tenantId) {
    // This would typically fetch from your database or configuration service
    // For example:
    return await fetch(`/api/tenants/${tenantId}/config`).then(r => r.json());
  }
}

export { ChatComponent, MultiTenantChatService };