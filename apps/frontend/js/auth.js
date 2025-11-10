// Authentication utilities

// API Base URL - Update this when deploying to Cloud Run
// Local development: http://localhost:8080
// Cloud Run: https://your-backend-service-url.a.run.app
const API_BASE_URL = 'https://centef-rag-api-gac7qac6jq-uc.a.run.app';

// Token management
function getToken() {
    return localStorage.getItem('auth_token');
}

function setToken(token) {
    localStorage.setItem('auth_token', token);
}

function removeToken() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
}

function getUserInfo() {
    const userStr = localStorage.getItem('user_info');
    return userStr ? JSON.parse(userStr) : null;
}

function setUserInfo(user) {
    localStorage.setItem('user_info', JSON.stringify(user));
}

function isAuthenticated() {
    return !!getToken();
}

function hasRole(role) {
    const user = getUserInfo();
    return user && user.roles && user.roles.includes(role);
}

function isAdmin() {
    return hasRole('admin');
}

// API call wrapper with authentication
async function apiCall(endpoint, method = 'GET', body = null) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const options = {
        method,
        headers,
    };
    
    if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    if (response.status === 401) {
        // Token expired or invalid
        removeToken();
        window.location.href = 'login.html';
        throw new Error('Authentication required');
    }
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `Request failed with status ${response.status}`);
    }
    
    // Return parsed JSON for successful requests
    return await response.json();
}

// Login
async function login(email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    setToken(data.access_token);
    
    // Fetch user info
    const user = await apiCall('/auth/me', 'GET');
    setUserInfo(user);
    
    return data;
}

// Logout
function logout() {
    removeToken();
    window.location.href = 'login.html';
}

// Check authentication on page load
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
    }
}

// Check admin role
function requireAdmin() {
    if (!isAdmin()) {
        showError('Access denied. Admin role required.');
        window.location.href = 'chat.html';
    }
}

// Display user info in nav
function displayUserInfo() {
    const user = getUserInfo();
    if (user) {
        const userEmailEl = document.getElementById('user-email');
        if (userEmailEl) {
            userEmailEl.textContent = user.email;
        }
        
        // Show/hide admin links
        const adminLinks = document.querySelectorAll('.admin-only');
        adminLinks.forEach(link => {
            link.style.display = isAdmin() ? 'inline' : 'none';
        });
    }
}

// Error display
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message message-error';
    errorDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'message message-success';
    successDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(successDiv, container.firstChild);
        setTimeout(() => successDiv.remove(), 5000);
    }
}

