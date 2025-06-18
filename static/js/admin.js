const adminName = localStorage.getItem('playerName');
if (adminName?.toLowerCase() !== 'admin') {
    window.location.href = '/login.html';
}

let currentTurnIndex = 0;
let initiativeOrder = [];
// Добавим объект для хранения состояния вкладок
let activeTabStates = {};

// Создаем EventSource для получения обновлений
const eventSource = new EventSource("/stream");

// Обрабатываем получаемые сообщения
eventSource.onmessage = function(event) {
    try {
        const data = JSON.parse(event.data);
        if (data.scene) {
            updateScene(data.scene);
        }
        if (data.characters) {
            updateCharacters(data.characters);
            if (initiativeOrder.length === 0) {
                updateTurnOrder(data.characters);
            }
        }
    } catch (error) {
        console.error('Update error:', error);
    }
};

// Обработка ошибок подключения
eventSource.onerror = function(error) {
    console.error("EventSource failed:", error);
    eventSource.close();
    // Попытка переподключения через 5 секунд
    setTimeout(() => {
        window.location.reload();
    }, 5000);
};

// Первоначальная загрузка данных
async function fetchUpdates() {
    try {
        const response = await fetch('/refresh');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        updateScene(data.scene);
        updateCharacters(data.characters);
        if (initiativeOrder.length === 0) {
            updateTurnOrder(data.characters);
        }
    } catch (error) {
        console.error('Fetch error:', error);
    }
}

// Загружаем начальные данные
fetchUpdates();

function updateScene(scene) {
    if (!scene) return;

    document.getElementById('sceneName').textContent = scene.name;
    document.getElementById('sceneDescription').innerHTML = marked.parse(scene.description);

    const objectsContainer = document.getElementById('sceneObjects');
    objectsContainer.innerHTML = scene.objects.map(obj => `
        <div class="scene-object">
            <h4>${obj.name}</h4>
            <p>${obj.description}</p>
            <p><small>${obj.position_in_scene}</small></p>
        </div>
    `).join('');
}

// Функция для создания безопасного ID
function makeValidId(str) {
    return str.toLowerCase().replace(/[^a-z0-9]/g, '_');
}

