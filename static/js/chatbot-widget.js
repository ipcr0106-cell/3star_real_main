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
  // cwMessages(플로팅 위젯) 또는 chatWindow(/chatbot 페이지) 탐색
  let msgs = document.getElementById('cwMessages');
  // cwMessages가 숨겨진 chatWidget 안에 있으면 chatWindow로 폴백
  if (msgs) {
    const parent = msgs.closest('.chat-widget');
    if (parent && parent.style.display === 'none') {
      msgs = document.getElementById('chatWindow') || msgs;
    }
  }
  if (!msgs) msgs = document.getElementById('chatWindow');
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

/* ── 다국어 레이블 (레시피 카드용) ── */
const CW_RECIPE_LABELS = {
  ko: { ingredients: '📝 재료', steps: '👨‍🍳 조리법', tips: '💡 팁', cart: '🛒 장바구니', favorites: '⭐ 즐겨찾기', servings: '인분' },
  vi: { ingredients: '📝 Nguyên liệu', steps: '👨‍🍳 Cách làm', tips: '💡 Mẹo', cart: '🛒 Giỏ hàng', favorites: '⭐ Yêu thích', servings: ' phần' },
  en: { ingredients: '📝 Ingredients', steps: '👨‍🍳 Steps', tips: '💡 Tips', cart: '🛒 Cart', favorites: '⭐ Favorites', servings: ' servings' },
};

/* ── 장바구니 추가 (cart.js 연동) ── */
function _cwAddToCart(productId, qty) {
  qty = qty || 1;
  if (typeof window.addToCartFromChatbot === 'function') {
    window.addToCartFromChatbot(productId, qty);
  } else {
    var name = (typeof window.PRODUCTS !== 'undefined' && window.PRODUCTS[productId])
      ? window.PRODUCTS[productId].name : productId;
    alert('🛒 ' + name + ' ' + qty + (cwLang === 'vi' ? ' đã thêm!' : cwLang === 'en' ? ' added!' : '개 장바구니에 추가!'));
  }
}

/* ── 즐겨찾기 추가 ── */
function _cwAddToFavorites(recipeId, recipeName) {
  var favs = JSON.parse(localStorage.getItem('chatbot_favorites') || '[]');
  if (!favs.find(function(f) { return f.id === recipeId; })) {
    favs.push({ id: recipeId, name: recipeName, savedAt: new Date().toISOString() });
    localStorage.setItem('chatbot_favorites', JSON.stringify(favs));
  }
}

