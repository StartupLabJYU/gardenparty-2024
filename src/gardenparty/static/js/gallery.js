document.addEventListener('DOMContentLoaded', () => {
    const galleryContainer = document.getElementById('gallery');

    // Fetch image URLs from the server
    fetch('/get_all_images')
        .then(response => response.json())
        .then(imageUrls => {
            imageUrls.forEach(url => {
                // Create an <a> element for each image
                const link = document.createElement('a');
                link.href = url; // Set the href to the image URL
                link.target = '_blank'; // Open in a new tab
                
                // Create an <img> element
                const img = document.createElement('img');
                img.src = url;
                img.alt = 'Gallery Image';
                img.className = 'gallery-image'; // Apply CSS class for styling
                
                // Append the image to the link, and the link to the gallery
                link.appendChild(img);
                galleryContainer.appendChild(link);
            });
        })
        .catch(error => {
            console.error('Error fetching images:', error);
            alert('Failed to load images. Please try again later.');
        });
});
