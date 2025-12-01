import random
import string
import logging
import json 
from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'avalon_secret_key_123456'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet') 

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- 游戏配置表 ---
DEFAULT_CONFIG = {
    '5': {'quests': [2, 3, 2, 3, 3], 'fails_needed': [1, 1, 1, 1, 1], 'default_roles': {'梅林': 1, '忠臣': 2, '莫甘娜': 1, '刺客': 1}},
    '6': {'quests': [2, 3, 4, 3, 4], 'fails_needed': [1, 1, 1, 1, 1], 'default_roles': {'梅林': 1, '派西维尔': 1, '忠臣': 2, '莫甘娜': 1, '刺客': 1}},
    '7': {'quests': [2, 3, 3, 4, 4], 'fails_needed': [1, 1, 1, 2, 1], 'default_roles': {'梅林': 1, '派西维尔': 1, '忠臣': 2, '莫甘娜': 1, '刺客': 1, '奥伯伦': 1}},
    '8': {'quests': [3, 4, 4, 5, 5], 'fails_needed': [1, 1, 1, 2, 1], 'default_roles': {'梅林': 1, '派西维尔': 1, '忠臣': 3, '莫甘娜': 1, '刺客': 1, '莫德雷德': 1}},
    '9': {'quests': [3, 4, 4, 5, 5], 'fails_needed': [1, 1, 1, 2, 1], 'default_roles': {'梅林': 1, '派西维尔': 1, '忠臣': 4, '莫甘娜': 1, '刺客': 1, '莫德雷德': 1}},
    '10': {'quests': [3, 4, 4, 5, 5], 'fails_needed': [1, 1, 1, 2, 1], 'default_roles': {'梅林': 1, '派西维尔': 1, '忠臣': 4, '莫甘娜': 1, '刺客': 1, '莫德雷德': 1, '奥伯伦': 1}}
}

