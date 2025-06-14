// Инициализируем обработчики событий после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    // Получаем ссылки на основные элементы интерфейса
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const sideMenu = document.getElementById('sideMenu');
    const menuOpen = document.getElementById('menuOpen');
    const menuClose = document.getElementById('menuClose');
    const collapseToggle = document.getElementById('collapseToggle');
    
    // Обработка открытия бокового меню
    menuOpen.addEventListener('click', function() {
        sideMenu.classList.add('open');
    });
    
    // Обработка закрытия бокового меню
    menuClose.addEventListener('click', function() {
        sideMenu.classList.remove('open');
    });

    // Переключение состояния сворачивания бокового меню
    collapseToggle.addEventListener('click', function() {
        sideMenu.classList.toggle('collapsed');
        const icon = collapseToggle.querySelector('.material-icons');
        icon.textContent = sideMenu.classList.contains('collapsed') ? 'chevron_right' : 'chevron_left';
    });
    
    // Функция добавления нового сообщения в чат
    function addMessage(text, sender, isReceived) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isReceived ? 'received' : 'sent');
        
        // Создаем элементы сообщения
        const senderName = document.createElement('div');
        senderName.classList.add('sender-name');
        senderName.textContent = sender;
        
        const messageText = document.createElement('div');
        messageText.textContent = text;
        
        const timestamp = document.createElement('div');
        timestamp.classList.add('timestamp');
        timestamp.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Собираем сообщение воедино
        messageDiv.appendChild(senderName);
        messageDiv.appendChild(messageText);
        messageDiv.appendChild(timestamp);
        chatMessages.appendChild(messageDiv);
        
        // Прокручиваем чат к последнему сообщению
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Обработчик нажатия на кнопку отправки
    sendButton.addEventListener('click', function() {
        const message = messageInput.value.trim();
        if (message) {
            // Отправляем сообщение пользователя
            addMessage(message, "You", false);
            messageInput.value = '';
            
            // Имитируем ответ бота
            setTimeout(() => {
                const replies = [
                    "Понятно! Что ещё я могу для вас сделать?",
                    "Интересное замечание!",
                    "Я посмотрю, что можно сделать.",
                    "Спасибо за информацию!",
                    "Отличный вопрос!",
                    "Дайте подумать над этим..."
                ];
                const randomReply = replies[Math.floor(Math.random() * replies.length)];
                addMessage(randomReply, "Bot", true);
            }, 800);
        }
    });
    
    // Обработка отправки сообщения по нажатию Enter
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendButton.click();
        }
    });
    
    // Отправляем приветственное сообщение
    setTimeout(() => {
        addMessage("Добро пожаловать в Material Chat! Чем могу помочь?", "Bot", true);
    }, 500);
    
    // Закрываем меню при клике вне его на мобильных устройствах
    document.addEventListener('click', function(e) {
        if (!sideMenu.contains(e.target) && e.target !== menuOpen) {
            sideMenu.classList.remove('open');
        }
    });
});
