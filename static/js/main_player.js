// Инициализируем обработчики событий после загрузки DOM
document.addEventListener('DOMContentLoaded', async function() {
    
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
    playerWaitLoading.style.display = "none"
    // Получаем имя игрока из localStorage (установленное при логине)
    const currentPlayerName = localStorage.getItem('playerName');
    
    if (await get_current_character() != character_name){
        console.log("Other player's turn")
        lock_input()
    }
    // Если имя не установлено, перенаправляем на страницу логина
    if (!currentPlayerName) {
        window.location.href = '/login';
        return;
    }

    

    let lastMessageCount = 0; // Для отслеживания новых сообщений

    // Создаем EventSource для получения обновлений
    const eventSource = new EventSource(`/stream?name=${character_name}`);

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
            case "player_joined":
                showNotification(`Player [${data.data}] joined the room`)
                break;
                
            case "player_left":
                showNotification(`Player [${data.data}] left the room`)
                break;


            case "lock":
                if (data.allowed_players.includes(character_name)) {
                    unlock_input();
                } else {
                    // Using strict inequality (!==) is generally safer than loose (!=)
                    lock_input(data.allowed_players.length !== 0);
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

    // Обработка ошибок подключения
    eventSource.onerror = function(error) {
        showNotification("Connection error reconnecting")
        // showNotification("The character is unavailable")
        setTimeout(() => {
            // window.location.href = '/login';
            window.location.reload()
        }, 1000);
    };


    function unlock_input(){
        playerWaitLoading.style.display = "none";
        messageInput.disabled = false
        sendButton.disabled = false
        messageInput.placeholder="Type a message..."
    }

    async function get_current_character(){
        let response = await fetch('/get_current_character')
        let name = await response.text()
        console.log(name)
        return name
    }

    async function lock_input(is_waiting = true) {
        playerWaitLoading.style.display = "";
        messageInput.disabled = true
        sendButton.disabled = true
        messageInput.placeholder = is_waiting 
            ? `Wait for your turn (${await get_current_character()}'s turn)...` 
            : `Processing something...`;
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
            updateSceneInfo(data.scene);
        }
        if (data.chat_history) {
            updateChat(data.chat_history);
        }
    }

    function addMessage(messageText, senderName) {
        const scrollThreshold = 30; 
        const isScrolledToBottom = chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + scrollThreshold;
        if (senderName == "system"){
            let new_message = `
            <div class="message-system">
                <div class="message-text-system">
                ${messageText}
                </div>
            </div>`;
            chatMessages.innerHTML += new_message;
        }
        else{
            let message_src = "";
            if (senderName == character_name) {
                message_src = "sent";
            } else {
                message_src = "received";
            }
    
            let is_DM = "";
            if (senderName == "DM") { is_DM = "DM_message" }
    
            let new_message = `
            <div class="message ${message_src} ${is_DM}">
                ${senderName != character_name ? `<div class="sender-name">${senderName}</div>` : ""} 
                <div class="message-text">
                ${marked.parse(messageText.trimStart())}
                </div>
            </div>
            `;
            chatMessages.innerHTML += new_message;
        }

        // --- Scroll down ONLY if the user was already at the bottom ---
        if (isScrolledToBottom) {
            // You can use scrollIntoView on the new last element...
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

    // Функция обновления информации о персонаже
    function updateCharacterInfo(character) {
        // Обновляем базовую информацию
        const charName = document.getElementById('charName');
        const charHP = document.getElementById('charHP');
        const charAC = document.getElementById('charAC');
        const conditionsList = document.getElementById('conditionsList');

        if (charName) charName.textContent = character.name;
        if (charHP) charHP.textContent = `${character.current_hp}/${character.max_hp}`;
        if (charAC) charAC.textContent = character.ac;
        if (conditionsList) {
            conditionsList.innerHTML = character.conditions.map(condition => 
                `<li class="condition">${condition}</li>`
            ).join('') || 'Нет активных состояний';
        }

        // Обновляем инвентарь
        const inventoryList = document.getElementById('inventoryList');
        if (inventoryList) {
            inventoryList.innerHTML = character.inventory.map(item => `                <div class="inventory-item">
                    <div class="item-header">
                        <strong class="name rarity-${item.rarity || 'Common'}">${item.name}</strong>
                        <span class="keyword">${item.item_type}</span>
                        ${item.rarity ? `<span class="rarity-${item.rarity}">(${item.rarity})</span>` : ''}</div>
                    <p>${item.description}</p>
                    <div class="item-details">
                        ${item.quantity ? `<span class="item-stat">Количество: ${item.quantity}</span>` : ''}
                        ${item.damage ? `<span class="item-stat">Урон: ${item.damage}</span>` : ''}
                        ${item.armor_class ? `<span class="item-stat">AC: ${item.armor_class}</span>` : ''}
                        ${item.effect ? `<span class="item-stat">Эффект: ${item.effect}</span>` : ''}
                    </div>
                </div>
            `).join('') || 'Инвентарь пуст';
        }

        // Обновляем способности
        const abilitiesList = document.getElementById('abilitiesList');
        if (abilitiesList) {
            abilitiesList.innerHTML = character.abilities.map(ability => `
                <div class="ability-item">
                    <div class="ability-header">
                        <strong class="name">${ability.name}</strong>
                    </div>
                    <p>${ability.description}</p>
                    ${ability.details ? `<div class="ability-details">${JSON.stringify(ability.details)}</div>` : ''}
                </div>
            `).join('') || 'Нет доступных способностей';
        }

        // Обновляем историю персонажа
        const personalityHistory = document.getElementById('personalityHistory');
        if (personalityHistory) {
            personalityHistory.innerHTML = `<p>${character.personality_history || 'Нет информации о предыстории'}</p>`;
        }
    }

    // Функция обновления информации о сцене
    function updateSceneInfo(scene) {
        const sceneName = document.getElementById('sceneName');
        const sceneDescription = document.getElementById('sceneDescription');
        const sceneObjects = document.getElementById('sceneObjects');

        if (sceneName) sceneName.textContent = scene.name;
        if (sceneDescription) sceneDescription.textContent = scene.description;
        if (sceneObjects) {
            sceneObjects.innerHTML = scene.objects.map(obj => `
                <div class="scene-object">
                    <strong class="name">${obj.name}</strong>
                    <p>${obj.description}</p>
                    <p class="keyword">Взаимодействия: ${obj.interactions.join(', ')}</p>
                </div>
            `).join('');
        }
    }

    // Открытие бокового меню
    menuOpen.addEventListener('click', function(e) {
        e.stopPropagation();
        sideMenu.classList.add('open');
        document.addEventListener('click', closeMenuOutside);
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

    // Обработка кликов по пунктам меню
    menuItems.forEach(item => {
        const header = item.querySelector('span:not(.material-icons)').parentElement;
        header.addEventListener('click', function(e) {
            e.stopPropagation();
            menuItems.forEach(otherItem => {
                if (otherItem !== item) {
                    otherItem.classList.remove('expanded');
                }
            });
            item.classList.toggle('expanded');
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

    // Выполняем первоначальную загрузку данных
    fetch('/refresh')
        .then(response => response.json())
        .then(data => {
            updateUI(data);
        })
        .catch(error => {
            console.error('Error fetching initial data:', error);
        });
});
