/* ═══════════════════════════════════════════════════════
   chatbot-widget.js  —  다미푸드 플로팅 챗봇 위젯
   index.html 하단 <script src="/static/js/chatbot-widget.js"> 로 로드
   API: POST /api/chat
═══════════════════════════════════════════════════════ */

/* ── 다국어 텍스트 ── */
const CW_LANG = {
  ko: {
    hello: '안녕하세요! 🐉',
    help: '무엇을 도와드릴까요?',
    placeholder: '메시지를 입력하세요...',
    send: '➤',
    loading: '용담이가 생각 중이에요... 🍳',
    error: '오류가 발생했어요. 다시 시도해 주세요.',
    selectCategory: '카테고리를 선택하세요:',
    selectTaste: '어떤 맛을 원하세요?',
    resetDone: '대화가 초기화되었어요!',
    categories: ['🍲 국물·탕','🍜 면·볶음면','🥩 구이·볶음','🥗 쌈·샐러드','🍚 밥·죽','🧋 간식·음료'],
    tastes: ['🌶️ 매운','🥜 고소','💧 담백','🍯 달콤','🍋 새콤','🧂 짭짤','🍘 바삭','✨ 감칠맛','🔥 얼큰'],
    quickActions: ['🍜 쌀국수 레시피','🥩 불고기 레시피','🥗 비건 요리','🎲 랜덤 추천'],
    guidedUserMsg: (cat, taste) => `📋 가이드 추천: ${cat} + ${taste} 맛`,
    randomUserMsg: '🎲 랜덤 레시피 추천해 주세요!',
  },
  vi: {
    hello: 'Xin chào! 🐉',
    help: 'Tôi có thể giúp gì cho bạn?',
    placeholder: 'Nhập tin nhắn...',
    send: '➤',
    loading: 'Yongdami đang suy nghĩ... 🍳',
    error: 'Đã xảy ra lỗi. Vui lòng thử lại.',
    selectCategory: 'Chọn danh mục:',
    selectTaste: 'Bạn muốn vị gì?',
    resetDone: 'Cuộc trò chuyện đã được đặt lại!',
    categories: ['🍲 Canh·Lẩu','🍜 Mì·Bún xào','🥩 Nướng·Xào','🥗 Cuốn·Salad','🍚 Cơm·Cháo','🧋 Ăn vặt·Đồ uống'],
    tastes: ['🌶️ Cay','🥜 Béo','💧 Thanh','🍯 Ngọt','🍋 Chua','🧂 Mặn','🍘 Giòn','✨ Umami','🔥 Cay nồng'],
    quickActions: ['🍜 Công thức Phở','🥩 Công thức Bulgogi','🥗 Món chay','🎲 Gợi ý ngẫu nhiên'],
    guidedUserMsg: (cat, taste) => `📋 Gợi ý: ${cat} + vị ${taste}`,
    randomUserMsg: '🎲 Gợi ý công thức ngẫu nhiên!',
  },
  en: {
    hello: 'Hello! 🐉',
    help: 'How can I help you?',
    placeholder: 'Type a message...',
    send: '➤',
    loading: 'Yongdami is thinking... 🍳',
    error: 'An error occurred. Please try again.',
    selectCategory: 'Select a category:',
    selectTaste: 'What flavor do you prefer?',
    resetDone: 'Conversation has been reset!',
    categories: ['🍲 Soup·Stew','🍜 Noodles·Stir-fry','🥩 Grill·Sauté','🥗 Wrap·Salad','🍚 Rice·Porridge','🧋 Snack·Drink'],
    tastes: ['🌶️ Spicy','🥜 Nutty','💧 Mild','🍯 Sweet','🍋 Sour','🧂 Salty','🍘 Crispy','✨ Umami','🔥 Fiery'],
    quickActions: ['🍜 Pho Recipe','🥩 Bulgogi Recipe','🥗 Vegan Dish','🎲 Random Pick'],
    guidedUserMsg: (cat, taste) => `📋 Guided: ${cat} + ${taste} flavor`,
    randomUserMsg: '🎲 Suggest a random recipe!',
  }
};

/* ── 카테고리 data 값 (언어별로 동일하게 API에 전달) ── */
const CW_CAT_KEYS  = ['국물탕','면볶음면','구이볶음','쌈샐러드','밥죽','간식음료'];
const CW_TASTE_KEYS= ['매운','고소','담백','달콤','새콤','짭짤','바삭','감칠맛','얼큰'];

/* ── 상태 변수 ── */
let cwLang    = 'ko';
let cwMode    = 'chat';
let cwCat     = null;
let cwTaste   = null;
let cwHistory = [];          // 대화 히스토리
let cwMsgIdx  = 0;           // 메시지 고유 ID 카운터
let cwOpen    = false;       // 위젯 열림 여부

