

function handleFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    // Convert FormData to JSON
    const data = JSON.stringify(Object.fromEntries(formData.entries()));

    fetch(form.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: data
    })
        .then(response => {
            // First, check the response status
            switch (response.status) {
                case 200:
                    // OK - Success
                    return response.json();
                case 400:
                    // Bad Request
                    if (response.msg)
                        alert(response.msg);
                    else
                    {
                        //alert('Bad Request');
                        alert('User already exists with this email');
                    }
                    break;
                case 401:
                    if (response.msg)
                        alert(response.msg);
                    else
                    {
                        //alert('Unauthorized');
                        alert('You are not authorized. Please log in.');
                    }
                    break;
                case 500:
                    if (response.msg)
                        alert(response.msg);
                    else
                    {
                        //alert('Internal Server Error');
                        alert('Server error. Please try again later.');
                    }
                    break;
                default:
                    if (response.msg)
                        alert(response.msg);
                    else
                    {
                        //alert('An unexpected error occurred. Please try again.');
                        alert('An unexpected error occurred. Please try again.');
                    }

                    break;
            }
            // If the response is not ok and not handled by the switch, throw an error
            if (!response.ok) {
                if (response.msg)
                    alert(response.msg);
                else
                {
                    //alert('An unexpected error occurred. Please try again.');
                    alert('An unexpected error occurred. Please try again.');
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && data.redirect) {
                // Redirect if a URL is provided
                window.location.href = data.redirect;
            } else {
                // Handle no redirect with a message if available
                if (data && data.msg) {
                    alert(data.msg);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error: ${error.message}`);
        });
}


// Attach the event listener to all forms with the class 'ajax-form'
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.ajax-form').forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
});
