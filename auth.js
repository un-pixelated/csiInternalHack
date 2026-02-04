// static/auth.js

// 1. REGISTER FUNCTION
async function register(username, password) {
    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        });

        if (response.ok) {
            alert("Registration successful! You can now log in.");
        } else {
            const errorData = await response.json();
            alert("Error: " + (errorData.detail || "Registration failed"));
        }
    } catch (error) {
        console.error("Registration error:", error);
    }
}

// 2. LOGIN FUNCTION
async function login(username, password) {
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('username', username);
            alert("Login Successful!");
            window.location.href = '/difficulty.html'; 
        } else {
            const errorData = await response.json();
            alert("Login Failed: " + (errorData.detail || "Invalid credentials"));
        }
    } catch (error) {
        console.error("Login error:", error);
    }
}

// 3. LOGOUT FUNCTION
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    window.location.href = '/';
}