/* ── 위젯 열기 / 닫기 ── */
function toggleChatWidget() {
  cwOpen = !cwOpen;
  const widget   = document.getElementById('chatWidget');
  const fabImg   = document.getElementById('fabImg');
  const fabClose = document.getElementById('fabClose');

  if (cwOpen) {
    widget.style.display = 'flex';
    // 처음 열릴 때 환영 화면 초기화
    _cwRenderWelcome();
    setTimeout(() => widget.classList.add('cw-visible'), 10);
  } else {
    widget.classList.remove('cw-visible');
    setTimeout(() => { widget.style.display = 'none'; }, 250);
  }

  if (fabImg)   fabImg.style.display   = cwOpen ? 'none'  : 'block';
  if (fabClose) fabClose.style.display = cwOpen ? 'inline': 'none';
}

/* ── 언어 전환 ── */
function cwSetLang(lang) {
  cwLang = lang;
  const L = CW_LANG[lang];
  document.querySelectorAll('.cw-lang-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.lang === lang)
  );
  // placeholder
  const input = document.getElementById('cwInput');
  if (input) input.placeholder = L.placeholder;
  // 환영 텍스트 갱신
  const helloEl = document.getElementById('cwHello');
  const helpEl  = document.getElementById('cwHelp');
  if (helloEl) helloEl.textContent = L.hello;
  if (helpEl)  helpEl.textContent  = L.help;
  // 가이드 라벨 갱신
  const catLabel   = document.getElementById('cwCatLabel');
  const tasteLabel = document.getElementById('cwTasteLabel');
  if (catLabel)   catLabel.textContent   = L.selectCategory;
  if (tasteLabel) tasteLabel.textContent = L.selectTaste;
  // 퀵 버튼 재렌더링
  _cwRenderQuickGrid();
  // 가이드 버튼 재렌더링 (열려있을 경우)
  if (cwMode === 'guided') _cwRenderGuidedButtons();
}

/* ── 모드 전환 ── */
function cwSetMode(mode) {
  cwMode = mode;
  document.querySelectorAll('.cw-mode-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.mode === mode)
  );

  const guided  = document.getElementById('cwGuided');
  const welcome = document.getElementById('cwWelcome');
  const msgs    = document.getElementById('cwMessages');

  // 가이드 패널
  if (guided) guided.style.display = mode === 'guided' ? 'block' : 'none';

  if (mode === 'random') {
    // 랜덤 모드: 바로 전송
    if (welcome) welcome.style.display = 'none';
    if (msgs)    msgs.style.display    = 'block';
    _cwSendRandom();
  } else if (mode === 'guided') {
    cwCat   = null;
    cwTaste = null;
    document.getElementById('cwTasteWrap').style.display = 'none';
    _cwRenderGuidedButtons();
  }
}

/* ── 가이드 카테고리·맛 버튼 렌더링 ── */
function _cwRenderGuidedButtons() {
  const L = CW_LANG[cwLang];
  const catWrap = document.getElementById('cwCatButtons');
  if (catWrap) {
    catWrap.innerHTML = '';
    L.categories.forEach((label, i) => {
      const btn = document.createElement('button');
      btn.className = 'cw-cat-btn';
      btn.textContent = label;
      btn.dataset.cat = CW_CAT_KEYS[i];
      btn.onclick = () => _cwSelectCat(btn);
      catWrap.appendChild(btn);
    });
  }
  const tasteWrap = document.getElementById('cwTasteButtons');
  if (tasteWrap) {
    tasteWrap.innerHTML = '';
    L.tastes.forEach((label, i) => {
      const btn = document.createElement('button');
      btn.className = 'cw-taste-btn';
      btn.textContent = label;
      btn.dataset.taste = CW_TASTE_KEYS[i];
      btn.onclick = () => _cwSelectTaste(btn);
      tasteWrap.appendChild(btn);
    });
  }
}

