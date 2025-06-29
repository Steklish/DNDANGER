document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('character-creation-form');
    const createCharacterBtn = document.getElementById('create-character-btn');
    const btnText = createCharacterBtn.querySelector('.btn-text');
    const btnLoader = createCharacterBtn.querySelector('.btn-loader');
    
    const pointsRemainingEl = document.getElementById('points-remaining');
    const sliders = document.querySelectorAll('.stat-slider');
    const backToLoginBtn = document.getElementById('back-to-login');
    const messageContainer = document.getElementById('message-container');
    const loadingContainer = document.getElementById('loading-container');

    // --- FIX: Get computed color values from CSS variables ---
    const rootStyles = getComputedStyle(document.documentElement);
    const colorDamage = rootStyles.getPropertyValue('--color-damage').trim();
    const colorHeal = rootStyles.getPropertyValue('--color-heal').trim();
    const colorMid = rootStyles.getPropertyValue('--text-secondary').trim();
    const colorBgDark = rootStyles.getPropertyValue('--bg-dark').trim();

    const initialPoints = 8;
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
            
            let trackColorVar;
            if (currentValue < 9) {
                trackColorVar = 'var(--color-damage)';
            } else if (currentValue > 11) {
                trackColorVar = 'var(--color-heal)';
            } else {
                trackColorVar = 'var(--text-secondary)';
            }
            
            
            // Set the CSS variables on the slider element
            slider.parentElement.style.setProperty('border-color', trackColorVar);
        });
        
        if (pointsRemaining < 0) {
            createCharacterBtn.disabled = true;
            pointsRemainingEl.style.color = 'var(--color-damage)';
        } else {
            createCharacterBtn.disabled = false;
            pointsRemainingEl.style.color = 'var(--text-primary)';
        }
    };

    

    sliders.forEach(slider => {
        slider.addEventListener('input', (e) => {
            const stat = e.target.dataset.stat;
            const newValue = parseInt(e.target.value, 10);
            const oldValue = stats[stat];
            const pointsSpent = calculatePointsSpent();
            const cost = newValue - oldValue;

            if (cost > (initialPoints - pointsSpent)) {
                e.target.value = oldValue;
                return;
            }
            
            stats[stat] = newValue;
            document.getElementById(`${stat}-value`).textContent = newValue;
            updateUI();
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        createCharacterBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        loadingContainer.style.display = 'flex';
        showNotification('Отправка запроса...', 'info');

        const pointsSpent = calculatePointsSpent();
        if (pointsSpent > initialPoints) {
            showNotification("Вы израсходовали слишком много очков!", 'error');
            createCharacterBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
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
                showNotification('Персонаж успешно создан! Перенаправление...', 'success');
                setTimeout(() => { window.location.href = '/'; }, 2000);
            } else {
                showNotification(`Ошибка: ${responseData.detail}`, 'error');
                createCharacterBtn.disabled = false;
                btnText.style.display = 'inline';
                btnLoader.style.display = 'none';
            }
        } catch (error) {
            console.error('Failed to create character:', error);
            showNotification('Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова.', 'error');
            createCharacterBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        } finally {
            if (!createCharacterBtn.disabled) {
                 loadingContainer.style.display = 'none';
            }
        }
    });

    backToLoginBtn.addEventListener('click', () => {
        window.location.href = '/';
    });

    updateUI();
});


