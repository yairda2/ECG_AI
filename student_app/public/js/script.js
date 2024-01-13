document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();
    var formData = new FormData(this);
    fetch('/login', {
        method: 'POST',
        body: formData
    }).then(response => response.text())
      .then(data => alert(data))
      .catch(error => console.error('Error:', error));
});

document.getElementById('registerForm').addEventListener('submit', function(event) {
    event.preventDefault();
    var formData = new FormData(this);
    fetch('/register', {
        method: 'POST',
        body: formData
    }).then(response => response.text())
      .then(data => alert(data))
      .catch(error => console.error('Error:', error));
});
