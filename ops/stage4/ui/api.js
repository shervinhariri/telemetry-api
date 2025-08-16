// Global API fetch wrapper with authentication
const API_BASE = window.__API_BASE__ || '/v1';

async function apiFetch(path, init = {}) {
    // Prepend API_BASE if path starts with "/"
    const fullPath = path.startsWith('/') ? `${API_BASE}${path}` : path;
    
    // Get API key from localStorage
    const apiKey = localStorage.getItem('telemetry_api_key') || '';
    
    // Prepare headers
    const headers = {
        'Accept': 'application/json',
        ...init.headers
    };
    
    // Add Authorization header for all endpoints except health and docs
    if (apiKey && !path.endsWith('/health') && !path.includes('/docs') && init.method !== 'OPTIONS') {
        headers['Authorization'] = `Bearer ${apiKey}`;
    }
    
    // Make the request
    const response = await fetch(fullPath, {
        ...init,
        headers
    });
    
    // Handle errors
    if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
            const errorBody = await response.json();
            if (errorBody.detail) {
                errorMessage = errorBody.detail;
            }
        } catch (e) {
            // Ignore JSON parse errors, use default message
        }
        
        // Show toast for 401 errors
        if (response.status === 401) {
            showToast('Invalid API key. Please check your key and try again.', 'error');
        }
        
        throw new Error(errorMessage);
    }
    
    return response;
}

// Toast notification helper
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#fee2e2' : '#dbeafe'};
        color: ${type === 'error' ? '#991b1b' : '#1e40af'};
        padding: 12px 16px;
        border-radius: 8px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// Export for use in other scripts
window.apiFetch = apiFetch;
window.showToast = showToast;
