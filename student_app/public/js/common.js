// common.js


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

// common.js

// Function to convert form data to JSON
function formToJson(form) {
    const formData = new FormData(form);
    const jsonData = {};
    formData.forEach((value, key) => {
        jsonData[key] = value;
    });
    return JSON.stringify(jsonData);
}

// Function to handle redirection on token expiration
function handleTokenExpiration(response) {
    if (response.status === 401) {
        response.json().then(data => {
            if (['TokenExpired', 'NoToken', 'InvalidToken'].includes(data.message)) {
                alert('Your session has expired or is invalid. Please log in again.');
                window.location.href = '/login';
            } else {
                alert(data.message);
            }
        });
    } else {
        response.json().then(data => alert(data.message)).catch(() => alert('An unexpected error occurred.'));
    }
}


// Function to handle page redirection or form submission
function handlePageAction(action, method, body = null) {
    const options = {
        method: method,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    fetch(action, options)
        .then(response => {
            if (!response.ok) {
                handleTokenExpiration(response);
            } else {
                response.json().then(data => {
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        alert(data.message);
                    }
                });
            }
        })
        .catch(err => console.error('Error:', err));
}

// Function to handle form submission
function handleChooseModelSubmit(event, value) {
    handlePageAction('/chooseModel', event.method, { action: value });

}
// Function to handle form submission
function handleFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const action = form.action;
    const method = form.method.toUpperCase();
    const body = formToJson(form);

    handlePageAction(action, method, JSON.parse(body));
}


// Initialize buttons and forms on page load
document.addEventListener('DOMContentLoaded', () => {
    const mainpageButton = document.getElementById('mainpageButton');
    const infoButton = document.getElementById('infoButton');
    const modelChooseForm = document.getElementById('modelChooseForm');
    const forms = document.querySelectorAll('form');

    if (mainpageButton) {
        mainpageButton.addEventListener('click', () => handlePageAction('/chooseModel', 'GET'));
    }

    if (infoButton) {
        infoButton.addEventListener('click', () => handlePageAction('/info', 'GET'));
    }

    if (modelChooseForm) {
        modelChooseForm.addEventListener('submit', event => {
            event.preventDefault();
            const action = event.submitter.value; // Using submitter to get the clicked button value
            handleChooseModelSubmit(action, 'POST');
        });
    }

    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
});

// Initialize buttons and forms on page load
    document.addEventListener('DOMContentLoaded', () => {
        const mainpageButton = document.getElementById('mainpageButton');
        const infoButton = document.getElementById('infoButton');

        if (mainpageButton) mainpageButton.addEventListener('click', () => handleFormSubmit('/chooseModel', 'GET'));
        if (infoButton) infoButton.addEventListener('click', () => handleFormSubmit('/info', 'GET'));
    });
