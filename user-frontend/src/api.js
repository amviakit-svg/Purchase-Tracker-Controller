export const API_BASE_URL = 'http://localhost:5000/api';

export async function apiCall(endpoint, options = {}) {
    let url = `${API_BASE_URL}${endpoint}`;
    const moduleId = localStorage.getItem('module_id') || "1";
    const fetchOptions = { ...options };
    if (fetchOptions.skipCache) {
        fetchOptions.cache = 'no-store';
        delete fetchOptions.skipCache;
    }

    // Always bust cache for GET requests to prevent cross-module cache pollution
    // since the browser doesn't know to Vary by X-Module-ID header
    if (!fetchOptions.method || fetchOptions.method.toUpperCase() === 'GET') {
        const separator = url.includes('?') ? '&' : '?';
        url = `${url}${separator}_t=${Date.now()}`;
    }

    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                'X-Module-ID': String(moduleId),
                ...fetchOptions.headers,
            },
            ...fetchOptions,
        });

        if (!response.ok) {
            let errorMsg = `Server error ${response.status}`;
            let errorData = null;
            try {
                errorData = await response.json();
                errorMsg = errorData.detail || errorData.message || errorData.reason || errorData.error || errorMsg;
            } catch (e) {
                const text = await response.text();
                if (text) errorMsg = text.substring(0, 100);
            }
            const error = new Error(errorMsg);
            error.data = errorData;
            error.status = response.status;
            throw error;
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Ensure FormData works correctly without Content-Type override
export async function apiCallForm(endpoint, formData) {
    const url = `${API_BASE_URL}${endpoint}`;
    const moduleId = localStorage.getItem('module_id') || "1";
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Module-ID': String(moduleId)
            },
            body: formData,
        });

        if (!response.ok) {
            let errorMsg = `Server error ${response.status}`;
            let errorData = null;
            try {
                errorData = await response.json();
                errorMsg = errorData.detail || errorData.message || errorData.reason || errorData.error || errorMsg;
            } catch (e) {
                // Ignore
            }
            const error = new Error(errorMsg);
            error.data = errorData;
            error.status = response.status;
            throw error;
        }

        return await response.json();
    } catch (error) {
        throw error;
    }
}
