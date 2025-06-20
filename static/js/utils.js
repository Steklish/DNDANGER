// alert funtions
function createNotificationContainer() {
    // Check if the container already exists
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }
    return container;
}

function showNotification(message, type = 'info', duration = 3000) {
    const container = createNotificationContainer();

    // 1. Create the notification element
    const notification = document.createElement('div');
    notification.className = `info ${type}`; // e.g., 'info success'

    // Set its inner HTML with the message and icons
    notification.innerHTML = `
        <div class="info__icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" viewBox="0 0 24 24" height="24" fill="none"><path fill="#fff" d="m12 1.5c-5.79844 0-10.5 4.70156-10.5 10.5 0 5.7984 4.70156 10.5 10.5 10.5 5.7984 0 10.5-4.7016 10.5-10.5 0-5.79844-4.7016-10.5-10.5-10.5zm.75 15.5625c0 .1031-.0844.1875-.1875.1875h-1.125c-.1031 0-.1875-.0844-.1875-.1875v-6.375c0-.1031.0844-.1875.1875-.1875h1.125c.1031 0 .1875.0844.1875.1875zm-.75-8.0625c-.2944-.00601-.5747-.12718-.7808-.3375-.206-.21032-.3215-.49305-.3215-.7875s.1155-.57718.3215-.7875c.2061-.21032.4864-.33149.7808-.3375.2944.00601.5747.12718.7808.3375.206.21032.3215.49305.3215.7875s-.1155.57718-.3215.7875c-.2061.21032-.4864.33149-.7808.3375z"></path></svg>
        </div>
        <div class="info__title">${message}</div>
    `;

    // 2. Add it to the container
    container.prepend(notification); // Prepend to show newest at the top

    // 3. Force a reflow, then add the 'show' class to trigger the animation
    // This is a trick to make sure the browser registers the initial state before animating
    setTimeout(() => {
        notification.classList.add('show');
    }, 10); // A small delay is enough

    // 4. Set a timer to automatically remove the notification
    const hideTimer = setTimeout(() => {
        notification.classList.remove('show');
    }, duration);

    // 6. Remove the element from the DOM after the hide animation finishes
    notification.addEventListener('transitionend', (event) => {
        // Ensure we're listening for the transform property specifically if needed
        if (event.propertyName === 'transform' && !notification.classList.contains('show')) {
            notification.remove();
        }
    });
}