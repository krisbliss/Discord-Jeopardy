import eventlet
eventlet.monkey_patch()

import os
import random
import string
import requests
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv
from modules.parsing import parse_jeopardy_xml
from modules.ai import generate_trivia_xml

load_dotenv() # pull in environment variables from .env file

app = Flask(__name__)
@app.after_request
def add_security_headers(response):
    # Explicitly allow Discord and the Discord proxy to frame your application
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://*.discord.com https://*.discordsays.com;"
    
    # Remove X-Frame-Options if it was injected by another service
    if 'X-Frame-Options' in response.headers:
        del response.headers['X-Frame-Options']
        
    return response

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret')
socketio = SocketIO(app, cors_allowed_origins="*")  # allow cross-origin requests from all sources

rooms = {} # Dict to hold all rooms and their current game states
"""
    rooms structure example:
    
    rooms[code] = {
        'admin_sid': '...',         <-- int sid value for admin user
        'players': [...],           <-- 'players' = [ # Note, this is a list of all player objects. navigate with ['players'][player_idx]
                                            {
                                                'sid': int_sid_id,
                                                'score': int_score
                                            },
                                            {Next player object...},
                                            {and so on...}
                                        ]
        'last_question_value': 0,   <-- int value updated after most recent active question is closed, starting value is always 0
        'buzzer_locked': True,      <--
        'buzzer_winner': None,      <--
        'game_state': None,         <-- 'game_state' = {
                                            'categories':[  # Note this is a list of category objects, navigate with ['categories'][cat_idx]
                                                {
                                                    'questions': [  # Note this is a list of question objects inside each category object, navigate with ['categories'][cat_idx]['questions'][q_idx]
                                                        { 
                                                            'question': "Text of the question",
                                                            'answer': "Text of the answer",
                                                            'value': "$200",
                                                            'video_id': "non-empty string if user added a video id"
                                                            'video_start': 0,
                                                            'used': boolean
                                                        },

                                                        {Next question...},
                                                        {and so on...}
                                                    ]
                                                },
                                                {Next category...},
                                                {and so on...}
                                            ]
                                        }
        'active_question': None     <-- tracks if a question is on screen
    }
"""

def generate_room_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

@app.route('/')  # default index page access
def index():
    return render_template('index.html',client_id=os.getenv('DISCORD_CLIENT_ID'))