/* ── API 응답 처리 ── */
function _cwHandleResponse(data, loadingId) {
  const msgEl = document.getElementById(loadingId);
  if (!msgEl) return;

  const RL = CW_RECIPE_LABELS[cwLang] || CW_RECIPE_LABELS.ko;
  let html = '';

  if (data.type === 'recipe') {
    // 레시피 카드 렌더링
    html += '<div class="cw-recipe-card">';

    if (data.image_url) {
      html += '<img src="' + data.image_url + '" alt="' + (data.title || '') + '" class="cw-recipe-img" loading="lazy">';
    }

    html += '<h3>' + (data.title || '') + '</h3>';

    if (data.product) {
      html += '<p class="cw-product-tag">🏷️ ' + data.product + '</p>';
    }

    // 인분 조절
    var baseServ = data.base_servings || 2;
    html += '<div class="cw-serving-control" data-base="' + baseServ + '">';
    html += '<button class="cw-serv-btn" onclick="_cwAdjustServing(this, -1)">−</button>';
    html += '<span class="cw-serv-display">' + baseServ + '</span>';
    html += '<span class="cw-serv-label">' + RL.servings + '</span>';
    html += '<button class="cw-serv-btn" onclick="_cwAdjustServing(this, 1)">+</button>';
    html += '</div>';

    // 재료
    if (data.ingredients && data.ingredients.length) {
      html += '<div class="cw-collapse-section open">';
      html += '<button class="cw-collapse-toggle" onclick="this.parentElement.classList.toggle(\'open\')">';
      html += '<span class="cw-collapse-title">' + RL.ingredients + ' (' + data.ingredients.length + ')</span>';
      html += '<span class="cw-collapse-arrow">▸</span>';
      html += '</button>';
      html += '<div class="cw-collapse-content"><ul>';
      data.ingredients.forEach(function(i) { html += '<li class="cw-ingredient-item">' + i + '</li>'; });
      html += '</ul></div></div>';
    }

    // 조리법
    if (data.steps && data.steps.length) {
      html += '<div class="cw-collapse-section open">';
      html += '<button class="cw-collapse-toggle" onclick="this.parentElement.classList.toggle(\'open\')">';
      html += '<span class="cw-collapse-title">' + RL.steps + ' (' + data.steps.length + ')</span>';
      html += '<span class="cw-collapse-arrow">▸</span>';
      html += '</button>';
      html += '<div class="cw-collapse-content"><ol>';
      data.steps.forEach(function(s) {
        var cleaned = s.replace(/^\d+\.\s*/, '');
        html += '<li>' + cleaned + '</li>';
      });
      html += '</ol></div></div>';
    }

    // 팁
    if (data.tips) {
      var tipsText = Array.isArray(data.tips) ? data.tips.join(' / ') : data.tips;
      html += '<div class="cw-tips">' + RL.tips + ': ' + tipsText + '</div>';
    }

    // 액션 버튼 (장바구니 + 즐겨찾기)
    html += '<div class="cw-recipe-actions">';
    if (data.product_id) {
      html += '<button onclick="_cwAddToCart(\'' + data.product_id + '\', 1)" class="cw-action-btn">' + RL.cart + '</button>';
    }
    var recipeId = data.recipe_id || data.product_id || '';
    var recipeTitle = (data.title || '').replace(/'/g, "\\'");
    if (recipeId) {
      html += '<button onclick="_cwAddToFavorites(\'' + recipeId + '\', \'' + recipeTitle + '\')" class="cw-action-btn">' + RL.favorites + '</button>';
    }
    html += '</div>';

    html += '</div>';

    // 히스토리 저장
    cwHistory.push({ role: 'assistant', content: JSON.stringify(data._raw || data) });
  } else {
    // 텍스트 응답
    const text = data.reply || data.response || data.message || data.text || '';
    if (text) {
      html += '<div class="cw-reply-text">' + text.replace(/\n/g, '<br>') + '</div>';
    }
    if (data.image_url) {
      html += '<img src="' + data.image_url + '" class="cw-recipe-img" alt="recipe">';
    }
    if (text) cwHistory.push({ role: 'assistant', content: text });
  }

  msgEl.innerHTML = html || CW_LANG[cwLang].error;
}

/* ── 인분 조절 (프론트엔드 계산) ── */
function _cwAdjustServing(btn, delta) {
  var control = btn.closest('.cw-serving-control');
  var display = control.querySelector('.cw-serv-display');
  var base = parseInt(control.dataset.base) || 2;
  var current = parseInt(display.textContent) || base;
  var next = current + delta;
  if (next < 1 || next > 20) return;
  display.textContent = next;

  var card = control.closest('.cw-recipe-card');
  if (!card) return;
  var items = card.querySelectorAll('.cw-ingredient-item');
  var multiplier = next / base;

  items.forEach(function(item) {
    var original = item.dataset.original;
    if (!original) {
      item.dataset.original = item.textContent;
      original = item.textContent;
    }
    item.textContent = original.replace(/(\d+)\/(\d+)|(\d+\.?\d*)/g, function(match, fNum, fDen, num) {
      if (fNum && fDen) {
        var frac = (parseFloat(fNum) / parseFloat(fDen)) * multiplier;
        return frac % 1 === 0 ? frac.toString() : frac.toFixed(1);
      }
      if (num) {
        var n = parseFloat(num);
        var result = n * multiplier;
        return result % 1 === 0 ? result.toString() : result.toFixed(1);
      }
      return match;
    });
  });
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
