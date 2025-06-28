const adminButton = document.getElementById('adminButton');
const createCharacterButton = document.getElementById('createCharacterButton');
const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('username');

// Handler for the admin button
adminButton.addEventListener('click', function() {
    localStorage.setItem('playerName', 'admin');
    window.location.href = '/admin';
});

// Handler for the create character button
createCharacterButton.addEventListener('click', function() {
    window.location.href = '/character-creation';
});

// Handler for the player login form
loginForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const username = usernameInput.value.trim();
    if (username) {
        localStorage.setItem('playerName', username);
        window.location.href = `/player/${username}`;
    }
});