rooms = {}
sid_map = {} 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>阿瓦隆 Avalon - 房间 {{ room_id }}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #1a202c; color: #e2e8f0; font-family: sans-serif; -webkit-tap-highlight-color: transparent; }
        .card { background-color: #2d3748; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .btn { width: 100%; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 8px; cursor: pointer; transition: 0.2s; }
        .btn:active { transform: scale(0.98); }
        .btn-blue { background-color: #3182ce; color: white; }
        .btn-green { background-color: #38a169; color: white; }
        .btn-red { background-color: #e53e3e; color: white; }
        .btn-purple { background-color: #805ad5; color: white; }
        .history-log { max-height: 250px; overflow-y: auto; font-size: 0.85em; background: #171923; padding: 10px; border-radius: 4px; border: 1px solid #4a5568;}
        .history-card { background-color: #242933; border: 1px solid #333946; padding: 10px; margin-bottom: 8px; border-radius: 6px; }
        
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 50; display: none; align-items: center; justify-content: center; }
        .modal-content { background: #2d3748; padding: 20px; border-radius: 10px; width: 90%; max-width: 400px; max-height: 80vh; overflow-y: auto; }
        
        /* 投票明细表格样式 */
        .vote-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 4px; margin-top: 6px; }
        .vote-item { background: #1a202c; padding: 4px; border-radius: 4px; text-align: center; font-size: 0.75rem; border-width: 1px; }
    </style>
</head>
<body class="p-4 text-sm">
    <div id="app" class="max-w-md mx-auto pb-10">
        <div class="flex justify-between items-center mb-4">
            <h1 class="text-xl font-bold text-yellow-500">⚔️ 阿瓦隆</h1>
            <span class="text-xs bg-gray-700 px-2 py-1 rounded text-gray-400">房号: {{ room_id }}</span>
        </div>
        
        <div id="login-screen" class="card">
            <h3 class="mb-3 text-lg font-bold">加入游戏</h3>
            <input type="text" id="username" placeholder="输入你的昵称" class="w-full p-3 text-black rounded border-none focus:ring-2 focus:ring-blue-500 mb-2">
            <button onclick="joinGame()" class="btn btn-blue">进入房间</button>
        </div>

        <div id="game-screen" style="display:none;">
            
            <div class="flex justify-between items-center mb-3 px-1">
                <span id="player-name" class="font-bold text-blue-300 text-lg"></span>
                <button onclick="toggleIdentity()" class="text-xs bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded transition">👁️ 查看身份</button>
            </div>
            
            <div id="identity-card" class="card bg-indigo-900 border-l-4 border-yellow-400" style="display:none;">
                <p class="text-lg">你的角色: <span id="my-role" class="font-bold text-yellow-300">???</span></p>
                <p class="text-sm text-gray-300 mt-1" id="my-info"></p>
                <div id="assassin-area" class="mt-4 pt-4 border-t border-indigo-700" style="display:none;">
                    <p class="text-xs text-red-300 mb-1">🗡️ 刺客技能</p>
                    <button onclick="openAssassinModal()" class="w-auto px-4 py-2 bg-red-700 hover:bg-red-600 text-white text-xs rounded shadow-md">
                        ☠️ 刺杀梅林
                    </button>
                </div>
            </div>

            <div id="status-area" class="card text-center relative overflow-hidden">
                <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
                <h2 id="phase-text" class="text-xl font-bold text-green-400 mt-1">等待开始...</h2>
                <div class="flex justify-around mt-3 text-sm text-gray-400">
                    <div class="flex flex-col">
                        <span class="text-xs uppercase">当前任务</span>
                        <span class="text-lg text-white font-mono"><span id="quest-round">1</span>/5</span>
                    </div>
                    <div class="flex flex-col">
                        <span class="text-xs uppercase">流局次数</span>
                        <span class="text-lg text-red-400 font-mono"><span id="vote-track">0</span>/5</span>
                    </div>
                </div>
                <div id="captain-order" class="mt-3 text-xs text-gray-400 p-2 bg-gray-700 rounded-md">
                    <span class="font-bold text-blue-300">队长轮换:</span> <span id="captain-list"></span>
                </div>
                <div id="quest-board" class="flex justify-center gap-2 mt-4"></div>
            </div>

            <div id="action-area" class="card border border-gray-600">
                <p id="instruction-text" class="mb-3 text-center text-gray-300 font-medium">等待房主...</p>
                
                <div id="host-controls" style="display:none;">
                    <p class="text-xs text-gray-500 mb-2">已加入玩家 (<span id="player-count">0</span>):</p>
                    <ul id="lobby-list" class="grid grid-cols-2 gap-1 mb-4 text-xs text-gray-300"></ul>
                    <h4 class="font-bold text-base mb-2 text-yellow-300">⚙️ 游戏配置</h4>
                    <select id="player-limit" onchange="updateRoleSettings()" class="w-full bg-gray-800 p-2 rounded text-white mb-3">
                        <option value="5">5人</option>
                        <option value="6">6人</option>
                        <option value="7">7人</option>
                        <option value="8">8人</option>
                        <option value="9" selected>9人</option>
                        <option value="10">10人</option>
                    </select>
                    <div id="role-settings" class="mb-4">
                        <div id="role-inputs" class="grid grid-cols-2 gap-2"></div>
                        <p id="role-total" class="mt-2 text-sm text-center font-bold"></p>
                    </div>
                    <div class="mb-4">
                        <label class="flex items-center space-x-2 text-sm bg-gray-700 p-2 rounded">
                            <input type="checkbox" id="assassin-anytime" class="form-checkbox text-blue-600">
                            <span>刺客可随时行使权利</span>
                        </label>
                    </div>
                    <button onclick="startGame()" id="start-btn" class="btn btn-green shadow-lg">🚀 开始游戏</button>
                </div>

                <div id="restart-controls" style="display:none;">
                    <button onclick="resetGame()" class="btn btn-purple shadow-lg">🔄 重置游戏 (回到大厅)</button>
                </div>

                <div id="team-select-controls" style="display:none;">
                    <p class="text-sm mb-2 text-center">本轮需要 <span id="needed-count" class="font-bold text-red-400 text-lg">0</span> 人</p>
                    <div id="player-checkboxes" class="grid grid-cols-2 gap-2 text-sm bg-gray-800 p-2 rounded"></div>
                    <button onclick="submitTeam()" class="btn btn-blue">✅ 确认提议</button>
                </div>

                <div id="voting-controls" style="display:none;">
                    <p class="mb-2 font-bold text-center">是否同意该队伍出发？</p>
                    <div class="flex gap-3">
                        <button onclick="voteTeam(true)" class="btn btn-green">同意</button>
                        <button onclick="voteTeam(false)" class="btn btn-red">反对</button>
                    </div>
                </div>

                <div id="mission-controls" style="display:none;">
                    <p class="mb-2 font-bold text-center text-red-400 animate-pulse">⚠️ 请执行任务</p>
                    <div id="mission-btns" class="flex gap-3"></div>
                </div>
            </div>

            <div class="card">
                <h3 class="text-xs font-bold mb-2 text-gray-500 uppercase tracking-wider">📜 游戏进程</h3>
                <div id="game-logs" class="history-log font-mono"></div>
            </div>
            
            <div class="card">
                <h3 class="text-xs font-bold mb-3 text-gray-500 uppercase tracking-wider">📊 历史记录</h3>
                <div id="game-history"></div>
            </div>
        </div>
    </div>

    <div id="assassin-modal" class="modal-overlay">
        <div class="modal-content text-center">
            <h3 class="text-2xl font-bold text-red-500 mb-2">☠️ 选择刺杀目标</h3>
            <p class="text-gray-400 text-sm mb-4">猜对梅林则坏人直接胜利。</p>
            <div id="assassin-targets" class="grid grid-cols-2 gap-2 mb-4"></div>
            <button onclick="closeAssassinModal()" class="w-full py-3 bg-gray-600 rounded text-white font-bold">取消返回</button>
        </div>
    </div>

    <script>
        const socket = io();
        const roomId = "{{ room_id }}";
        let myName = "";
        let currentPlayers = [];
        const CONFIGS = JSON.parse('{{ config_json|safe }}');

        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('player-limit').value = '9';
            updateRoleSettings();
        });

        function updateRoleSettings() {
            const count = parseInt(document.getElementById('player-limit').value);
            const config = CONFIGS[count];
            const roleInputsDiv = document.getElementById('role-inputs');
            
            let defaultRoles = {
                '梅林': 1, '派西维尔': config.default_roles['派西维尔'] || 0,
                '莫甘娜': config.default_roles['莫甘娜'] || 0, '刺客': 1,
                '莫德雷德': config.default_roles['莫德雷德'] || 0, '奥伯伦': config.default_roles['奥伯伦'] || 0,
                '普通坏人': 0
            };
            let baseGood = count;
            Object.values(defaultRoles).forEach(c => baseGood -= c);
            defaultRoles['忠臣'] = baseGood;

            let html = '';
            html += generateRoleInput('忠臣', '忠臣', defaultRoles['忠臣'], 'text-green-400');
            html += generateRoleInput('梅林', '梅林', defaultRoles['梅林'], 'text-green-400');
            html += generateRoleInput('派西维尔', '派西维尔', defaultRoles['派西维尔'], 'text-green-400');
            html += `<div class="col-span-2 h-px bg-gray-700 my-1"></div>`;
            html += generateRoleInput('莫甘娜', '莫甘娜', defaultRoles['莫甘娜'], 'text-red-400');
            html += generateRoleInput('刺客', '刺客', defaultRoles['刺客'], 'text-red-400');
            html += generateRoleInput('普通坏人', '普通坏人', defaultRoles['普通坏人'], 'text-red-400');
            html += generateRoleInput('莫德雷德', '莫德雷德', defaultRoles['莫德雷德'], 'text-red-400');
            html += generateRoleInput('奥伯伦', '奥伯伦', defaultRoles['奥伯伦'], 'text-red-400');
            roleInputsDiv.innerHTML = html;
            updateRoleTotal();
        }
        
        function generateRoleInput(id, label, defaultValue, colorClass) {
            const max = parseInt(document.getElementById('player-limit').value);
            return `<div class="flex justify-between items-center bg-gray-800 p-2 rounded">
                        <span class="${colorClass} text-xs font-bold">${label}</span>
                        <input type="number" id="role-${id}" value="${defaultValue}" min="0" max="${max}" 
                               onchange="updateRoleTotal()" class="w-12 p-1 text-center bg-gray-900 text-white rounded">
                    </div>`;
        }
        
        function updateRoleTotal() {
            const count = parseInt(document.getElementById('player-limit').value);
            let total = 0;
            document.querySelectorAll('#role-inputs input[type="number"]').forEach(input => total += parseInt(input.value || 0));
            const startBtn = document.getElementById('start-btn');
            const totalEl = document.getElementById('role-total');
            
            if (total === count) {
                totalEl.innerHTML = `<span class="text-green-500">角色总数: ${total} / ${count} (正常)</span>`;
                startBtn.disabled = false;
                startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                totalEl.innerHTML = `<span class="text-red-500">角色总数: ${total} / ${count} (不匹配)</span>`;
                startBtn.disabled = true;
                startBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }
        
        function joinGame() {
            myName = document.getElementById('username').value.trim();
            if(!myName) return alert("起个名字吧！");
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('game-screen').style.display = 'block';
            document.getElementById('player-name').innerText = myName;
            socket.emit('join', {room: roomId, name: myName});
        }

        function toggleIdentity() {
            const el = document.getElementById('identity-card');
            el.style.display = el.style.display === 'none' ? 'block' : 'none';
        }

        function startGame() {
            const count = parseInt(document.getElementById('player-limit').value);
            let roles = {};
            document.querySelectorAll('#role-inputs input[type="number"]').forEach(input => {
                roles[input.id.replace('role-', '')] = parseInt(input.value || 0);
            });
            socket.emit('start_game', {
                room: roomId,
                config: { player_count: count, roles: roles, assassin_anytime: document.getElementById('assassin-anytime').checked }
            });
        }
        
        function resetGame() {
            if(!confirm("确定要重置游戏吗？所有人将回到大厅重新分配角色。")) return;
            socket.emit('reset_game', {room: roomId});
        }

        function submitTeam() {
            const checkboxes = document.querySelectorAll('input[name="team_select"]:checked');
            const team = Array.from(checkboxes).map(c => c.value);
            socket.emit('propose_team', {room: roomId, team: team});
        }

        function voteTeam(approve) {
            socket.emit('vote_team', {room: roomId, approve: approve});
            document.getElementById('voting-controls').style.display = 'none';
            document.getElementById('instruction-text').innerText = "已投票，等待其他人...";
        }

        function doQuest(success) {
            if(!confirm("确认选择 " + (success ? "【成功】" : "【失败】") + " 吗？")) return;
            socket.emit('do_quest', {room: roomId, success: success});
            document.getElementById('mission-controls').style.display = 'none';
        }

        function openAssassinModal() {
            const container = document.getElementById('assassin-targets');
            container.innerHTML = currentPlayers.map(p => {
                if(p === myName) return '';
                return `<button onclick="confirmAssassinate('${p}')" class="p-3 bg-gray-700 hover:bg-red-900 border border-gray-600 rounded text-white font-bold transition">
                            ${p}
                        </button>`;
            }).join('');
            document.getElementById('assassin-modal').style.display = 'flex';
        }

        function closeAssassinModal() {
            document.getElementById('assassin-modal').style.display = 'none';
        }

        function confirmAssassinate(target) {
            if(confirm(`🗡️ 确认要刺杀 [${target}] 吗？`)) {
                socket.emit('assassinate', {room: roomId, target: target});
                closeAssassinModal();
            }
        }

        socket.on('update_state', (data) => {
            currentPlayers = data.players;
            renderGame(data);
        });

        socket.on('notification', (msg) => { alert(msg); });

        function renderGame(data) {
            document.getElementById('player-count').innerText = data.players.length;
            document.getElementById('lobby-list').innerHTML = data.players.map(p => 
                `<li>👤 ${p} ${data.phase !== 'LOBBY' && data.players[data.captain_index] === p ? '👑' : ''}</li>`
            ).join('');
            
            const isHost = data.players[0] === myName;
            document.getElementById('host-controls').style.display = (data.phase === 'LOBBY' && isHost) ? 'block' : 'none';
            document.getElementById('restart-controls').style.display = 'none'; // 默认隐藏
            
            ['team-select-controls', 'voting-controls', 'mission-controls'].forEach(id => 
                document.getElementById(id).style.display = 'none'
            );
            
            const logs = document.getElementById('game-logs');
            logs.innerHTML = data.logs.map(l => `<div class="mb-1 border-b border-gray-700 pb-1">${l}</div>`).join('');
            logs.scrollTop = logs.scrollHeight;

            document.getElementById('phase-text').innerText = getPhaseText(data.phase, data);
            
            if (data.phase !== 'LOBBY') {
                document.getElementById('quest-round').innerText = data.current_quest + 1;
                document.getElementById('vote-track').innerText = `${data.failed_votes}/${data.max_failed_votes}`;
                
                renderQuestBoard(data);
                renderHistory(data);
                
                let orderHtml = [];
                for(let i=0; i<5; i++) {
                    let idx = (data.captain_index + i) % data.players.length;
                    let p = data.players[idx];
                    let style = i === 0 ? "text-yellow-400 font-bold border-b border-yellow-500" : "text-gray-500";
                    orderHtml.push(`<span class="${style}">${p}</span>`);
                }
                document.getElementById('captain-list').innerHTML = orderHtml.join(' → ');
            }

            if (data.role_map && data.role_map[myName]) {
                const myData = data.role_map[myName];
                document.getElementById('my-role').innerText = myData.role;
                document.getElementById('my-info').innerText = myData.info;
                
                const isAssassin = myData.role === '刺客';
                const canAssassinate = (data.phase === 'ASSASSINATION') || (isAssassin && data.assassin_anytime && data.phase !== 'GAME_OVER' && data.phase !== 'LOBBY');
                
                const assassinArea = document.getElementById('assassin-area');
                if (isAssassin) {
                    assassinArea.style.display = 'block';
                    const btn = assassinArea.querySelector('button');
                    btn.disabled = !canAssassinate;
                    btn.classList.toggle('opacity-50', !canAssassinate);
                    btn.classList.toggle('cursor-not-allowed', !canAssassinate);
                    btn.innerText = canAssassinate ? "☠️ 刺杀梅林 (点击选择)" : "☠️ 刺杀梅林 (暂不可用)";
                } else {
                    assassinArea.style.display = 'none';
                }
                renderActionControls(data, myData, isHost);
            }
        }

        function renderActionControls(data, myData, isHost) {
            const captain = data.players[data.captain_index];
            const instruction = document.getElementById('instruction-text');

            if (data.phase === 'PROPOSING') {
                instruction.innerText = `等待队长 [${captain}] 选人...`;
                if (myName === captain) {
                    document.getElementById('team-select-controls').style.display = 'block';
                    document.getElementById('needed-count').innerText = data.quests_config[data.current_quest];
                    document.getElementById('player-checkboxes').innerHTML = data.players.map(p =>
                        `<label class="flex items-center space-x-2 cursor-pointer bg-gray-700 p-2 rounded hover:bg-gray-600">
                            <input type="checkbox" name="team_select" value="${p}" class="form-checkbox h-4 w-4 text-blue-600">
                            <span>${p}</span>
                        </label>`
                    ).join('');
                }
            }
            else if (data.phase === 'VOTING') {
                const notVoted = data.players.filter(p => !data.votes.hasOwnProperty(p));
                instruction.innerHTML = `队长 [${captain}] 提议: <span class="text-yellow-300">${data.current_team.join(', ')}</span><br>
                                       <span class="text-xs text-gray-500">等待投票: ${notVoted.length}人</span>`;
                if (!data.votes.hasOwnProperty(myName)) {
                    document.getElementById('voting-controls').style.display = 'block';
                }
            }
            else if (data.phase === 'QUEST') {
                const notActed = data.current_team.filter(p => !data.quest_votes.hasOwnProperty(p));
                instruction.innerHTML = `执行任务中... <span class="text-xs text-gray-500">等待: ${notActed.length}人</span>`;
                if (data.current_team.includes(myName) && !data.quest_votes.hasOwnProperty(myName)) {
                    document.getElementById('mission-controls').style.display = 'block';
                    const btnContainer = document.getElementById('mission-btns');
                    const goodRoles = ['梅林', '派西维尔', '忠臣'];
                    const isGood = goodRoles.includes(myData.role);
                    if (isGood) {
                        btnContainer.innerHTML = `<button onclick="doQuest(true)" class="btn btn-blue w-full">✨ 任务成功</button>`;
                    } else {
                        btnContainer.innerHTML = `<button onclick="doQuest(true)" class="btn btn-blue w-1/2">✨ 任务成功</button>
                                                  <button onclick="doQuest(false)" class="btn btn-red w-1/2">☠️ 任务失败</button>`;
                    }
                }
            }
            else if (data.phase === 'ASSASSINATION') {
                instruction.innerHTML = `<span class="text-red-500 font-bold animate-pulse">好人任务胜利！刺客正在寻找梅林...</span>`;
            }
            else if (data.phase === 'GAME_OVER') {
                // 修改点1：不再闪烁“寻找梅林”，直接显示结果
                instruction.innerHTML = `<div class="text-2xl font-bold text-yellow-400 p-2 border-2 border-yellow-600 rounded bg-gray-800">${data.winner}</div>`;
                
                // 修改点3：显示重置按钮
                if (isHost) {
                    document.getElementById('restart-controls').style.display = 'block';
                }
            }
        }

        function getPhaseText(phase, data) {
            const map = {'LOBBY':'😴 游戏大厅', 'PROPOSING':'👑 队长选人', 'VOTING':'🗳️ 全员投票', 'QUEST':'⚔️ 执行任务', 'ASSASSINATION':'🗡️ 刺客时刻', 'GAME_OVER':'🏆 游戏结束'};
            return map[phase] || phase;
        }

        function renderQuestBoard(data) {
            const board = document.getElementById('quest-board');
            let html = '';
            data.quests_config.forEach((num, idx) => {
                let statusClass = 'bg-gray-700 text-gray-400';
                let content = num;
                
                if (idx < data.quest_results.length) {
                    if (data.quest_results[idx]) {
                        statusClass = 'bg-blue-600 text-white border-2 border-blue-400';
                        content = '✨';
                    } else {
                        statusClass = 'bg-red-600 text-white border-2 border-red-400';
                        content = '☠️';
                    }
                } else if (idx === data.current_quest) {
                    statusClass = 'bg-yellow-600 text-white animate-pulse border-2 border-yellow-400';
                }
                
                const failNeeded = data.fails_needed[idx];
                const failText = failNeeded > 1 ? `需${failNeeded}败` : `需1败`;
                
                html += `<div class="flex flex-col items-center">
                            <div class="relative w-10 h-10 rounded-full flex items-center justify-center font-bold shadow-md ${statusClass} z-10">
                                ${content}
                            </div>
                            <span class="text-[10px] mt-1 text-gray-400 bg-gray-800 px-1 rounded border border-gray-600">${failText}</span>
                         </div>`;
            });
            board.innerHTML = html;
        }

        function renderHistory(data) {
            const historyDiv = document.getElementById('game-history');
            if (data.history.length === 0) {
                 historyDiv.innerHTML = '<p class="text-gray-500 text-center text-xs">暂无历史...</p>';
                 return;
            }
            
            historyDiv.innerHTML = data.history.map(quest => {
                const resClass = quest.result === '成功' ? 'text-blue-400' : 'text-red-400';
                
                const proposalsHtml = quest.proposals.map(prop => {
                    const resultIcon = prop.vote_result === '通过' ? '✅' : '❌';
                    const resultColor = prop.vote_result === '通过' ? 'text-green-400' : 'text-gray-400';
                    
                    // 修改点2：投票结果改为绿色文字“同意”，红色“反对”
                    const voteDetailsHtml = Object.entries(prop.votes).map(([pName, voteVal]) => {
                        const vColor = voteVal ? 'text-green-400 border-green-600' : 'text-red-400 border-red-600';
                        const vText = voteVal ? '同意' : '反对';
                        return `<div class="vote-item border ${vColor}">
                                    <div class="font-bold truncate text-gray-300">${pName}</div>
                                    <div class="font-bold">${vText}</div>
                                </div>`;
                    }).join('');

                    return `
                        <div class="mb-3 pl-3 border-l-2 border-gray-600">
                            <div class="flex justify-between items-center text-xs mb-1">
                                <span class="font-bold text-gray-300">队长: ${prop.captain}</span>
                                <span class="${resultColor} font-bold border border-gray-600 px-1 rounded">${resultIcon} ${prop.vote_result}</span>
                            </div>
                            <div class="text-xs text-yellow-500 mb-1">
                                提议: [${prop.team.join(', ')}]
                            </div>
                            <div class="vote-grid">
                                ${voteDetailsHtml}
                            </div>
                        </div>
                    `;
                }).join('');

                return `
                    <div class="history-card">
                        <div class="flex justify-between border-b border-gray-500 pb-2 mb-2 bg-gray-800 p-2 rounded-t">
                            <span class="font-bold text-white text-sm">第 ${quest.quest_number} 轮任务</span>
                            <span class="${resClass} font-bold text-sm">${quest.result}</span>
                        </div>
                        <div class="flex justify-center gap-4 text-xs font-mono bg-gray-900 p-2 rounded mb-3">
                            <span class="text-blue-300">✨ 成功票: ${quest.success_votes}</span>
                            <span class="text-red-300">☠️ 失败票: ${quest.fail_votes}</span>
                        </div>
                        <div class="space-y-2">
                            ${proposalsHtml}
                        </div>
                    </div>
                `;
            }).join('');
        }
    </script>
</body>
</html>
"""
CONFIG_JSON = json.dumps(DEFAULT_CONFIG)

def get_room(room_id):
    if room_id not in rooms:
        rooms[room_id] = {
            'phase': 'LOBBY',
            'players': [],
            'role_map': {},
            'captain_index': 0,
            'current_quest': 0,
            'failed_votes': 0,
            'current_team': [],
            'votes': {},
            'quest_votes': {},
            'quest_results': [],
            'logs': ['👋 欢迎来到阿瓦隆。'],
            'quests_config': [],
            'fails_needed': [],
            'winner': None,
            'history': [],
            'current_quest_proposals': [],
            'max_failed_votes': 5,
            'assassin_anytime': False
        }
    return rooms[room_id]

@app.route('/')
def index():
    room = request.args.get('room')
    if not room:
        room = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f'<script>window.location.href="/?room={room}"</script>'
    return render_template_string(HTML_TEMPLATE, room_id=room, config_json=CONFIG_JSON)

@socketio.on('join')
def on_join(data):
    room_id = data['room']
    name = data['name']
    sid_map[request.sid] = name
    join_room(room_id)
    room = get_room(room_id)

    if room['phase'] != 'LOBBY':
        if name in room['players']:
             emit('notification', '你已在游戏中。', room=request.sid)
        else:
             emit('notification', '游戏已开始，你只能旁观。', room=request.sid)
             emit('update_state', room, room=request.sid) 
             return

    if name not in room['players']:
        room['players'].append(name)
        room['logs'].append(f"👋 {name} 进场了")
    
    emit('update_state', room, room=room_id)

@socketio.on('start_game')
def on_start(data):
    room = get_room(data['room'])
    cfg = data['config']
    
    if len(room['players']) < cfg['player_count']:
        emit('notification', '人数不足', room=request.sid)
        return
        
    room['max_failed_votes'] = 5
    room['assassin_anytime'] = cfg['assassin_anytime']
    q_cfg = DEFAULT_CONFIG[str(cfg['player_count'])]
    room['quests_config'] = q_cfg['quests']
    room['fails_needed'] = q_cfg['fails_needed']
    
    roles_list = []
    for role, count in cfg['roles'].items():
        roles_list.extend([role] * count)
    
    if len(roles_list) != cfg['player_count']:
        emit('notification', f'角色配置错误: {len(roles_list)} != {cfg["player_count"]}', room=request.sid)
        return

    random.shuffle(roles_list)
    room['role_map'] = {}
    
    evil_team = [] 
    for i, p in enumerate(room['players']):
        if i >= len(roles_list): break
        r = roles_list[i]
        if r in ['莫甘娜', '刺客', '莫德雷德', '普通坏人']:
            evil_team.append(p)
    
    merlin_seen = []
    for i, p in enumerate(room['players']):
        if i >= len(roles_list): break
        r = roles_list[i]
        if r in ['莫甘娜', '刺客', '奥伯伦', '普通坏人']:
            merlin_seen.append(p)

    for i, p in enumerate(room['players']):
        if i >= len(roles_list): break
        role = roles_list[i]
        info = "普通好人，无特殊视野。"
        if role == '梅林':
            info = f"👀 你看见的坏人: {', '.join(merlin_seen)}"
        elif role == '派西维尔':
            targets = [n for idx, n in enumerate(room['players']) if idx < len(roles_list) and roles_list[idx] in ['梅林', '莫甘娜']]
            random.shuffle(targets)
            info = f"👀 你看见了: {', '.join(targets)} (分不清梅林/莫甘娜)"
        elif role in ['莫甘娜', '刺客', '莫德雷德', '普通坏人']:
            others = [e for e in evil_team if e != p]
            info = f"😈 你的坏人队友: {', '.join(others)}"
        elif role == '奥伯伦':
            info = "😈 你是坏人，但你看不到队友，队友也看不到你。"
        room['role_map'][p] = {'role': role, 'info': info}

    room['phase'] = 'PROPOSING'
    room['captain_index'] = random.randint(0, len(room['players'])-1)
    room['logs'].append("🎮 游戏开始！身份已发放。")
    emit('update_state', room, room=data['room'])

# --- 修改点3：重置游戏功能 ---
@socketio.on('reset_game')
def on_reset(data):
    room = get_room(data['room'])
    
    # 仅重置游戏状态，保留玩家列表
    room['phase'] = 'LOBBY'
    room['role_map'] = {}
    room['captain_index'] = 0
    room['current_quest'] = 0
    room['failed_votes'] = 0
    room['current_team'] = []
    room['votes'] = {}
    room['quest_votes'] = {}
    room['quest_results'] = []
    room['history'] = []
    room['current_quest_proposals'] = []
    room['winner'] = None
    
    room['logs'].append("🔄 房主重置了游戏，回到大厅，请重新配置。")
    emit('update_state', room, room=data['room'])

@socketio.on('propose_team')
def on_propose(data):
    room = get_room(data['room'])
    room['current_team'] = data['team']
    room['phase'] = 'VOTING'
    room['votes'] = {}
    room['logs'].append(f"📋 队长 [{room['players'][room['captain_index']]}] 提议: {', '.join(data['team'])}")
    emit('update_state', room, room=data['room'])

@socketio.on('vote_team')
def on_vote(data):
    room = get_room(data['room'])
    user = sid_map[request.sid]
    room['votes'][user] = data['approve']
    
    if len(room['votes']) == len(room['players']):
        yes = sum(1 for v in room['votes'].values() if v)
        no = len(room['players']) - yes
        
        proposal = {
            'captain': room['players'][room['captain_index']],
            'team': room['current_team'],
            'votes': room['votes'].copy(),
            'vote_result': '通过' if yes > no else '不通过',
        }
        room['current_quest_proposals'].append(proposal)
        
        room['logs'].append(f"🗳️ 投票结果: {yes}赞成 / {no}反对")
        
        if yes > no:
            room['phase'] = 'QUEST'
            room['quest_votes'] = {}
            room['failed_votes'] = 0
            room['logs'].append("✅ 队伍出发，开始做任务...")
        else:
            room['failed_votes'] += 1
            if room['failed_votes'] >= room['max_failed_votes']:
                room['phase'] = 'GAME_OVER'
                room['winner'] = '坏人获胜 (流局次数耗尽)'
                room['logs'].append("❌ 连续流局达到上限，坏人直接获胜！")
            else:
                room['captain_index'] = (room['captain_index'] + 1) % len(room['players'])
                room['phase'] = 'PROPOSING'
                room['logs'].append(f"❌ 提议被否决 (流局 {room['failed_votes']})")
                
    emit('update_state', room, room=data['room'])

@socketio.on('do_quest')
def on_quest(data):
    room = get_room(data['room'])
    user = sid_map[request.sid]
    
    role = room['role_map'][user]['role']
    is_good = role in ['梅林', '派西维尔', '忠臣']
    vote_val = True if is_good else data['success']
    
    room['quest_votes'][user] = vote_val
    
    if len(room['quest_votes']) == len(room['current_team']):
        fails = sum(1 for v in room['quest_votes'].values() if not v)
        required = room['fails_needed'][room['current_quest']]
        success = fails < required
        
        room['quest_results'].append(success)
        
        room['history'].append({
            'quest_number': room['current_quest'] + 1,
            'result': '成功' if success else '失败',
            'success_votes': len(room['current_team']) - fails,
            'fail_votes': fails,
            'proposals': room['current_quest_proposals']
        })
        room['current_quest_proposals'] = []
        
        result_text = "✨ 成功" if success else "☠️ 失败"
        room['logs'].append(f"任务 {room['current_quest']+1} 结果: {result_text} (失败票: {fails})")
        
        wins = sum(1 for r in room['quest_results'] if r)
        losses = sum(1 for r in room['quest_results'] if not r)
        
        if wins >= 3:
            room['phase'] = 'ASSASSINATION'
            room['logs'].append("🎉 好人方赢得了3个任务！进入刺杀时刻...")
            room['logs'].append("🗡️ 请刺客寻找梅林，一击定胜负！")
        elif losses >= 3:
            room['phase'] = 'GAME_OVER'
            room['logs'].append("💀 坏人方破坏了3个任务，坏人获胜！")
            room['winner'] = '坏人获胜 (任务失败3次)'
        else:
            room['current_quest'] += 1
            room['captain_index'] = (room['captain_index'] + 1) % len(room['players'])
            room['phase'] = 'PROPOSING'
            
    emit('update_state', room, room=data['room'])

@socketio.on('assassinate')
def on_assassinate(data):
    room = get_room(data['room'])
    user = sid_map[request.sid]
    target = data['target']
    if room['role_map'][user]['role'] != '刺客': return
    
    target_role = room['role_map'][target]['role']
    room['phase'] = 'GAME_OVER'
    room['logs'].append(f"🗡️ 刺客 [{user}] 选择刺杀 [{target}]...")
    
    if target_role == '梅林':
        room['logs'].append(f"🩸 [{target}] 竟然真的是梅林！刺杀成功！")
        room['winner'] = '坏人获胜 (刺杀梅林成功)'
    else:
        room['logs'].append(f"🛡️ [{target}] 并不是梅林 (身份是 {target_role})。刺杀失败！")
        room['winner'] = '好人获胜 (刺杀梅林失败)'
        
    emit('update_state', room, room=data['room'])

# if __name__ == '__main__':
#     socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)