function _cwSelectCat(btn) {
  document.querySelectorAll('.cw-cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cwCat = btn.dataset.cat;
  document.getElementById('cwTasteWrap').style.display = 'block';
}

function _cwSelectTaste(btn) {
  document.querySelectorAll('.cw-taste-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cwTaste = btn.dataset.taste;
  _cwSendGuided();
}

/* ── 퀵 액션 그리드 렌더링 ── */
function _cwRenderQuickGrid() {
  const L    = CW_LANG[cwLang];
  const grid = document.getElementById('cwQuickGrid');
  if (!grid) return;
  grid.innerHTML = '';
  L.quickActions.forEach(label => {
    const btn = document.createElement('button');
    btn.className   = 'cw-quick-btn';
    btn.textContent = label;
    btn.onclick     = () => {
      const welcome = document.getElementById('cwWelcome');
      const msgs    = document.getElementById('cwMessages');
      if (welcome) welcome.style.display = 'none';
      if (msgs)    msgs.style.display    = 'block';
      if (label.includes('랜덤') || label.includes('ngẫu nhiên') || label.includes('Random')) {
        _cwSendRandom();
      } else {
        _cwAppendMsg('user', label);
        _cwCallAPI({ message: label, mode: 'chat' });
      }
    };
    grid.appendChild(btn);
  });
}

/* ── 환영 화면 초기화 ── */
function _cwRenderWelcome() {
  const L = CW_LANG[cwLang];
  const helloEl = document.getElementById('cwHello');
  const helpEl  = document.getElementById('cwHelp');
  if (helloEl) helloEl.textContent = L.hello;
  if (helpEl)  helpEl.textContent  = L.help;

  const welcome = document.getElementById('cwWelcome');
  const msgs    = document.getElementById('cwMessages');
  // 히스토리가 있으면 메시지 창 유지, 없으면 환영 화면
  if (cwHistory.length === 0) {
    if (welcome) welcome.style.display = 'block';
    if (msgs)    msgs.style.display    = 'none';
  }
  const input = document.getElementById('cwInput');
  if (input) input.placeholder = L.placeholder;
  _cwRenderQuickGrid();
}

/* ── 메시지 추가 ── */
function _cwAppendMsg(role, html, id) {
  const msgs = document.getElementById('cwMessages');
  if (!msgs) return null;

  // 처음 메시지 추가 시 환영 화면 숨기기
  const welcome = document.getElementById('cwWelcome');
  if (welcome) welcome.style.display = 'none';
  msgs.style.display = 'block';

  const msgId  = id || ('cwm-' + (cwMsgIdx++));
  const div    = document.createElement('div');
  div.className = role === 'user' ? 'cw-msg cw-msg-user' : 'cw-msg cw-msg-bot';
  div.id        = msgId;
  div.innerHTML = html;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return msgId;
}

/* ── API 응답 처리 ── */
function _cwHandleResponse(data, loadingId) {
  const msgEl = document.getElementById(loadingId);
  if (!msgEl) return;

  let html = '';

  // 응답 텍스트 (reply 또는 response 또는 message 필드 모두 대응)
  const text = data.reply || data.response || data.message || data.text || '';
  if (text) {
    html += `<div class="cw-reply-text">${text.replace(/\n/g, '<br>')}</div>`;
  }

  // 레시피 이미지
  if (data.image_url) {
    html += `<img src="${data.image_url}" class="cw-recipe-img" alt="recipe">`;
  }

  msgEl.innerHTML = html || CW_LANG[cwLang].error;

  // 히스토리 저장
  if (text) cwHistory.push({ role: 'assistant', content: text });
}

/* ── API 호출 공통 함수 ── */
async function _cwCallAPI(payload) {
  const L = CW_LANG[cwLang];
  const loadingId = _cwAppendMsg('bot', `<span class="cw-loading">${L.loading}</span>`);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        language: cwLang,
        conversation_history: cwHistory.slice(-6),
        ...payload
      })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    _cwHandleResponse(data, loadingId);
  } catch (e) {
    const el = document.getElementById(loadingId);
    if (el) el.textContent = L.error;
  }
}

/* ── 메시지 전송 (chat 모드) ── */
function cwSend() {
  const input   = document.getElementById('cwInput');
  const message = input ? input.value.trim() : '';
  if (!message) return;
  input.value = '';

  _cwAppendMsg('user', message);
  cwHistory.push({ role: 'user', content: message });
  _cwCallAPI({ message, mode: 'chat' });
}

/* ── 가이드 추천 전송 ── */
async function _cwSendGuided() {
  const L = CW_LANG[cwLang];
  _cwAppendMsg('user', L.guidedUserMsg(cwCat, cwTaste));
  _cwCallAPI({
    message: '',
    mode: 'guided',
    category: cwCat,
    taste: cwTaste,
    conversation_history: []
  });
}

/* ── 랜덤 레시피 전송 ── */
async function _cwSendRandom() {
  const L = CW_LANG[cwLang];
  _cwAppendMsg('user', L.randomUserMsg);
  _cwCallAPI({ message: '', mode: 'random', conversation_history: [] });
}

/* ── 대화 초기화 ── */
function cwReset() {
  cwHistory = [];
  cwCat     = null;
  cwTaste   = null;
  cwMode    = 'chat';

  const msgs = document.getElementById('cwMessages');
  if (msgs) { msgs.innerHTML = ''; msgs.style.display = 'none'; }

  const welcome = document.getElementById('cwWelcome');
  if (welcome) welcome.style.display = 'block';

  // 모드 버튼 초기화
  document.querySelectorAll('.cw-mode-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.mode === 'chat')
  );
  // 가이드 패널 닫기
  const guided = document.getElementById('cwGuided');
  if (guided) guided.style.display = 'none';
  const tasteWrap = document.getElementById('cwTasteWrap');
  if (tasteWrap) tasteWrap.style.display = 'none';

  _cwRenderWelcome();
}

/* ── 가이드 버튼 초기 렌더링 (DOM 로드 후) ── */
document.addEventListener('DOMContentLoaded', () => {
  _cwRenderGuidedButtons();
  _cwRenderQuickGrid();
});
