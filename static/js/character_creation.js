document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('character-creation-form');
    const createCharacterBtn = document.getElementById('create-character-btn');
    const pointsRemainingEl = document.getElementById('points-remaining');
    const sliders = document.querySelectorAll('.stat-slider');
    const backToLoginBtn = document.getElementById('back-to-login');
    const messageContainer = document.getElementById('message-container');
    const loadingContainer = document.getElementById('loading-container');

    // Move sliders to the controls section
    const statsGrid = document.querySelector('.stats-grid');
    const statsContainer = document.querySelector('.stats-container');
    if (statsContainer) {
        statsGrid.innerHTML = statsContainer.innerHTML;
        statsContainer.remove();
    }
    
    const initialPoints = 7;
    const baseStat = 8;

    const stats = {
        strength: baseStat,
        dexterity: baseStat,
        constitution: baseStat,
        intelligence: baseStat,
        wisdom: baseStat,
        charisma: baseStat,
    };

    const calculatePointsSpent = () => {
        return Object.values(stats).reduce((total, value) => total + (value - baseStat), 0);
    };

    const updateUI = () => {
        const pointsSpent = calculatePointsSpent();
        const pointsRemaining = initialPoints - pointsSpent;
        pointsRemainingEl.textContent = pointsRemaining;

        sliders.forEach(slider => {
            const stat = slider.dataset.stat;
            const currentValue = stats[stat];
            const min = parseInt(slider.min, 10);
            const max = parseInt(slider.max, 10);
            const valuePercent = ((currentValue - min) / (max - min)) * 100;
            slider.style.background = `linear-gradient(to right, var(--primary) ${valuePercent}%, var(--bg-dark) ${valuePercent}%)`;
        });
    };

    const showMessage = (message, type) => {
        messageContainer.textContent = message;
        messageContainer.className = type;
    };

    sliders.forEach(slider => {
        slider.addEventListener('input', (e) => {
            const stat = e.target.dataset.stat;
            const newValue = parseInt(e.target.value, 10);
            const oldValue = stats[stat];
            const pointsSpent = calculatePointsSpent();
            const pointsRemaining = initialPoints - pointsSpent;
            const cost = newValue - oldValue;

            if (cost > pointsRemaining) {
                e.target.value = oldValue;
                return;
            }
            
            stats[stat] = newValue;
            document.getElementById(`${stat}-value`).textContent = newValue;
            updateUI();
        });
    });

    createCharacterBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        
        createCharacterBtn.disabled = true;
        loadingContainer.style.display = 'flex';
        showMessage('Отправка запроса...', 'info');

        const pointsSpent = calculatePointsSpent();
        if (pointsSpent > initialPoints) {
            showMessage("Вы израсходовали слишком много очков!", 'error');
            createCharacterBtn.disabled = false;
            loadingContainer.style.display = 'none';
            return;
        }

        const characterData = {
            name: document.getElementById('name').value,
            background: document.getElementById('background').value,
            inventory: document.getElementById('inventory').value,
            stats: stats
        };
        
        try {
            const response = await fetch('/create-character', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(characterData),
            });

            const responseData = await response.json();

            if (response.ok) {
                showMessage('Персонаж успешно создан! Перенаправление...', 'success');
                setTimeout(() => {
                    window.location.href = '/'; 
                }, 2000);
            } else {
                showMessage(`Ошибка: ${responseData.detail}`, 'error');
                createCharacterBtn.disabled = false;
            }
        } catch (error) {
            console.error('Failed to create character:', error);
            showMessage('Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова.', 'error');
            createCharacterBtn.disabled = false;
        } finally {
            loadingContainer.style.display = 'none';
        }
    });

    backToLoginBtn.addEventListener('click', () => {
        window.location.href = '/';
    });

    updateUI();
});