@app.route('/api/token', methods=['POST']) # function for handling Discord SDK authorization
def token():
    code = request.json.get('code')  # grab temp code generated from frontend (Note: temp code is generated when index.html invokes  `window.DiscordSDK = DiscordSDK`)
    data = {
        'client_id': os.getenv('DISCORD_CLIENT_ID'),
        'client_secret': os.getenv('DISCORD_CLIENT_SECRET'),
        'grant_type': 'authorization_code',
        'code': code
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    return jsonify(r.json())


# --- Socket Events for dynamic frontend screen updates ---

@socketio.on('create_room')
def handle_create_room():
    room_code = generate_room_code()

    while room_code in rooms: # ensure room code generated is unique
        room_code = generate_room_code()

    rooms[room_code] = {
        'admin_sid': request.sid,
        'players': [],
        'last_question_value': 0,
        'buzzer_locked': True,
        'buzzer_winner': None,
        'game_state': None,
        'active_question': None
    }
    join_room(room_code)
    emit('room_created', {'code': room_code})



@socketio.on('join_room')
def handle_join_room(data):
    room_code = data.get('code','').upper()
    name = data.get('name')

    if room_code in rooms:
    # Check for duplicate player names
        existing_player = next((p for p in rooms[room_code]['players'] if p['name'] == name), None)
        if existing_player:
            emit('prompt_override',{
                'msg': 'You are about to override an existing player in the game, do you want to continue?',
                'room_code': room_code,
                'name': name
            }, to=request.sid)
            return

        # Normal join
        join_room(room_code)
        new_player = {'name': name, 'score': 0, 'sid': request.sid}
        rooms[room_code]['players'].append(new_player)

        emit('join_success', {'msg':'Joined!'}, to=request.sid)
        emit('update_players', {
            'players': rooms[room_code]['players'], 'buzzer_winner': rooms[room_code].get('buzzer_winner')
        }, to=room_code)

        # Sync State (Board state)
        if rooms[room_code].get('game_state'):
            emit('load_board',{
                'categories': rooms[room_code]['game_state']['categories']
            }, to=request.sid)

        # Sync State (Active Question)
        if rooms[room_code].get('active_question'):
            aq = rooms[room_code]['active_question']
            emit('show_question',aq, to=request.sid)
            if aq.get('revealed'):
                emit('reveal_answer_to_all',{}, to=request.sid)

    else:
        emit('error',{'msg': 'Room not found.'}, to=request.sid)


# override user with new sid
@socketio.on('confirm_override')
def handle_confirm_override(data):
    room_code = data.get('code','').upper()
    name = data.get('name')

    if room_code in rooms:
        for player in rooms[room_code]['players']:
            if player['name'] == name:

                # update the overridden player's sid
                player['sid'] = request.sid
                join_room(room_code)
                emit('join_success',{
                    'msg': 'Player sid override successful!'
                }, to=request.sid)

                # Resend Scores and Buzzer state
                emit('update_players', {
                    'players': rooms[room_code]['players'],
                    'buzzer_winner': rooms[room_code].get('buzzer_winner')
                }, to=request.sid)

                emit('buzzer_state',{
                    'locked': room[room_code].get('buzzer_locked',True),
                    'winner': rooms[room_code].get('buzzer_winner')
                }, to=request.sid)

                # Sync and resend game state (Game Board)
                if rooms[room_code].get('game_state'):
                    emit('load_board', {
                        'categories': rooms[room_code]['game_state']['categories']
                    }, to=request.sid)

                # Sync and resend game state (Active Question)
                if rooms[room_code].get('active_question'):
                    aq = rooms[room_code]['active_question']
                    emit('show_question', aq, to=request.sid)
                    if aq.get('revealed'):
                        emit('reveal_answer_to_all',{},to=request.sid)
                break

@socketio.on('ai_generate_trivia')
def handle_ai_generate_trivia(data):
    room_code = data.get('room_code')
    categories = data.get('categories')

    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        generated_trivia = generate_trivia_xml(categories)

        emit('new_trivia_generated',{
            'xml_content':generated_trivia
        }, to=request.sid)


@socketio.on('upload_game')
def handle_upload_game(data):
    room_code = data.get('room_code')
    xml_content = data.get('xml_content')
    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        game_data = parse_jeopardy_xml(xml_content)
        if game_data:
            rooms[room_code]['game_state'] = {'categories' : game_data}
            emit('load_board',{
                'categories': game_data
            }, to=room_code)

        else:
            emit('error',{
                'msg': 'Invalid XML'
            }, to=request.sid)


@socketio.on('reveal_question')
def handle_reveal(data):
    room_code = data.get('room_code')
    cat_idx = data.get('cat_idx')
    q_idx = data.get('q_idx')

    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        game = rooms[room_code]['game_state']['categories']
        question_data = game[cat_idx]['questions'][q_idx]
        
        # Save the active question state
        aq = {
            'text': question_data['question'],
            'answer': question_data['answer'],
            'value': question_data['value'],
            'video_id': question_data.get('video_id'),
            'source': question_data['source'],
            'cat_idx': cat_idx,
            'q_idx': q_idx,
            'revealed': False # default state before admin reveals answer
        }
        rooms[room_code]['active_question'] = aq
        emit('show_question', aq, to=room_code)

@socketio.on('trigger_reveal_answer')
def handle_trigger_reveal(data):
    room_code = data.get('room_code')
    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        if rooms[room_code].get('active_question'):
            rooms[room_code]['active_question']['revealed'] = True
        emit('reveal_answer_to_all', {}, to=room_code)


@socketio.on('close_question')
def handle_close(data):
    room_code = data.get('room_code')
    cat_idx = data.get('cat_idx')
    q_idx = data.get('q_idx')

    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        rooms[room_code]['game_state']['categories'][cat_idx]['questions'][q_idx]['used'] = True

        # Clear active question and lock buzzer
        rooms[room_code]['active_question'] = None
        rooms[room_code]['buzzer_locked'] = True
        rooms[room_code]['buzzer_winner'] = None

        emit('buzzer_state', {
            'locked': True, 
            'winner': None
        }, to=room_code)

        emit('update_players', {
            'players': rooms[room_code]['players'],
            'buzzer_winner': None
        }, to=room_code)

        dollar_value = rooms[room_code]['game_state']['categories'][cat_idx]['questions'][q_idx]['value']
        try:
            clean_val  = int(str(dollar_value).replace('$','').replace(',',''))
            rooms[room_code]['last_question_value'] = clean_val
        except:
            rooms[room_code]['last_question_value'] = 0

        emit('hide_question', {
            'cat_idx': cat_idx, 'q_idx': q_idx
        }, to=room_code)


@socketio.on('update_score')
def handle_score_update(data):
    room_code = data.get('room_code')
    player_idx = data.get('player_idx')
    action = data.get('action')

    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        points = rooms[room_code]['last_question_value']
        if 0 <= player_idx < len(rooms[room_code]['players']):
            if action == 'add':
                rooms[room_code]['players'][player_idx]['score'] += points
            elif action == 'sub':
                rooms[room_code]['players'][player_idx]['score'] -= points
            emit('update_players', {
                'players': rooms[room_code]['players'], 
                'buzzer_winner': rooms[room_code].get('buzzer_winner')
            }, to=room_code)


@socketio.on('arm_buzzer')
def handle_arm_buzzer(data):
    room_code = data.get('room_code')
    if rooms.get(room_code) and request.sid == rooms[room_code]['admin_sid']:
        rooms[room_code]['buzzer_locked'] = False
        rooms[room_code]['buzzer_winner'] = None

        emit('buzzer_state', {
            'locked': False, 'winner': None
        }, to=room_code)

        emit('update_players', {
            'players': rooms[room_code]['players'],
            'buzzer_winner': None
        }, to=room_code)


@socketio.on('player_buzz')
def handle_player_buzz(data):
    room_code = data.get('room_code')
    
    if rooms.get(room_code) and not rooms[room_code]['buzzer_locked']:
        rooms[room_code]['buzzer_locked'] = True
        winner_name = next((p['name'] for p in rooms[room_code]['players'] if p['sid'] == request.sid), "Unknown")
        rooms[room_code]['buzzer_winner'] = winner_name
        
        emit('buzzer_state',{
            'locked': True,
            'winner': winner_name
        }, to=room_code)

        emit('update_players',{
            'players':rooms[room_code]['players'],
            'buzzer_winner': winner_name
        },to=room_code)

if __name__ == '__main__':
    socketio.run(app,debug=True, port=8000, host='0.0.0.0')

