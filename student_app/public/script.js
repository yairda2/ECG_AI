function fetchRandomImage() {
    fetch('/random-image')
        .then(response => response.json())
        .then(data => {
            document.getElementById('imageToClassify').src = data.imagePath;
        })
        .catch(error => console.error('Error fetching image:', error));
}

function classifyImage() {
    const imageSrc = document.getElementById('imageToClassify').src;
    const category = document.getElementById('categorySelect').value;
    fetch('/classify-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName: imageSrc.split('/').pop(), category })
    })
        .then(response => response.text())
        .then(message => {
            alert(message);
            fetchRandomImage();  // Fetch next image
        })
        .catch(error => console.error('Error classifying image:', error));
}

window.onload = fetchRandomImage;
