document.addEventListener('DOMContentLoaded', () => {
    const socket = io({ transports: ['websocket', 'polling'] });
    let currentRoomCode = "";
    let isAdmin = false;
    let currentCatIdx = -1;
    let currentQIdx = -1;
    let pendingOverrideData = null;

    const buzzSound = new Audio('/static/audio/buzz_in.mp3');
    buzzSound.volume = 0.5;

    // --- REJOIN LOGIC (Check saved room code) ---
    //const savedRoom = sessionStorage.getItem('rejoin_room_code');
    // if (savedRoom) {
    //     document.getElementById('input-room-code').value = savedRoom;
    //     document.getElementById('screen-menu').classList.add('hidden');
    //     document.getElementById('screen-join-input').classList.remove('hidden');
    //     sessionStorage.removeItem('rejoin_room_code');
    // }

    // --- LISTENERS ---
    document.getElementById('btn-create').addEventListener('click', () => socket.emit('create_room'));

    document.getElementById('btn-show-join').addEventListener('click', () => {
        document.getElementById('screen-menu').classList.add('hidden');
        document.getElementById('screen-join-input').classList.remove('hidden');
    });

    document.getElementById('btn-back').addEventListener('click', () => location.reload());

    document.getElementById('btn-join-enter').addEventListener('click', () => {
        const code = document.getElementById('input-room-code').value.trim().toUpperCase();
        const name = document.getElementById('input-name').value.trim();
        if(!code || !name) return alert("Enter code and name");
        currentRoomCode = code;
        socket.emit('join_room', { code, name });
    });

    document.getElementById('btn-load-game').addEventListener('click', () => {
        const file = document.getElementById('file-upload').files[0];
        if (!file) return alert("Select an XML file first.");
        const reader = new FileReader();
        reader.onload = (e) => socket.emit('upload_game', { room_code: currentRoomCode, xml_content: e.target.result });
        reader.readAsText(file);
    });

    document.getElementById('btn-reveal').addEventListener('click', () => {
        socket.emit('trigger_reveal_answer', { room_code: currentRoomCode });
    });

    document.getElementById('btn-close').addEventListener('click', () => {
        socket.emit('close_question', { room_code: currentRoomCode, cat_idx: currentCatIdx, q_idx: currentQIdx });
    });

    document.getElementById('btn-arm').addEventListener('click', () => {
        socket.emit('arm_buzzer', { room_code: currentRoomCode });
    });

    document.getElementById('buzzer-btn').addEventListener('click', () => {
        if (!isAdmin) {
            socket.emit('player_buzz', { room_code: currentRoomCode });
        }
    });
  
    // --- CUSTOM MODAL LISTENERS ---
   document.getElementById('btn-override-yes').addEventListener('click', () => {
      if (pendingOverrideData) {
        currentRoomCode = pendingOverrideData.room_code;
        socket.emit('confirm_override', { code: pendingOverrideData.room_code, name: pendingOverrideData.name });

        // Hide the modal and clear the data
        document.getElementById('override-modal').classList.add('hidden');
        pendingOverrideData = null;
      }
    });

    document.getElementById('btn-override-no').addEventListener('click', () => {
      // Hide the modal
      document.getElementById('override-modal').classList.add('hidden');
      pendingOverrideData = null;

      // Clear the name input and focus it so they can try a new name
      document.getElementById('input-name').value = '';
      document.getElementById('input-name').focus();
    });

    document.getElementById('btn-ai-generate-trivia').addEventListener('click',()=>{
      const btn = document.getElementById('btn-ai-generate-trivia');
      btn.innerText("Generating a new trivia board...");
      btn.disable = true;
      btn.style.opacity = "0.5";
      socket.emit('ai_generate_trivia',{ room_code:currentRoomCode });
    });


    // --- SOCKET EVENTS ---
    socket.on('room_created', (data) => {
        isAdmin = true;
        currentRoomCode = data.code;
        document.getElementById('screen-menu').classList.add('hidden');
        document.getElementById('screen-admin').classList.remove('hidden');
        document.getElementById('room-code-display').innerText = data.code;
        document.getElementById('scoreboard-container').classList.remove('hidden');
    });

    socket.on('prompt_override', (data) => {
        // Store the data so the Yes/No buttons can use it
        pendingOverrideData = data;
        
        // Update the text and unhide our custom HTML modal
        document.getElementById('override-msg').innerText = data.msg;
        document.getElementById('override-modal').classList.remove('hidden');
    });

    socket.on('join_success', () => {
        document.getElementById('screen-join-input').classList.add('hidden');
        document.getElementById('screen-game').classList.remove('hidden');
        document.getElementById('scoreboard-container').classList.remove('hidden');
    });

    socket.on('update_players', (data) => renderScoreboard(data.players));

    socket.on('load_board', (data) => {
        document.getElementById('screen-admin').classList.add('hidden');
        document.getElementById('screen-game').classList.remove('hidden');
        document.getElementById('game-status').style.display = 'none';
        renderBoard(data.categories);
    });

    socket.on('show_question', (data) => {
        currentCatIdx = data.cat_idx;
        currentQIdx = data.q_idx;
        const overlay = document.getElementById('active-question-overlay');
        document.getElementById('question-text').innerText = data.text;
        
        // VIDEO LOGIC
        const vidContainer = document.getElementById('video-container');
        const vidFrame = document.getElementById('video-frame');
        if (data.video_id) {
            vidContainer.style.display = 'block';
            let embedUrl = `https://www.youtube.com/embed/${data.video_id}?autoplay=1`;
            if (data.video_start > 0) {
                embedUrl += `&start=${data.video_start}`;
            }
            vidFrame.src = embedUrl;
        } else {
            vidContainer.style.display = 'none';
            vidFrame.src = "";
        }

        const aText = document.getElementById('answer-text');
        aText.innerText = data.answer;
        overlay.classList.remove('hidden');

        if (isAdmin) {
            document.getElementById('admin-question-controls').classList.remove('hidden');
            aText.style.display = 'block';
            aText.className = 'answer-private';
            aText.innerHTML = "HOST VIEW: " + data.answer;
            
            document.getElementById('buzzer-area').classList.add('hidden');
            
            const info = document.getElementById('admin-buzzer-info');
            info.innerText = "Buzzer: LOCKED";
            info.style.color = "#ed4245"; 
        } else {
            document.getElementById('admin-question-controls').classList.add('hidden');
            aText.style.display = 'none';
            aText.className = '';
            
            document.getElementById('buzzer-area').classList.remove('hidden');
        }
    });

    socket.on('reveal_answer_to_all', () => {
        const aText = document.getElementById('answer-text');
        const rawAnswer = aText.innerText.replace("HOST VIEW: ", ""); 
        aText.innerText = rawAnswer;
        aText.style.display = 'block';
        aText.className = 'answer-public';
    });

    socket.on('hide_question', (data) => {
        document.getElementById('active-question-overlay').classList.add('hidden');
        document.getElementById('buzzer-area').classList.add('hidden');
        document.getElementById('video-frame').src = "";
        const tile = document.getElementById(`tile-${data.cat_idx}-${data.q_idx}`);
        if(tile) tile.classList.add('used');
    });

    socket.on('buzzer_state', (data) => {
        const btn = document.getElementById('buzzer-btn');
        
        if (data.locked) {
            btn.innerText = data.winner ? "BUZZED" : "LOCKED";
            btn.classList.remove('armed');
            btn.style.cursor = "not-allowed";
            btn.style.opacity = "0.5";
            
            if(data.winner){
                buzzSound.currentTime = 0;
                buzzSound.play().catch(err => console.log("Audio blocked by browser", err));
            }

        }else {
            btn.innerText = "BUZZ!";
            btn.classList.add('armed');
            btn.style.cursor = "pointer";
            btn.style.opacity = "1";
        }

        if (isAdmin) {
            const info = document.getElementById('admin-buzzer-info');
            if (!data.locked) {
                info.innerText = "Buzzer: ARMED (Waiting for buzz...)";
                info.style.color = "#3ba55c"; 
            } else if (data.winner) {
                info.innerText = `First to Buzz: ${data.winner}`;
                info.style.color = "#ffcc00"; 
            } else {
                info.innerText = "Buzzer: LOCKED";
                info.style.color = "#ed4245"; 
            }
        }
    });

    socket.on('new_trivia_generated',(data)=>{
      const btn = document.getElementById('btn-ai-generate-trivia');
      btn.innerText = "Generate Random Trivia XML";
      btn.disable = false;
      btn.style.opacity = "1";
      
      const blob = new Blob([data.xml_content],{type:'text/xml'});
      const file = new File([blob],'ai_generate_trivia.xml',{type:'text/xml'});

      const dataTransfer = new DataTransfer();
      dataTransfer.item.add(file);
      
      const fileInput = document.getElementById('file-upload');
      fileInput.files = dataTransfer.files;

      alert("Random trivia board generated successfully!");
    });

    function renderBoard(categories) {
        const board = document.getElementById('game-board');
        board.innerHTML = ''; 
        board.style.gridTemplateColumns = `repeat(${categories.length}, 1fr)`;

        categories.forEach(cat => {
            const div = document.createElement('div');
            div.className = 'category-header';
            div.innerText = cat.name;
            board.appendChild(div);
        });

        if(categories.length > 0) {
            const numQuestions = categories[0].questions.length;
            for (let q = 0; q < numQuestions; q++) {
                categories.forEach((cat, catIdx) => {
                    const qData = cat.questions[q];
                    const tile = document.createElement('div');
                    tile.className = 'question-tile';
                    tile.id = `tile-${catIdx}-${q}`;
                    tile.innerText = `$${qData.value}`;
                    if(qData.used) tile.classList.add('used');

                    tile.addEventListener('click', () => {
                        if(isAdmin) socket.emit('reveal_question', { room_code: currentRoomCode, cat_idx: catIdx, q_idx: q });
                    });
                    board.appendChild(tile);
                });
            }
        }
    }

    function renderScoreboard(players) {
        const sb = document.getElementById('scoreboard-container');
        sb.innerHTML = ''; 
        players.forEach((player, idx) => {
            const card = document.createElement('div');
            card.className = 'player-card';

            const name = document.createElement('div');
            name.className = 'player-name';
            name.innerText = player.name;
            
            const score = document.createElement('div');
            score.className = 'player-score';
            score.innerText = `$${player.score}`;

            card.appendChild(name);
            card.appendChild(score);

            if (isAdmin) {
                const controls = document.createElement('div');
                controls.className = 'score-controls';

                const btnSub = document.createElement('button');
                btnSub.className = 'btn-score';
                btnSub.innerText = '-';
                btnSub.style.backgroundColor = '#ed4245'; 
                btnSub.onclick = () => socket.emit('update_score', { room_code: currentRoomCode, player_idx: idx, action: 'sub' });

                const btnAdd = document.createElement('button');
                btnAdd.className = 'btn-score';
                btnAdd.innerText = '+';
                btnAdd.style.backgroundColor = '#3ba55c'; 
                btnAdd.onclick = () => socket.emit('update_score', { room_code: currentRoomCode, player_idx: idx, action: 'add' });

                controls.appendChild(btnSub);
                controls.appendChild(btnAdd);
                card.appendChild(controls);
            }
            sb.appendChild(card);
        });
    }
});
