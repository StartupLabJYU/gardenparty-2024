document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('.voting-image');
    const imageContainer = document.querySelector('.image-container');
    const messageDiv = document.getElementById('message');
    const headline = document.getElementById('headline');
    const waitingMessage = document.getElementById('waiting-message');
    
    const FULL_DASH_ARRAY = 283;
    const TIME_LIMIT = 5;
    let timePassed = 0;
    let timeLeft = TIME_LIMIT;
    let timerInterval = null;

    if (waitingMessage) {
        // If we are in the waiting state
        startTimer(() => {
            location.reload();
        });
    } else {
        images.forEach(image => {
            image.addEventListener('click', () => handleVote(image));
        });
    }

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
            winner: clickedImage.getAttribute('data-name'),
            vote_token: document.getElementById('vote_token').value
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
                // Hide images and headline, then show the message
                imageContainer.style.display = 'none';
                headline.style.display = 'none';
                messageDiv.style.display = 'block';

                // Start countdown animation
                startTimer(() => {
                    location.reload();
                });
            } else {
                throw new Error('Failed to submit vote');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred, please try again.');
        });
    }

    function startTimer(callback) {
        timerInterval = setInterval(() => {
            timePassed += 1;
            timeLeft = TIME_LIMIT - timePassed;

            if (timeLeft === 0) {
                clearInterval(timerInterval);
                callback();
            } else {
                setCircleDasharray();
            }
        }, 1000);
    }

    function calculateTimeFraction() {
        const rawTimeFraction = timeLeft / TIME_LIMIT;
        return rawTimeFraction - (1 / TIME_LIMIT);
    }

    function setCircleDasharray() {
        const circleDasharray = `${(calculateTimeFraction() * FULL_DASH_ARRAY).toFixed(0)} 283`;
        document
            .getElementById('base-timer-path-remaining')
            .setAttribute('stroke-dasharray', circleDasharray);
    }
});
