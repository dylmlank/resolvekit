// ResolveKit panel — renderer. Talks to the local backend (server.py) over a
// WebSocket; the backend runs the Claude agent loop and drives DaVinci Resolve.

const BACKEND = 'ws://127.0.0.1:8765';

const $ = (id) => document.getElementById(id);
const statusEl = $('status');
const logEl = $('log');
let ws = null;
let busy = false;

function setStatus(state, text) {
    statusEl.className = 'status ' + state;
    statusEl.textContent = text;
}

function addLine(text, kind) {
    const div = document.createElement('div');
    div.className = 'line ' + (kind || '');
    div.textContent = text;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
}

function connect() {
    setStatus('connecting', 'connecting…');
    ws = new WebSocket(BACKEND);
    ws.onopen = () => setStatus('on', 'online');
    ws.onclose = () => {
        setStatus('off', 'offline');
        setTimeout(connect, 2000); // auto-reconnect
    };
    ws.onerror = () => setStatus('off', 'offline');
    ws.onmessage = (evt) => {
        let msg;
        try { msg = JSON.parse(evt.data); } catch { return; }
        if (msg.type === 'log') {
            addLine(msg.text, msg.text.startsWith('  · ') ? 'tool' : 'assistant');
        } else if (msg.type === 'error') {
            addLine('⚠ ' + msg.text, 'error');
        } else if (msg.type === 'done') {
            setBusy(false);
        }
    };
}

function setBusy(state) {
    busy = state;
    $('send').disabled = state;
    $('plan').disabled = state;
    document.querySelectorAll('.chips button').forEach((b) => (b.disabled = state));
}

function send(text) {
    if (!text || busy) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        addLine('⚠ Backend offline — start server.py (python server.py).', 'error');
        return;
    }
    addLine('› ' + text, 'user');
    setBusy(true);
    ws.send(JSON.stringify({ type: 'chat', text }));
}

// --- UI wiring -------------------------------------------------------------
$('plan').addEventListener('click', () => {
    const topic = $('topic').value.trim() || 'a short video';
    const mood = $('mood').value;
    const length = $('length').value;
    send(`Plan and script a ${length} ${mood} video about "${topic}". Save the ` +
         `script, create a new timeline named after the topic, lay the beats on ` +
         `it as markers, and add a title card for the opening hook.`);
});

const ACTIONS = {
    suggest: 'Read the current timeline and transcribe its clips if needed, then ' +
             'suggest cuts and pacing improvements as yellow marker notes.',
    voiceover: 'Generate a voiceover for the opening line of the current script ' +
               'using Resolve TTS and add it to the timeline.',
    media: 'Generate a placeholder b-roll image and a short music bed for the ' +
           'current topic, import them, and append to the timeline.',
    effects: 'Insert a Fusion title at the playhead and an OFX generator, so I ' +
             'have an intro card and a background to style.'
};

document.querySelectorAll('.chips button').forEach((btn) => {
    btn.addEventListener('click', () => send(ACTIONS[btn.dataset.action]));
});

$('send').addEventListener('click', () => {
    const el = $('chat');
    send(el.value.trim());
    el.value = '';
});
$('chat').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') $('send').click();
});

connect();
