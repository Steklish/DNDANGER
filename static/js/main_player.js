// Инициализируем обработчики событий после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    // Получаем ссылки на основные элементы интерфейса
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const sideMenu = document.getElementById('sideMenu');
    const menuOpen = document.getElementById('menuOpen');
    const menuClose = document.getElementById('menuClose');
    const menuItems = document.querySelectorAll('.menu-item');
    const character_name = document.getElementById('character_name').innerHTML

    // Получаем имя игрока из localStorage (установленное при логине)
    const currentPlayerName = localStorage.getItem('playerName');
    
    // Если имя не установлено, перенаправляем на страницу логина
    if (!currentPlayerName) {
        window.location.href = '/login.html';
        return;
    }

    let lastMessageCount = 0; // Для отслеживания новых сообщений

    // Функция обновления данных
    function fetchUpdates() {
        fetch('/refresh')
            .then(response => response.json())
            .then(data => {
                try {
                    console.log('Получены данные:', data); // Для отладки

                    // Обновляем информацию о персонаже
                    if (data.characters && data.characters.length > 0) {
                        const playerCharacter = data.characters[0]; // Берем первого персонажа из массива
                        
                        // Обновляем базовую информацию
                        const charName = document.getElementById('charName');
                        const charHP = document.getElementById('charHP');
                        const charAC = document.getElementById('charAC');
                        const conditionsList = document.getElementById('conditionsList');
                        const inventoryList = document.getElementById('inventoryList');
                        const abilitiesList = document.getElementById('abilitiesList');
                        const personalityHistory = document.getElementById('personalityHistory');

                        if (charName) charName.textContent = playerCharacter.name;
                        if (charHP) charHP.textContent = `${playerCharacter.current_hp}/${playerCharacter.max_hp}`;
                        if (charAC) charAC.textContent = playerCharacter.ac;

                        // Состояния
                        if (conditionsList) {
                            conditionsList.innerHTML = playerCharacter.conditions.length ? 
                                playerCharacter.conditions.map(condition => `<li>${condition}</li>`).join('') : 
                                '<li>Нет активных состояний</li>';
                        }

                        // Инвентарь
                        if (inventoryList) {
                            inventoryList.innerHTML = playerCharacter.inventory.map(item => `
                                <div class="inventory-item">
                                    <h4>${item.name} ${item.item_type ? `(${item.item_type})` : ''}</h4>
                                    <p>${item.description}</p>
                                    ${item.quantity ? `<p><em>Количество:</em> ${item.quantity}</p>` : ''}
                                    ${item.weight ? `<p><em>Вес:</em> ${item.weight}</p>` : ''}
                                    ${item.value ? `<p><em>Ценность:</em> ${item.value}</p>` : ''}
                                    ${item.rarity ? `<p><em>Редкость:</em> ${item.rarity}</p>` : ''}
                                    ${item.is_magical !== undefined ? `<p><em>Магический:</em> ${item.is_magical ? 'Да' : 'Нет'}</p>` : ''}
                                    ${item.damage ? `<p><em>Урон:</em> ${item.damage} ${item.damage_type ? `(${item.damage_type})` : ''}</p>` : ''}
                                    ${item.effect ? `<p><em>Эффект:</em> ${item.effect}</p>` : ''}
                                    ${item.properties && item.properties.length > 0 ? `<p><em>Свойства:</em> ${item.properties.join(', ')}</p>` : ''}
                                </div>
                            `).join('');
                        }

                        // Способности
                        if (abilitiesList) {
                            abilitiesList.innerHTML = playerCharacter.abilities.map(ability => `
                                <div class="ability-item">
                                    <h4>${ability.name}</h4>
                                    <p>${ability.description}</p>
                                    ${ability.details ? `
                                        <div class="ability-details">
                                            <p><em>Использование:</em> ${ability.details.usage}</p>
                                            <p><em>Тип действия:</em> ${ability.details.action_type}</p>
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('');
                        }

                        // История персонажа
                        if (personalityHistory) {
                            personalityHistory.innerHTML = parseMarkdownAndHTML(playerCharacter.personality_history || 'История не указана');
                        }
                    }

                    // Обновляем информацию о сцене
                    if (data.scene) {
                        const sceneName = document.getElementById('sceneName');
                        const sceneDescription = document.getElementById('sceneDescription');
                        const sceneSize = document.getElementById('sceneSize');
                        const sceneObjects = document.getElementById('sceneObjects');

                        if (sceneName) sceneName.textContent = data.scene.name;
                        if (sceneDescription) sceneDescription.innerHTML = parseMarkdownAndHTML(data.scene.description);
                        if (sceneSize) sceneSize.textContent = data.scene.size_description;
                        
                        if (sceneObjects) {
                            sceneObjects.innerHTML = `<h4>Объекты в сцене:</h4>` + 
                                data.scene.objects.map(obj => `
                                    <div class="scene-object">
                                        <h5>${obj.name}</h5>
                                        <p>${obj.description}</p>
                                        <p><em>Расположение:</em> ${obj.position_in_scene}</p>
                                        <p><em>Размер:</em> ${obj.size_description}</p>
                                        <p><em>Действия:</em> ${obj.interactions.join(', ')}</p>
                                    </div>
                                `).join('');
                        }
                    }

                    // Обновляем чат
                    if (data.chat_history) {
                        updateChat(data.chat_history);
                        lastMessageCount = data.chat_history.length;
                    }

                } catch (error) {
                    console.error('Ошибка при обработке данных:', error);
                }
            })
            .catch(error => {
                console.error('Ошибка при получении обновлений:', error);
            });
    }

    function addMessage(messageText, senderName) {
        let new_message = ''
        if (senderName == character_name){
            new_message = `
                <div class="message sent">
                    <div class="sender-name">${senderName}</div>
                    <div class="message-text">
                    ${marked.parse(messageText.trimStart())}
                    </div>
                </div>
                `
        }
        else{
            new_message = `
                <div class="message received">
                    <div class="sender-name">${senderName}</div>
                    <div class="message-text">
                    ${marked.parse(messageText.trimStart())}
                    </div>
                </div>
                `
        }
            // console.log(messageText)
        chatMessages.innerHTML += new_message
        return
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
        const characterDropdown = document.getElementById('characterDropdown');
        if (!characterDropdown) return;

        let html = `
            <h3>Character Details</h3>
            <p><strong>Имя:</strong> ${character.name}</p>
            <p><strong>HP:</strong> ${character.current_hp} / ${character.max_hp}</p>
            <p><strong>AC:</strong> ${character.ac}</p>
            
            <h4>Способности:</h4>
            <ul>
                ${character.abilities.map(ability => `
                    <li>
                        <strong>${ability.name}</strong>: ${ability.description}
                        ${ability.details ? `<br><em>Детали:</em> ${JSON.stringify(ability.details)}` : ''}
                    </li>
                `).join('')}
            </ul>
            
            <h4>Инвентарь:</h4>
            <ul>
                ${character.inventory.map(item => `
                    <li>
                        <strong>${item.name}</strong> (${item.item_type})
                        <br>${item.description}
                        ${item.quantity !== undefined ? `<br><em>Количество:</em> ${item.quantity}` : ''}
                        ${item.weight !== undefined ? `<br><em>Вес:</em> ${item.weight}` : ''}
                        ${item.value !== undefined ? `<br><em>Ценность:</em> ${item.value}` : ''}
                        ${item.rarity !== undefined ? `<br><em>Редкость:</em> ${item.rarity}` : ''}
                        ${item.is_magical !== undefined ? `<br><em>Магический:</em> ${item.is_magical ? 'Да' : 'Нет'}` : ''}
                        ${item.damage !== undefined ? `<br><em>Урон:</em> ${item.damage} (${item.damage_type})` : ''}
                        ${item.armor_class !== undefined ? `<br><em>Класс брони:</em> ${item.armor_class}` : ''}
                        ${item.effect !== undefined ? `<br><em>Эффект:</em> ${item.effect}` : ''}
                        ${item.properties && item.properties.length > 0 ? `<br><em>Свойства:</em> ${item.properties.join(', ')}</em>` : ''}
                    </li>
                `).join('')}
            </ul>
            
            <h4>Состояния:</h4>
            <p>${character.conditions.length ? character.conditions.join(', ') : 'Нет активных состояний'}</p>
            
            <h4>История и Личность:</h4>
            <p>${character.personality_history || 'Нет информации'}</p>
        `;
        characterDropdown.innerHTML = html;
    }

    // Функция обновления информации о сцене
    function updateSceneInfo(scene) {
        const sceneDropdown = document.getElementById('sceneDropdown');
        if (!sceneDropdown) return;

        let html = `
            <h3>${scene.name}</h3>
            <p>${scene.description}</p>
            <p><strong>Размеры:</strong> ${scene.size_description}</p>
            
            <h4>Объекты в сцене:</h4>
            <ul>
                ${scene.objects.map(obj => `
                    <li>
                        <strong>${obj.name}</strong>
                        <br>${obj.description}
                        <br><em>Размер:</em> ${obj.size_description}
                        <br><em>Расположение:</em> ${obj.position_in_scene}
                        <br><em>Возможные действия:</em> ${obj.interactions.join(', ')}
                    </li>
                `).join('')}
            </ul>
        `;
        sceneDropdown.innerHTML = html;
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
            addMessage(message, character_name)
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

    // Функция для парсинга Markdown и HTML
    // ! под снос
    function parseMarkdownAndHTML(inputText) {
        try {
            if (typeof marked === 'undefined') {
                console.warn('Marked library not loaded, returning raw text');
                return inputText;
            }

            if (typeof inputText !== 'string') {
                return '';
            }
            
            const htmlContent = marked.parse(inputText);
            
            const container = document.createElement('div');
            container.innerHTML = htmlContent;
            
            container.querySelectorAll('.html-class').forEach(element => {
                element.style.color = 'var(--primary)';
            });
            
            return container.innerHTML;
        } catch (error) {
            console.error('Error parsing markdown:', error);
            return inputText || '';
        }
    }

    // Запускаем периодическое обновление каждые 5 секунд
    fetchUpdates(); // Первый запрос сразу
    // setInterval(fetchUpdates, 5000); // Увеличил интервал до 5 секунд
});
