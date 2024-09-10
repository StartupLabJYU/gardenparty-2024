document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('.voting-image');
    const imageContainer = document.querySelector('.image-container');

    images.forEach(image => {
        image.addEventListener('click', () => handleVote(image));
    });

    function handleVote(clickedImage) {
        // Disable further clicks
        images.forEach(image => {
            image.classList.add('clicked');
            image.removeEventListener('click', handleVote);
        });

        const image1 = document.getElementById('image1');
        const image2 = document.getElementById('image2');

        // Prepare data to send
        const data = {
            img1: image1.getAttribute('data-name'),
            img2: image2.getAttribute('data-name'),
            winner: clickedImage.getAttribute('data-name')
        };

        // Send the vote to the server
        fetch('/vote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (response.ok) {
                // Request new images from the server
                return response.json();
            } else {
                throw new Error('Failed to submit vote');
            }
        })
        .then(newImages => {
            // Update images with new ones from the server
            image1.src = newImages.image1;
            image2.src = newImages.image2;

            // Re-enable clicks
            images.forEach(image => {
                image.classList.remove('clicked');
                image.addEventListener('click', () => handleVote(image));
            });
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred, please try again.');
        });
    }
});
