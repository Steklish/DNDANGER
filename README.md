# DND Born in Pain

An intelligent AI Dungeon Master assistant for D&D campaigns, using Python, FastAPI, and Google Gemini AI to create immersive narratives.

## Ongoing Development

This project is under active development. Current efforts are focused on:

*   **Admin Panel:** Enhancing the admin dashboard with more granular control over the game state, including character and story management.
*   **Character Creation:** Implementing a full-featured character creation screen with a point-buy system for stats.
*   **API Refinement:** Standardizing API endpoints for consistency and clarity.
*   **Real-time Updates:** Improving the reliability and scope of real-time updates for all clients.

## Installation

1.  **Set up environment variables:**
    ```bash
    # Copy the example environment file
    cp .env.example .env
    ```
2.  **Configure Google AI credentials:**
    *   Obtain a Google API key from the Google Cloud Console.
    *   Add your API key to the `.env` file:
        ```
        GOOGLE_API_KEY="your-api-key"
        GEMINI_MODEL_DUMB="gemini-1.5-flash"
        ```

## Usage

### Running the application:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## Technical Details

*   **Backend:** FastAPI (asynchronous Python framework)
*   **Real-time:** Server-Sent Events (SSE) for streaming game events.
*   **AI:** Google Gemini for content generation.
*   **Data Validation:** Pydantic
*   **Templating:** Jinja2
*   **Frontend:** Vanilla JavaScript and CSS

## API Endpoints

### HTML Pages
*   `GET /`: Login page.
*   `GET /character-creation`: Character creation page.
*   `GET /player/{name}`: The main player interface.
*   `GET /admin`: The admin dashboard.

### Game State & Interaction
*   `GET /api/game_state`: Retrieves the complete current state of the game.
*   `POST /interact`: Submits a player action or message.
*   `POST /create-character`: Creates a new player character.

### Admin & Story Management
*   `POST /api/story/next`: Advances the story to the next plot point.
*   `POST /api/story/previous`: Reverts the story to the previous plot point.
*   `POST /api/story/set/{plot_point_id}`: Jumps to a specific plot point.
*   `POST /api/character/update`: Updates a character's details.
*   `DELETE /api/character/{character_name}`: Deletes a character from the game.

### Real-time Stream
*   `GET /stream`: Establishes an SSE connection for real-time updates.

## Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.