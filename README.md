# 🎮 Discord Jeopardy

Discord Jeopardy is a real-time, interactive multiplayer trivia game designed to run as a **Discord Activity** (Embedded App). Built with a Python/Flask backend and a WebSocket-powered frontend, it allows users to host and play custom Jeopardy-style games directly within Discord voice channels.

---

## ✨ Features

* **Real-Time Multiplayer Integration:** Powered by `Flask-SocketIO` for instantaneous buzzer actions, score updates, and board state synchronization.
* **Discord Embedded App SDK:** Designed to be played natively inside a Discord voice channel using the new Activity framework.
* **Role-Based Gameplay:**
  * **Host (Admin):** Creates the room, uploads the game board, reveals answers, arms the buzzer, and manages scores.
  * **Players:** Join via a 4-letter room code, race to buzz in, and compete for the highest score.
* **Custom XML Game Boards:** Easily create and upload custom game boards. Supports text-based questions, answers, dollar values, and embedded YouTube videos.
* **Rejoin & Override Logic:** Players can safely overwrite their session if they get disconnected, preventing stale connections.
* **Dynamic Media Support:** Questions can feature YouTube videos that auto-play seamlessly when revealed.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.11, Flask, Flask-SocketIO
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Socket.IO Client
* **Integration:** Discord Embedded App SDK (`@discord/embedded-app-sdk`)
* **Deployment:** Docker

---

## 📂 Project Structure

```text
.
├── app.py                 # Main Flask application and Socket.IO event handlers
├── Dockerfile             # Docker configuration for containerized deployment
├── index.html             # Main frontend UI and Discord SDK initialization
├── play_test.xml          # Example game board file (XML format)
├── requirements.txt       # Python dependencies (needs to be created)
├── .env                   # Environment variables (needs to be created)
├── modules/
│   └── parsing.py         # XML parsing logic (Custom module used in app.py)
└── static/
    ├── main.js            # Frontend game logic and socket events
    ├── style.css          # UI styling (Discord-themed)
    ├── socket.io.min.js   # Socket.IO client library
    └── audio/
        └── buzz_in.mp3    # Buzzer sound effect
(Note: Ensure you have requirements.txt, .env, and the modules/parsing.py script set up locally based on the imports in app.py).

⚙️ Setup & Installation
You can run this project locally for testing or using Docker for a clean, containerized deployment.

1. Environment Variables
Create a .env file in the root directory. You will need to retrieve your Discord Client credentials from the Discord Developer Portal.

Code snippet

FLASK_SECRET_KEY=your_secure_random_secret_key
DISCORD_CLIENT_ID=your_discord_application_client_id
DISCORD_CLIENT_SECRET=your_discord_application_client_secret
2. Local Python Setup (Without Docker)
Ensure you have Python 3.11+ installed.

Clone the repository and navigate to the project root.

Create a virtual environment:

Bash

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install the required dependencies (Make sure your requirements.txt includes Flask, Flask-SocketIO, python-dotenv, and requests):

Bash

pip install -r requirements.txt
Run the application:

Bash

python app.py
The server will start on http://0.0.0.0:8000.

3. Docker Setup (Recommended)
Ensure Docker is installed on your machine.

Build the Docker image:

Bash

docker build -t discord-jeopardy .
Run the Docker container, passing in your .env file and exposing port 8000:

Bash

docker run -p 8000:8000 --env-file .env discord-jeopardy
🚀 Setting up the Discord Activity
To use this app directly inside Discord:

Go to the Discord Developer Portal and select your application.

Navigate to URL Mapping under the Embedded App SDK section.

Map the base path / to your externally hosted application URL (you can use tools like ngrok or Cloudflare Tunnels to expose port 8000 for local development).

Launch the activity in a Discord Voice channel!

📝 Creating Custom Games (XML Format)
The game uses XML to structure the categories, questions, and answers. The host must upload an XML file to populate the game board.

Here is the basic structure based on the provided play_test.xml:

XML

<game>
    <category name="Pop Culture">
        <entry value="200">
            <question>This artist has the most streams on Spotify.</question>
            <answer>Taylor Swift</answer>
        </entry>
        
        <entry value="1000">
            <question>This publication shared the following video...</question>
            <video>[https://www.youtube.com/watch?v=SvZmRv6U_s0](https://www.youtube.com/watch?v=SvZmRv6U_s0)</video>
            <answer>Pitchfork</answer>
        </entry>
    </category>
    </game>
Host Instructions:
1. Start the game to generate a Room Code.

2. Upload your custom .xml file.

3. Click Load Game Board.

4. Have your players join using the room code.

5. Click a tile to reveal a question, Arm the Buzzer, wait for a player to buzz in, and award or subtract points based on their answer!