function updateCharacters(characters) {
    if (!characters?.length) return;

    // Сохраняем текущие активные вкладки перед обновлением
    const cards = document.querySelectorAll('.character-card');
    cards.forEach(card => {
        const charName = card.querySelector('h3').textContent;
        const charId = makeValidId(charName);
        const activeTab = card.querySelector('.tab-btn.active');
        if (activeTab) {
            const tabIndex = Array.from(card.querySelectorAll('.tab-btn')).indexOf(activeTab);
            activeTabStates[charId] = ['abilities', 'inventory', 'background'][tabIndex];
        }
    });

    const panel = document.getElementById('charactersPanel');
    panel.innerHTML = characters.map(char => {
        const charId = makeValidId(char.name);
        const activeTab = activeTabStates[charId] || 'abilities'; // По умолчанию abilities

        return `
            <div class="character-card">
                <div class="char-header">
                    <h3>${char.name}</h3>
                    <span class="char-type">${char.is_player ? 'Player' : 'NPC'}</span>
                </div>

                <div class="hp-bar">
                    <div class="hp-bar-inner" style="width: ${(char.current_hp / char.max_hp) * 100}%"></div>
                </div>
                <div class="stats-row">
                    <span class="stat-item">HP: ${char.current_hp}/${char.max_hp}</span>
                    <span class="stat-item">AC: ${char.ac}</span>
                </div>

                ${char.conditions.length ? `
                    <div class="stats-row">
                        <span class="stat-item conditions">${char.conditions.join(', ')}</span>
                    </div>
                ` : ''}

                <div class="char-tabs">
                    <button class="tab-btn ${activeTab === 'abilities' ? 'active' : ''}" 
                            onclick="showTab('${charId}', 'abilities')">Abilities</button>
                    <button class="tab-btn ${activeTab === 'inventory' ? 'active' : ''}" 
                            onclick="showTab('${charId}', 'inventory')">Inventory</button>
                    <button class="tab-btn ${activeTab === 'background' ? 'active' : ''}" 
                            onclick="showTab('${charId}', 'background')">Background</button>
                </div>

                <div id="${charId}_abilities" class="tab-content abilities-list" 
                     style="display: ${activeTab === 'abilities' ? 'block' : 'none'}">
                    <h4>Abilities</h4>
                    ${char.abilities.map(ability => `
                        <div class="ability-item">
                            <div class="ability-header">
                                <strong>${ability.name}</strong>
                            </div>
                            <p>${ability.description}</p>
                            ${ability.details ? `
                                <div class="ability-details">
                                    <em>Details:</em> ${JSON.stringify(ability.details)}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>

                <div id="${charId}_inventory" class="tab-content inventory-list" 
                     style="display: ${activeTab === 'inventory' ? 'block' : 'none'}">
                    <h4>Inventory</h4>
                    ${char.inventory.map(item => `
                        <div class="inventory-item">
                            <div class="item-header">
                                <strong class="name rarity-${item.rarity || 'Common'}">${item.name}</strong>
                                <span class="item-type">${item.item_type}</span>
                                ${item.rarity ? `<span class="rarity-${item.rarity}">(${item.rarity})</span>` : ''}
                            </div>
                            <p>${item.description}</p>
                            <div class="item-details">
                                ${item.quantity ? `<span class="item-stat">Quantity: ${item.quantity}</span>` : ''}
                                ${item.weight ? `<span class="item-stat">Weight: ${item.weight}</span>` : ''}
                                ${item.value ? `<span class="item-stat">Value: ${item.value}</span>` : ''}
                                ${item.rarity ? `<span class="item-stat">Rarity: ${item.rarity}</span>` : ''}
                                ${item.is_magical !== undefined ? `<span class="item-stat">Magical: ${item.is_magical ? 'Yes' : 'No'}</span>` : ''}
                                ${item.damage ? `<span class="item-stat">Damage: ${item.damage} (${item.damage_type})</span>` : ''}
                                ${item.armor_class ? `<span class="item-stat">AC: ${item.armor_class}</span>` : ''}
                            </div>
                            ${item.effect ? `<p class="item-effect">${item.effect}</p>` : ''}
                            ${item.properties?.length ? `
                                <div class="item-properties">
                                    <em>Properties:</em> ${item.properties.join(', ')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>

                <div id="${charId}_background" class="tab-content background-info" 
                     style="display: ${activeTab === 'background' ? 'block' : 'none'}">
                    <h4>Background & Personality</h4>
                    <p>${char.personality_history || 'No background information available.'}</p>
                </div>
            </div>
        `;
    }).join('');
}

function showTab(charId, tabName) {
    const card = document.querySelector(`.character-card:has(#${charId}_${tabName})`);
    if (!card) return;
    
    // Деактивируем все кнопки
    card.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Скрываем все вкладки
    card.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    
    // Активируем нужную вкладку и кнопку
    const targetTab = document.getElementById(`${charId}_${tabName}`);
    const targetBtn = card.querySelector(`.tab-btn:nth-child(${['abilities', 'inventory', 'background'].indexOf(tabName) + 1})`);
    
    if (targetTab) targetTab.style.display = 'block';
    if (targetBtn) targetBtn.classList.add('active');

    // Сохраняем состояние
    activeTabStates[charId] = tabName;
}

function updateTurnOrder(characters) {
    if (!characters?.length) return;

    if (initiativeOrder.length === 0) {
        initiativeOrder = characters
            .map(char => ({
                name: char.name,
                isPlayer: char.is_player,
                initiative: Math.floor(Math.random() * 20) + 1
            }))
            .sort((a, b) => b.initiative - a.initiative);
    }

    const list = document.getElementById('turnOrderList');
    list.innerHTML = initiativeOrder.map((char, index) => `
        <div class="turn-item ${index === currentTurnIndex ? 'active' : ''}">
            <span>${char.initiative}</span>
            <span>${char.name}</span>
        </div>
    `).join('');
}

function nextTurn() {
    if (initiativeOrder.length === 0) return;
    currentTurnIndex = (currentTurnIndex + 1) % initiativeOrder.length;
    updateTurnOrder([]);
}

function resetInitiative() {
    initiativeOrder = [];
    currentTurnIndex = 0;
}