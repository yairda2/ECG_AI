// common.js

// Function to get cookie value by name
function getCookie(name) {
    let cookieArr = document.cookie.split(";");
    for (let i = 0; i < cookieArr.length; i++) {
        let cookiePair = cookieArr[i].split("=");
        if (name === cookiePair[0].trim()) {
            return decodeURIComponent(cookiePair[1]);
        }
    }
    return null;
}

// Function to handle server responses
function handleServerResponse(response) {
    return response.json().then(data => {
        if (!response.ok) {
            if (data.message) {
                alert(data.message);
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            }
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } else if (data.redirect) {
            window.location.href = data.redirect;
        }
        return data;
    }).catch(err => {
        console.error('Error:', err);
        alert('An unexpected error occurred.');
    });
}

// Function to handle page actions
function handlePageAction(url, method, data = {}) {
    // If method is GET, remove body if method is GET
    if (method === 'GET') {
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
        })
            .then(response => handleServerResponse(response))
            .catch(err => console.error('Error:', err));
    } else if (method === 'POST') {
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(data)
        })
            .then(response => handleServerResponse(response))
            .catch(err => console.error('Error:', err));
    }
}


// Initialize buttons and forms on page load
document.addEventListener('DOMContentLoaded', () => {
    const mainpageButton = document.getElementById('mainpageButton');
    const infoButton = document.getElementById('infoButton');
    const registerButton = document.getElementById('registerButton');
    const loginButton = document.getElementById('loginButton');
    const forms = document.querySelectorAll('form');

    if (mainpageButton) {
        mainpageButton.addEventListener('click', () => handlePageAction('/main', 'GET'));
    }

    if (infoButton) {
        infoButton.addEventListener('click', () => handlePageAction('/user-data', 'GET'));
    }

    if (registerButton) {
        registerButton.addEventListener('click', () => handlePageAction('/sign-up', 'GET'));
    }

    if (loginButton) {
        loginButton.addEventListener('click', () => handlePageAction('/sign-in', 'GET'));
    }
});

// Display error message on page load
document.addEventListener("DOMContentLoaded", function () {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    if (error) {
        const errorMessage = {
            'NoToken': 'No token provided. Please log in to continue.',
            'InvalidToken': 'Your session has expired. Please log in again.'
        };
        alert(errorMessage[error] || 'An unknown error occurred.');
        window.location.href = '/login';
    }
    const success = urlParams.get('success');
    const redirect = urlParams.get('redirect');
    if (success) {
        alert(success);
        window.location.href = redirect;
    }
});
