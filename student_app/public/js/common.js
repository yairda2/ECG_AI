// common.js

// Function to handle redirection on token expiration
function handleTokenExpiration(response) {
    if (response.status === 401) {
        response.json().then(data => {
            if (data.message === 'TokenExpired') {
                alert('Your session has expired. Please log in again.');
                window.location.href = '/login';
            } else if (data.message === 'NoToken' || data.message === 'InvalidToken') {
                alert('You are not authorized. Please log in.');
                window.location.href = '/login';
            }
        });
    }
}

// Function to handle the main page button click
function handleMainpageButtonClick() {
    if (window.location.pathname === "/test") {
        if (confirm("Are you sure you want to leave the test?")) {
            fetch('/chooseModel', {
                method: 'GET',
                credentials: 'include'
            }).then(response => {
                if (!response.ok) {
                    handleTokenExpiration(response); // Check for token expiration
                } else {
                    window.location.href = '/chooseModel';
                }
            }).catch(err => console.error('Error:', err));
        }
    } else {
        fetch('/chooseModel', {
            method: 'GET',
            credentials: 'include'
        }).then(response => {
            if (!response.ok) {
                handleTokenExpiration(response); // Check for token expiration
            } else {
                window.location.href = '/chooseModel';
            }
        }).catch(err => console.error('Error:', err));
    }
}

// Function to handle the info button click
function handleInfoButtonClick() {
    fetch('/info', {
        method: 'GET',
        credentials: 'include'
    }).then(response => {
        if (!response.ok) {
            handleTokenExpiration(response); // Check for token expiration
        } else {
            window.location.href = '/info';
        }
    }).catch(err => console.error('Error:', err));
}

// Initialize buttons on page load
document.addEventListener('DOMContentLoaded', () => {
    const mainpageButton = document.getElementById('mainpageButton');
    const infoButton = document.getElementById('infoButton');

    mainpageButton.addEventListener('click', handleMainpageButtonClick);
    infoButton.addEventListener('click', handleInfoButtonClick);
});