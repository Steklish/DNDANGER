document.addEventListener('DOMContentLoaded', () => {
    fetchGameState();
});

async function fetchGameState() {
    try {
        const response = await fetch('/api/game_state');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const state = await response.json();
        updateUI(state);
    } catch (error) {
        console.error('Failed to fetch game state:', error);
    }
}

function updateUI(state) {
    // Game Mode, Story, Scene, Debug info... (remains the same)
    document.getElementById('game-mode-indicator').textContent = `Game Mode: ${state.game_mode}`;
    const story = state.story;
    document.getElementById('story-title').textContent = story.title;
    document.getElementById('story-goal').textContent = story.main_goal;
    if (story.current_plot_point) {
        document.getElementById('plot-point-desc').textContent = story.current_plot_point.description;
        document.getElementById('plot-point-conditions').textContent = `Completion: ${story.current_plot_point.completion_conditions}`;
    }
    const selector = document.getElementById('plot-point-selector');
    selector.innerHTML = story.all_plot_points.map(p => 
        `<option value="${p.id}" ${p.id === story.current_plot_point?.id ? 'selected' : ''}>${p.title}</option>`
    ).join('');
    document.getElementById('scene-name').textContent = state.scene.name;
    document.getElementById('scene-description').innerHTML = marked.parse(state.scene.description);
    document.getElementById('scene-objects-list').innerHTML = state.scene.objects.map(obj => `
        <div class="scene-object"><strong>${obj.name}</strong>: ${obj.description}</div>
    `).join('');
    document.getElementById('game-context').textContent = state.context || "No context available.";
    const chatHistory = document.getElementById('chat-history');
    chatHistory.innerHTML = state.chat_history.map(msg => `
        <div class="chat-message"><strong>${msg.sender_name}:</strong> ${msg.message_text}</div>
    `).join('');
    chatHistory.scrollTop = chatHistory.scrollHeight;

    // Event Log
    const eventLog = document.getElementById('event-log');
    eventLog.innerHTML = state.event_log.map(log => `
        <div class="log-entry">
            <strong>${log.event}</strong>
            <pre>${JSON.stringify(log.details, null, 2)}</pre>
        </div>
    `).join('');
    eventLog.scrollTop = eventLog.scrollHeight;


    // Enhanced Character Roster
    const roster = document.getElementById('character-roster');
    roster.innerHTML = state.characters.map(char => createCharacterCard(char)).join('');
    
    // Add event listeners for the new edit buttons
    document.querySelectorAll('.toggle-edit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const form = document.getElementById(`edit-form-${btn.dataset.charId}`);
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
        });
    });
}

function createCharacterCard(char) {
    const charId = char.name.replace(/\s+/g, '-').toLowerCase();
    return `
        <div class="character-card-admin" id="char-card-${charId}">
            <div class="char-header">
                <h3>${char.name}</h3>
                <span class="char-type">${char.is_player ? 'Player' : 'NPC'}</span>
                <button class="btn-small toggle-edit-btn" data-char-id="${charId}">Edit</button>
            </div>
            <div class="hp-bar">
                <div class="hp-bar-inner" style="width: ${(char.current_hp / char.max_hp) * 100}%"></div>
                <span class="hp-text">${char.current_hp}/${char.max_hp} HP</span>
            </div>
            
            <form id="edit-form-${charId}" class="edit-character-form" style="display:none;" onsubmit="saveCharacter(event, '${char.name}')">
                <h4>Edit ${char.name}</h4>
                
                <div class="form-section">
                    <label>HP:</label>
                    <input type="number" name="current_hp" value="${char.current_hp}"> / <input type="number" name="max_hp" value="${char.max_hp}">
                </div>
                
                <div class="form-section">
                    <label>Abilities (one per line):</label>
                    <textarea name="abilities" rows="4">${char.abilities.map(a => a.name + ': ' + a.description).join('\n')}</textarea>
                </div>

                <div class="form-section">
                    <label>Inventory (one per line):</label>
                    <textarea name="inventory" rows="4">${char.inventory.map(i => i.name).join('\n')}</textarea>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn-small">Save</button>
                    <button type="button" class="btn-small btn-danger" onclick="deleteCharacter('${char.name}')">Delete</button>
                </div>
            </form>
        </div>
    `;
}

async function saveCharacter(event, characterName) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    const abilitiesText = formData.get('abilities').split('\n').filter(line => line.trim() !== '');
    const inventoryText = formData.get('inventory').split('\n').filter(line => line.trim() !== '');

    const payload = {
        name: characterName,
        updates: {
            current_hp: parseInt(formData.get('current_hp')),
            max_hp: parseInt(formData.get('max_hp')),
            abilities: abilitiesText.map(line => {
                const [name, ...desc] = line.split(':');
                return { name: name.trim(), description: desc.join(':').trim(), details: {} };
            }),
            inventory: inventoryText.map(name => ({ name: name.trim(), description: "An item." })), // Simplified for now
        }
    };

    try {
        const response = await fetch('/api/character/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('Failed to save character');
        fetchGameState(); // Refresh UI
    } catch (error) {
        console.error('Error saving character:', error);
    }
}

async function deleteCharacter(characterName) {
    if (!confirm(`Are you sure you want to delete ${characterName}?`)) return;

    try {
        const response = await fetch(`/api/character/${characterName}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete character');
        fetchGameState(); // Refresh UI
    } catch (error) {
        console.error('Error deleting character:', error);
    }
}

// Story navigation functions (navigateStory, jumpToPlotPoint, setPlotPoint) remain the same
async function navigateStory(direction) {
    try {
        const response = await fetch(`/api/story/${direction}`, { method: 'POST' });
        if (!response.ok) throw new Error(`Failed to navigate story: ${response.statusText}`);
        fetchGameState();
    } catch (error) {
        console.error(error);
    }
}

function jumpToPlotPoint() {
    const selector = document.getElementById('plot-point-selector');
    const plotPointId = selector.value;
    setPlotPoint(plotPointId);
}

async function setPlotPoint(plotPointId) {
    try {
        const response = await fetch(`/api/story/set/${plotPointId}`, { method: 'POST' });
        if (!response.ok) throw new Error(`Failed to set plot point: ${response.statusText}`);
        fetchGameState();
    } catch (error) {
        console.error(error);
    }
}