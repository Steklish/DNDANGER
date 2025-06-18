const adminButton = document.getElementById('adminButton');
        const loginForm = document.getElementById('loginForm');
        const usernameInput = document.getElementById('username');

        // Обработчик для кнопки админа
        adminButton.addEventListener('click', function() {
            localStorage.setItem('playerName', 'admin');
            window.location.href = '/observer';
        });

        // Обработчик для формы игрока
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const username = usernameInput.value.trim();
            if (username) {
                localStorage.setItem('playerName', username);
                window.location.href = `/player/${username}`;
            }
        });