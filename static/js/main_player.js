// Инициализируем обработчики событий после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    let lockInputNonce = 0;
    let scene
    // Получаем ссылки на основные элементы интерфейса
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const sideMenu = document.getElementById('sideMenu');
    const menuOpen = document.getElementById('menuOpen');
    const menuClose = document.getElementById('menuClose');
    const menuItems = document.querySelectorAll('.menu-item');
    const character_name = document.getElementById('character_name').innerHTML;
    const playerWaitLoading = document.getElementById('player_wait_loading');

    const backgroundEtags = {};
    playerWaitLoading.style.display = "none"
    // Получаем имя игрока из localStorage (установленное при логине)
    const currentPlayerName = localStorage.getItem('playerName');
    
    // Non-blocking initial check for player's turn
    get_current_character().then(name => {
        if (name !== character_name) {
            console.log("Other player's turn");
            lock_input();
        }
    }).catch(error => {
        console.error("Initial character check failed:", error);
        // Decide if we should lock the input on failure as a safe default
        lock_input(); 
    });

    // Если имя не установлено, перенаправляем на страницу логина
    if (!currentPlayerName) {
        window.location.href = '/login';
        return;
    }

    

    let lastMessageCount = 0; // Для отслеживания новых сообщений

    // Создаем EventSource для получения обновлений
    let eventSource = new EventSource(`/stream?name=${character_name}`);

    // Обрабатываем получаемые сообщения
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log(data)
            switch (data.event) {
            case "message":
                addMessage(
                    data.data,
                    data.sender
                );
                break; // Prevents "fall-through" to the next case

            case "alert":
                addMessage(
                    data.data,
                    "system"
                );
                break;

            case "scene_change":
                showNotification(`Scene updated ${data.new_scene_name}`)
                updateBackground(data.new_scene_name)
                break;
                
            // case "player_left":
            //     showNotification(`Player [${data.data}] left the room`)
            //     break;


            case "lock":
                if (data.allowed_players.includes(character_name)) {
                    unlock_input();
                } else {
                    if (data.game_mode != "NARRATIVE"){
                        lock_input(data.allowed_players.length !== 0);
                    }
                    else if (data.lock_all == true) {
                        lock_input(data.allowed_players.length !== 0);
                    }

                }
                if (data.game_mode == "NARRATIVE" && data.lock_all == false){
                    unlock_input();
                    setTimeout(() => {
                        messageInput.placeholder = "Type something (story mode)..."
                    }, 100);
                }
                break;

            case "connection_denied":
                showNotification("Connection refused")
                showNotification("The character is unavailable")
                // секунда на почитать сообщение
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
                break;

            default:
                // Optional: This block runs if data.event doesn't match any of the cases.
                // It's good practice for handling unexpected events.
                console.log(`Received an unhandled event type: ${data.event}`);
                break;
        }
            
            // updateUI(data);
        } catch (error) {
            console.error('Error processing update:', error);
        }
    };

    function updateBackground(filename) {
        console.log("Changing chat bg", filename);
        // Add a cache-busting query parameter (timestamp)
        const cacheBuster = Date.now();
        chatMessages.style.backgroundImage = `url('/static/images/${filename}?cb=${cacheBuster}')`;
    }

    // Обработка ошибок подключения
    eventSource.onopen = () => console.log("SSE connection opened");
    eventSource.onclose = () => console.log("SSE connection closed");
    eventSource.onerror = function(error) {
        eventSource.close();
        showNotification("Reconnecting...")
        setTimeout(() => {
            eventSource = new EventSource(`/stream?name=${character_name}`);
        }, 3000); // 3 seconds delay before reconnecting
        refresh()
    };

    function unlock_input(){
        playerWaitLoading.style.display = "none";
        messageInput.disabled = false
        sendButton.disabled = false
        messageInput.placeholder="Type a message..."
    }

    async function get_current_character(){
        let response = await fetch('/api/get_current_character');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        let data = await response.json();
        console.log("Active character from API:", data.active_character);
        return data.active_character;
    }

    async function lock_input(is_waiting = true) {
        const nonce = ++lockInputNonce;
        playerWaitLoading.style.display = "";
        messageInput.disabled = true
        sendButton.disabled = true

        if (is_waiting) {
            messageInput.placeholder = `Wait for your turn...`;
            try {
                const name = await get_current_character();
                if (nonce === lockInputNonce) {
                    messageInput.placeholder = `Wait for your turn (${name}'s turn)...`;
                }
            } catch (error) {
                console.error("Failed to get current character:", error);
                if (nonce === lockInputNonce) {
                    messageInput.placeholder = `Wait for your turn...`; // Fallback
                }
            }
        } else {
            messageInput.placeholder = `Processing something...`;
        }
    }


    // Функция обновления UI
    function updateUI(data) {
        if (data.characters) {
            const playerCharacter = data.characters.find(char => char.name === character_name);
            if (playerCharacter) {
                updateCharacterInfo(playerCharacter);
            }
        }
        if (data.scene) {
            scene = data.scene;
            updateSceneInfo(data.scene);
            updateBackground(`${data.scene.name}.png`)
        }
        if (data.chat_history) {
            updateChat(data.chat_history);
        }
        if (data.turn_order) {
            updateTurnOrder(data.turn_order, data.characters);
        }
    }

    const PLAYER_COLORS = 8; // Number of player colors defined in CSS

    function simpleHashCode(str) {
        let hash = 0;
        if (str.length === 0) {
            return hash;
        }
        
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            
            // Convert to a 32bit integer
            hash |= 0; 
        }
        // Ensure the result is a non-negative number.
        return Math.abs(hash);
    }

    function getPlayerColor(name) {
        const hash = simpleHashCode(name);
        const colorIndex = (hash % PLAYER_COLORS) + 1;
        return {
            primary: `var(--player-color-${colorIndex})`,
            bg: `var(--player-color-${colorIndex}-bg)`
        };
    }

    function setGlobalTheme(name) {
        const playerColor = getPlayerColor(name);
        document.body.style.setProperty('--active-player-color', playerColor.primary);
        document.body.style.setProperty('--active-player-color-bg', playerColor.bg);
    }

    // Set the initial theme based on the current character
    setGlobalTheme(character_name);

    function addMessage(messageText, senderName) {
        const scrollThreshold = 60; 
        const isScrolledToBottom = chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + scrollThreshold;
        
        const messageElement = document.createElement('div');

        if (senderName === "system") {
            messageElement.className = 'message-system';
            messageElement.innerHTML = `<div class="message-text-system">${messageText}</div>`;
        } else {
            let message_src = "";
            if (senderName === character_name) {
                message_src = "sent player-message"; // Add player-message class
            } else {
                message_src = "received player-message"; // Add player-message class
            }
    
            let is_DM = "";
            if (senderName === "DM") { 
                is_DM = "DM_message";
            }
    
            messageElement.className = `message ${message_src} ${is_DM}`;
            messageElement.innerHTML = `
                ${senderName !== character_name ? `<div class="sender-name">${senderName}</div>` : ""} 
                <div class="message-text">
                    ${marked.parse(messageText.trimStart())}
                </div>
            `;

            // Assign a unique color to other players
            if (senderName !== "DM") {
                const playerColor = getPlayerColor(senderName);
                messageElement.style.setProperty('--player-color', playerColor.primary);
                messageElement.style.setProperty('--player-color-bg', playerColor.bg);
            }
        }

        chatMessages.appendChild(messageElement);

        // --- Scroll down ONLY if the user was already at the bottom ---
        if (isScrolledToBottom) {
            chatMessages.lastElementChild.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function send_interaction_request(text){
        fetch('/interact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "character" : character_name,
                    "message" : text 
                }
            )
        })
        .then(response => response.json())
        .then(data => {
            // Optionally handle response data here
            console.log('Interaction response:', data);
        })
        .catch(error => {
            console.error('Ошибка при отправке запроса взаимодействия:', error);
        });
    }
    // Функция обновления чата
    function updateChat(messages) {
        if (!chatMessages) return;

        chatMessages.innerHTML = '';
        messages.forEach(message => {
            const senderName = message.sender_name;
            const messageText = message.message_text;
            addMessage(messageText, senderName)
        });
        
        // Прокручиваем к последнему сообщению
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Обновляем боковую историю чата
        // ! это не используется сейчас но фича норм
        // const chatHistorySidebar = document.getElementById('chatHistory');
        // if (chatHistorySidebar) {
        //     chatHistorySidebar.innerHTML = messages.map(message => `
        //         <div class="chat-history-item">
        //             <strong>${message.sender_name}</strong>
        //             <p>${parseMarkdownAndHTML(message.message_text)}</p>
        //         </div>
        //     `).join('');
        // }
    }

    function updateTurnOrder(turnOrder, characters) {
        const turnOrderList = document.getElementById('turnOrderList');
        if (turnOrderList) {
            turnOrderList.innerHTML = turnOrder.map(name => {
                const character = characters.find(c => c.name === name);
                const isActive = character && character.name === window.character_name;
                return `
                    <div class="turn-item ${isActive ? 'active' : ''}">
                        <img src="/static/images/${name}.png" class="turn-char-icon" alt="${name}">
                        <span>${name}</span>
                    </div>
                `;
            }).join('') || '<li>No combatants</li>';
        }
    }

    // Функция обновления информации о персонаже
    function updateCharacterInfo(character) {
        // Helper to safely update text content
        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text || 'N/A';
        };

        // Vitals
        setText('charName', character.name);
        setText('charHP', `${character.current_hp}/${character.max_hp}`);
        setText('charAC', character.ac);
        setText('charGender', character.gender);

        // Conditions
        const conditionsList = document.getElementById('conditionsList');
        if (conditionsList) {
            conditionsList.innerHTML = character.conditions.map(c => `<li class="condition">${c}</li>`).join('') || '<li>None</li>';
        }

        // Stats
        setText('charStr', character.strength);
        setText('charDex', character.dexterity);
        setText('charCon', character.constitution);
        setText('charInt', character.intelligence);
        setText('charWis', character.wisdom);
        setText('charCha', character.charisma);

        // Appearance
        const charImage = document.getElementById('charImage');
        if (charImage) {
            charImage.src = `/static/images/${character.name}.png`;
        }
        setText('charAppearance', character.appearance);
        setText('charClothing', character.clothing_and_cosmetics);

        // Background
        setText('personalityHistory', character.personality_history);

        // Inventory
        const inventoryList = document.getElementById('inventoryList');
        if (inventoryList) {
            inventoryList.innerHTML = character.inventory.map(item => `
                <div class="inventory-item">
                    <div class="item-header">
                        <strong class="name rarity-${item.rarity}">${item.name}</strong>
                        <span class="keyword">${item.item_type}</span>
                    </div>
                    <p>${item.description}</p>
                    <div class="item-details">
                        <span class="item-stat">Qty: ${item.quantity}</span>
                        <span class="item-stat">Value: ${item.value}g</span>
                        <span class="item-stat">Weight: ${item.weight}lb</span>
                        ${item.is_magical ? `<span class="item-stat magical">Magical</span>` : ''}
                        ${item.damage ? `<span class="item-stat">Dmg: ${item.damage} ${item.damage_type || ''}</span>` : ''}
                        ${item.armor_class ? `<span class="item-stat">AC: ${item.armor_class}</span>` : ''}
                    </div>
                    ${item.effect ? `<p class="item-effect"><strong>Effect:</strong> ${item.effect}</p>` : ''}
                    ${item.properties.length > 0 ? `<p class="item-properties"><strong>Properties:</strong> ${item.properties.join(', ')}</p>` : ''}
                </div>
            `).join('') || '<p>Inventory is empty.</p>';
        }

        // Abilities
        const abilitiesList = document.getElementById('abilitiesList');
        if (abilitiesList) {
            abilitiesList.innerHTML = character.abilities.map(ability => {
                let detailsHtml = '';
                if (ability.details && Object.keys(ability.details).length > 0) {
                    detailsHtml = '<div class="ability-details">';
                    for (const [key, value] of Object.entries(ability.details)) {
                        detailsHtml += `<p><strong>${key.replace(/_/g, ' ')}:</strong> ${value}</p>`;
                    }
                    detailsHtml += '</div>';
                }
                return `
                    <div class="ability-item">
                        <div class="ability-header">
                            <strong class="name">${ability.name}</strong>
                        </div>
                        <p>${ability.description}</p>
                        ${detailsHtml}
                    </div>
                `;
            }).join('') || '<p>No abilities.</p>';
        }
    }

    // Функция обновления информации о сцене
    function updateSceneInfo(scene) {
        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text || 'N/A';
        };

        setText('sceneName', scene.name);
        setText('sceneDescription', scene.description);
        setText('sceneSize', scene.size_description);

        const sceneObjects = document.getElementById('sceneObjects');
        if (sceneObjects) {
            sceneObjects.innerHTML = scene.objects.map(obj => `
                <div class="scene-object">
                    <strong class="name">${obj.name}</strong>
                    <p>${obj.description}</p>
                    <p><strong>Size:</strong> ${obj.size_description}</p>
                    <p><strong>Position:</strong> ${obj.position_in_scene}</p>
                    ${obj.interactions.length > 0 ? `<p class="keyword">Interactions: ${obj.interactions.join(', ')}</p>` : ''}
                </div>
            `).join('') || '<p>No objects in this scene.</p>';
        }
        
        const sceneImage = document.getElementById('sceneImage');
        if (sceneImage) {
            sceneImage.src = `/static/images/${scene.name}.png`;
        }

        const event = new CustomEvent('scene_changed', { detail: scene });
        document.dispatchEvent(event);
    }


    // Открытие бокового меню
    menuOpen.addEventListener('click', function(e) {
        e.stopPropagation();
        sideMenu.classList.add('open');
        document.addEventListener('click', closeMenuOutside);
        refresh(); // Refresh data when menu opens
    });

    menuClose.addEventListener('click', function() {
        sideMenu.classList.remove('open');
        document.removeEventListener('click', closeMenuOutside);
    });

    // Функция для закрытия меню при клике вне его
    function closeMenuOutside(e) {
        if (!sideMenu.contains(e.target) && e.target !== menuOpen) {
            sideMenu.classList.remove('open');
            document.removeEventListener('click', closeMenuOutside);
        }
    }

    // Предотвращаем закрытие меню при клике внутри него
    sideMenu.addEventListener('click', function(e) {
        e.stopPropagation();
    });

    // Обработка кликов по пунктам меню (collapsible cards)
    const menuCardHeaders = document.querySelectorAll('.menu-item-header');
    menuCardHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const menuItem = this.parentElement;
            menuItem.classList.toggle('expanded');
            const dropdown = menuItem.querySelector('.menu-dropdown');
            if (menuItem.classList.contains('expanded')) {
                dropdown.style.display = 'block';
            } else {
                dropdown.style.display = 'none';
            }
        });
    });

    // Default expand for character sheet
    const characterSheet = document.querySelector('.menu-item');
    if(characterSheet){
        characterSheet.classList.add('expanded');
        characterSheet.querySelector('.menu-dropdown').style.display = 'block';
    }
    // Обработка переключения вкладок
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', function() {
            const tabId = this.dataset.tab;

            tabLinks.forEach(link => link.classList.remove('active'));
            this.classList.add('active');

            tabContents.forEach(content => {
                if (content.id === tabId) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });

    // Обработчик отправки сообщений
    sendButton.addEventListener('click', function() {
        const message = messageInput.value.trim();
        if (message) {
            send_interaction_request(message)
            chatMessages.scrollTop = chatMessages.scrollHeight;
            messageInput.value = '';
        }
    });

    // Обработка отправки сообщения по нажатию Enter
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendButton.click();
        }
    });

    function refresh(){
        fetch('/api/game_state')
            .then(response => response.json())
            .then(data => {
                updateUI(data);
            })
            .catch(error => {
                console.error('Error fetching initial data:', error);
            });
    }
        
    refresh()
});
