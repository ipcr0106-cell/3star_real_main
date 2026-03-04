/**
 * chatbot-float.js — 플로팅 챗봇 위젯 로직
 * base_b2c.html의 위젯 HTML과 함께 동작
 * /chatbot 전용 chatbot-widget.js와 충돌 방지: 모든 변수/함수에 cw 접두사 사용
 */

// ─── 다국어 데이터 ───
const CW_LANG = {
  ko: {
    hello: "안녕하세요!",
    helpText: "무엇을 도와드릴까요?",
    placeholder: "메시지를 입력하세요...",
    modes: ["💬 대화", "📋 가이드", "🎲 랜덤"],
    quickActions: ["🍲 레시피 추천", "📦 제품 정보", "🥕 재료로 검색", "🍳 요리 팁"],
    quickMsgs: ["매콤한 쌀국수 추천해줘", "코인육수 제품 알려줘", "소고기 양파 당근으로 뭘 만들까?", "쌀국수 삶는 팁 알려줘"],
    categories: ["🍲 국물·탕", "🍜 면·볶음면", "🥩 구이·볶음", "🥗 쌈·샐러드", "🍚 밥·죽", "🧋 간식·음료"],
    catValues: ["국물탕", "면볶음면", "구이볶음", "쌈샐러드", "밥죽", "간식음료"],
    tastes: ["🌶️ 매운", "🥜 고소", "💧 담백", "🍯 달콤", "🍋 새콤", "🧂 짭짤", "🍘 바삭", "✨ 감칠맛", "🔥 얼큰"],
    tasteValues: ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"],
    selectCat: "카테고리를 선택하세요",
    selectTaste: "어떤 맛을 원하세요?",
    ingredients: "재료",
    steps: "조리법",
    tips: "💡 팁",
    cart: "🛒 장바구니",
    favorites: "⭐ 즐겨찾기",
    loading: "🔄 응답 생성 중...",
    error: "⚠️ 오류가 발생했어요. 다시 시도해 주세요."
  },
  vi: {
    hello: "Xin chào!",
    helpText: "Tôi có thể giúp gì cho bạn?",
    placeholder: "Nhập tin nhắn...",
    modes: ["💬 Trò chuyện", "📋 Gợi ý", "🎲 Ngẫu nhiên"],
    quickActions: ["🍲 Gợi ý món", "📦 Sản phẩm", "🥕 Theo NL", "🍳 Mẹo nấu"],
    quickMsgs: ["Gợi ý phở cay", "Thông tin Coin Broth", "Nấu gì với thịt bò, hành, cà rốt?", "Mẹo luộc phở"],
    categories: ["🍲 Canh·Lẩu", "🍜 Mì·Bún", "🥩 Nướng·Xào", "🥗 Cuốn·Salad", "🍚 Cơm·Cháo", "🧋 Snack·Đồ uống"],
    catValues: ["국물탕", "면볶음면", "구이볶음", "쌈샐러드", "밥죽", "간식음료"],
    tastes: ["🌶️ Cay", "🥜 Béo", "💧 Thanh", "🍯 Ngọt", "🍋 Chua", "🧂 Mặn", "🍘 Giòn", "✨ Umami", "🔥 Nóng"],
    tasteValues: ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"],
    selectCat: "Chọn loại món",
    selectTaste: "Bạn muốn vị gì?",
    ingredients: "Nguyên liệu",
    steps: "Cách làm",
    tips: "💡 Mẹo",
    cart: "🛒 Giỏ hàng",
    favorites: "⭐ Yêu thích",
    loading: "🔄 Đang tạo phản hồi...",
    error: "⚠️ Đã xảy ra lỗi. Vui lòng thử lại."
  },
  en: {
    hello: "Hello!",
    helpText: "How can I help you today?",
    placeholder: "Type a message...",
    modes: ["💬 Chat", "📋 Guide", "🎲 Random"],
    quickActions: ["🍲 Recipe", "📦 Products", "🥕 By Ingredient", "🍳 Tips"],
    quickMsgs: ["Suggest a spicy noodle recipe", "Tell me about Coin Broth", "What can I make with beef, onion, carrot?", "Tips for cooking rice noodles"],
    categories: ["🍲 Soup", "🍜 Noodle", "🥩 Grill·Stir-fry", "🥗 Wrap·Salad", "🍚 Rice·Porridge", "🧋 Snack·Drink"],
    catValues: ["국물탕", "면볶음면", "구이볶음", "쌈샐러드", "밥죽", "간식음료"],
    tastes: ["🌶️ Spicy", "🥜 Nutty", "💧 Light", "🍯 Sweet", "🍋 Sour", "🧂 Salty", "🍘 Crispy", "✨ Umami", "🔥 Hot"],
    tasteValues: ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"],
    selectCat: "Choose a category",
    selectTaste: "What flavor?",
    ingredients: "Ingredients",
    steps: "How to Cook",
    tips: "💡 Tips",
    cart: "🛒 Cart",
    favorites: "⭐ Favorites",
    loading: "🔄 Generating response...",
    error: "⚠️ An error occurred. Please try again."
  }
};

// ─── 퀵 답장 데이터 ───
const CW_QUICK_REPLIES = {
  ko: ["🔍 비슷한 레시피", "🛒 이 제품 상세보기", "📱 레시피 공유"],
  vi: ["🔍 Món tương tự", "🛒 Xem sản phẩm", "📱 Chia sẻ"],
  en: ["🔍 Similar recipes", "🛒 View product", "📱 Share recipe"]
};

// ─── 간이 마크다운 → HTML 변환 ───
function cwMarkdown(text) {
  if (!text) return '';
  // XSS 방어: HTML 태그 이스케이프 (볼드 변환 전)
  var html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\r\n/g, '\n')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 줄 단위 처리
  var lines = html.split('\n');
  var result = [];
  var inList = false;

  lines.forEach(function(line) {
    var trimmed = line.trim();
    var listMatch = trimmed.match(/^[\-·\*]\s+(.+)/);
    var numMatch = trimmed.match(/^\d+\.\s+(.+)/);

    if (listMatch || numMatch) {
      if (!inList) { result.push('<ul>'); inList = true; }
      result.push('<li>' + (listMatch ? listMatch[1] : numMatch[1]) + '</li>');
    } else {
      if (inList) { result.push('</ul>'); inList = false; }
      if (trimmed === '') {
        result.push('<br>');
      } else {
        result.push('<p>' + trimmed + '</p>');
      }
    }
  });
  if (inList) result.push('</ul>');

  return result.join('')
    .replace(/<br>(<br>)+/g, '<br>')
    .replace(/<p><\/p>/g, '');
}

// ─── 상태 변수 ───
let cwLang = 'ko';
let cwMode = 'chat';
let cwSelectedCat = null;
let cwSelectedTaste = null;
let cwConversationHistory = [];
let cwMsgCounter = 0;
let cwIsOpen = false;

// ─── 아바타 GIF 상태 전환 ───
var CW_AVATAR_STATE = 'thinking';
var CW_AVATAR_SRCS = {
  thinking: '/static/images/brand/yongdami_thinking.gif',
  cooking:  '/static/images/brand/yongdami_cooking.gif',
  eating:   '/static/images/brand/yongdami_eating.gif'
};
function cwSetAvatar(state) {
  CW_AVATAR_STATE = state;
  var gif = document.getElementById('cwAvatar');
  if (gif && CW_AVATAR_SRCS[state]) {
    gif.src = CW_AVATAR_SRCS[state] + '?v=' + Date.now();
  }
}

// ─── 로딩 GIF preload (Blob 캐시) ───
var cwCookingGifBlob = null;
fetch('/static/images/brand/yongdami_cooking.gif')
  .then(function(r) { return r.blob(); })
  .then(function(b) { cwCookingGifBlob = b; })
  .catch(function() {});

function cwLoadingGifSrc() {
  if (cwCookingGifBlob) return URL.createObjectURL(cwCookingGifBlob);
  return '/static/images/brand/yongdami_cooking.gif';
}

// ─── 초기화 ───
document.addEventListener('DOMContentLoaded', function() {
  cwSetAvatar('thinking');
  cwBuildQuickActions();
  cwBuildGuided();
});

// ─── 위젯 토글 ───
function toggleChatWidget() {
  var widget = document.getElementById('chatWidget');
  var fabImg = document.getElementById('fabImg');
  var fabClose = document.getElementById('fabClose');
  cwIsOpen = !cwIsOpen;

  if (cwIsOpen) {
    widget.style.display = 'flex';
    setTimeout(function() { widget.classList.add('cw-visible'); }, 10);
    fabImg.style.display = 'none';
    fabClose.style.display = 'block';
  } else {
    widget.classList.remove('cw-visible');
    setTimeout(function() { widget.style.display = 'none'; }, 250);
    fabImg.style.display = 'block';
    fabClose.style.display = 'none';
  }
}

// ─── 언어 변경 ───
function cwSetLang(lang) {
  cwLang = lang;
  var L = CW_LANG[lang];

  // 언어 버튼 활성화
  document.querySelectorAll('.cw-lang-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.lang === lang);
  });

  // UI 텍스트 업데이트
  document.getElementById('cwHello').textContent = L.hello;
  document.getElementById('cwHelp').textContent = L.helpText;
  document.getElementById('cwInput').placeholder = L.placeholder;
  document.getElementById('cwCatLabel').textContent = L.selectCat;
  document.getElementById('cwTasteLabel').textContent = L.selectTaste;

  // 모드 버튼 텍스트
  var modeBtns = document.querySelectorAll('.cw-mode-btn');
  L.modes.forEach(function(txt, i) {
    if (modeBtns[i]) modeBtns[i].textContent = txt;
  });

  // 퀵 액션 재생성
  cwBuildQuickActions();
  // 가이드 버튼 재생성
  cwBuildGuided();
}

// ─── 모드 전환 ───
function cwSetMode(mode) {
  cwMode = mode;
  document.querySelectorAll('.cw-mode-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.mode === mode);
  });

  var guided = document.getElementById('cwGuided');
  var welcome = document.getElementById('cwWelcome');
  var messages = document.getElementById('cwMessages');

  if (mode === 'guided') {
    guided.style.display = 'block';
    welcome.style.display = 'none';
    messages.style.display = 'none';
    cwSelectedCat = null;
    cwSelectedTaste = null;
    document.getElementById('cwTasteWrap').style.display = 'none';
    cwBuildGuided();
  } else if (mode === 'random') {
    guided.style.display = 'none';
    welcome.style.display = 'none';
    messages.style.display = 'flex';
    cwSendRandom();
  } else {
    guided.style.display = 'none';
    // 메시지가 있으면 메시지 표시, 없으면 웰컴
    if (document.getElementById('cwMessages').children.length > 0) {
      welcome.style.display = 'none';
      messages.style.display = 'flex';
    } else {
      welcome.style.display = 'flex';
      messages.style.display = 'none';
    }
  }
}

// ─── 퀵 액션 버튼 생성 ───
function cwBuildQuickActions() {
  var grid = document.getElementById('cwQuickGrid');
  if (!grid) return;
  var L = CW_LANG[cwLang];
  grid.innerHTML = '';
  L.quickActions.forEach(function(label, i) {
    var btn = document.createElement('button');
    btn.className = 'cw-quick-btn';
    btn.textContent = label;
    btn.onclick = function() { cwSend(L.quickMsgs[i]); };
    grid.appendChild(btn);
  });
}

// ─── 가이드 모드 버튼 생성 ───
function cwBuildGuided() {
  var L = CW_LANG[cwLang];
  var catBox = document.getElementById('cwCatButtons');
  var tasteBox = document.getElementById('cwTasteButtons');
  if (!catBox || !tasteBox) return;

  catBox.innerHTML = '';
  L.categories.forEach(function(label, i) {
    var btn = document.createElement('button');
    btn.className = 'cw-cat-btn';
    btn.textContent = label;
    btn.onclick = function() {
      catBox.querySelectorAll('.cw-cat-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      cwSelectedCat = L.catValues[i];
      document.getElementById('cwTasteWrap').style.display = 'block';
      cwSetAvatar('cooking');
    };
    catBox.appendChild(btn);
  });

  tasteBox.innerHTML = '';
  L.tastes.forEach(function(label, i) {
    var btn = document.createElement('button');
    btn.className = 'cw-taste-btn';
    btn.textContent = label;
    btn.onclick = function() {
      tasteBox.querySelectorAll('.cw-taste-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      cwSelectedTaste = L.tasteValues[i];
      cwSendGuided();
    };
    tasteBox.appendChild(btn);
  });
}

// ─── 메시지 전송 ───
function cwSend(text) {
  var input = document.getElementById('cwInput');
  var message = text || input.value.trim();
  if (!message) return;
  if (!text) input.value = '';
  cwSetAvatar('cooking');

  // 웰컴 숨기고 메시지 영역 표시
  document.getElementById('cwWelcome').style.display = 'none';
  document.getElementById('cwMessages').style.display = 'flex';

  cwAppendMessage('user', message);
  cwConversationHistory.push({ role: 'user', content: message });

  var loadingHtml = '<div class="cw-loading-wrap">' +
    '<img src="" class="cw-loading-gif" alt="">' +
    '<span class="cw-loading-text">' + CW_LANG[cwLang].loading + '</span></div>';
  var loadingId = cwAppendMessage('bot', loadingHtml);
  var _gif = document.querySelector('#' + loadingId + ' .cw-loading-gif');
  if (_gif) {
    _gif.onload = function() { cwScrollCenter(loadingId); };
    _gif.src = cwLoadingGifSrc();
  }

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      language: cwLang,
      mode: cwMode,
      category: cwSelectedCat,
      taste: cwSelectedTaste,
      conversation_history: cwConversationHistory.slice(-6)
    })
  })
  .then(function(res) {
    if (!res.ok) throw new Error('Server error: ' + res.status);
    return res.json();
  })
  .then(function(data) {
    cwRemoveMessage(loadingId);
    renderCwMessage(data);
    var rawContent = data._raw || data;
    cwConversationHistory.push({ role: 'assistant', content: JSON.stringify(rawContent) });
  })
  .catch(function(err) {
    console.error('cwSend error:', err);
    cwRemoveMessage(loadingId);
    cwAppendMessage('bot', CW_LANG[cwLang].error);
  });
}

// ─── 가이드 전송 ───
function cwSendGuided() {
  // null 방어: 카테고리와 맛 모두 선택되지 않으면 전송하지 않음
  if (!cwSelectedCat || !cwSelectedTaste) {
    cwShowToast(cwLang === 'vi' ? 'Vui lòng chọn cả danh mục và vị!' : cwLang === 'en' ? 'Please select both category and taste!' : '카테고리와 맛을 모두 선택해주세요!');
    return;
  }
  cwSetAvatar('cooking');
  document.getElementById('cwGuided').style.display = 'none';
  document.getElementById('cwWelcome').style.display = 'none';
  document.getElementById('cwMessages').style.display = 'flex';

  // 표시용 label은 현재 언어의 카테고리/맛 이름 사용
  var L = CW_LANG[cwLang];
  var catIdx = L.catValues.indexOf(cwSelectedCat);
  var tasteIdx = L.tasteValues.indexOf(cwSelectedTaste);
  var displayCat = catIdx >= 0 ? L.categories[catIdx] : (cwSelectedCat || '');
  var displayTaste = tasteIdx >= 0 ? L.tastes[tasteIdx] : (cwSelectedTaste || '');
  var guideLabel = {ko: '📋 가이드', vi: '📋 Hướng dẫn', en: '📋 Guide'}[cwLang] || '📋 가이드';
  cwAppendMessage('user', guideLabel + ': ' + displayCat + ' + ' + displayTaste);

  var loadingHtml = '<div class="cw-loading-wrap">' +
    '<img src="" class="cw-loading-gif" alt="">' +
    '<span class="cw-loading-text">' + CW_LANG[cwLang].loading + '</span></div>';
  var loadingId = cwAppendMessage('bot', loadingHtml);
  var _gif = document.querySelector('#' + loadingId + ' .cw-loading-gif');
  if (_gif) {
    _gif.onload = function() { cwScrollCenter(loadingId); };
    _gif.src = cwLoadingGifSrc();
  }

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: '',
      language: cwLang,
      mode: 'guided',
      category: cwSelectedCat,
      taste: cwSelectedTaste,
      conversation_history: cwConversationHistory.slice(-6)
    })
  })
  .then(function(res) {
    if (!res.ok) throw new Error('Server error: ' + res.status);
    return res.json();
  })
  .then(function(data) {
    cwRemoveMessage(loadingId);
    renderCwMessage(data);
    cwConversationHistory.push({ role: 'user', content: guideLabel + ': ' + displayCat + ' + ' + displayTaste });
    var rawContent = data._raw || data;
    cwConversationHistory.push({ role: 'assistant', content: JSON.stringify(rawContent) });
    // 가이드 완료 후 선택값 초기화
    cwSelectedCat = null;
    cwSelectedTaste = null;
    cwSetMode('chat');
  })
  .catch(function(err) {
    console.error('cwSendGuided error:', err);
    cwRemoveMessage(loadingId);
    cwAppendMessage('bot', CW_LANG[cwLang].error);
  });
}

// ─── 랜덤 전송 ───
function cwSendRandom() {
  cwSetAvatar('cooking');
  document.getElementById('cwWelcome').style.display = 'none';
  document.getElementById('cwMessages').style.display = 'flex';

  var randomLabel = {ko: '🎲 랜덤 레시피!', vi: '🎲 Món ngẫu nhiên!', en: '🎲 Random recipe!'}[cwLang] || '🎲 랜덤 레시피!';
  cwAppendMessage('user', randomLabel);
  var loadingHtml = '<div class="cw-loading-wrap">' +
    '<img src="" class="cw-loading-gif" alt="">' +
    '<span class="cw-loading-text">' + CW_LANG[cwLang].loading + '</span></div>';
  var loadingId = cwAppendMessage('bot', loadingHtml);
  var _gif = document.querySelector('#' + loadingId + ' .cw-loading-gif');
  if (_gif) {
    _gif.onload = function() { cwScrollCenter(loadingId); };
    _gif.src = cwLoadingGifSrc();
  }

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: '',
      language: cwLang,
      mode: 'random',
      conversation_history: cwConversationHistory.slice(-6)
    })
  })
  .then(function(res) {
    if (!res.ok) throw new Error('Server error: ' + res.status);
    return res.json();
  })
  .then(function(data) {
    cwRemoveMessage(loadingId);
    renderCwMessage(data);
    cwConversationHistory.push({ role: 'user', content: randomLabel });
    var rawContent = data._raw || data;
    cwConversationHistory.push({ role: 'assistant', content: JSON.stringify(rawContent) });
    cwSetMode('chat');
  })
  .catch(function(err) {
    console.error('cwSendRandom error:', err);
    cwRemoveMessage(loadingId);
    cwAppendMessage('bot', CW_LANG[cwLang].error);
  });
}

// ─── 장바구니 (자체 구현, chatbot-widget.js 의존 제거) ───
function cwAddToCart(productId, quantity) {
  quantity = quantity || 1;
  var pName = (typeof window.PRODUCTS !== 'undefined' && window.PRODUCTS[productId])
    ? window.PRODUCTS[productId].name : productId;
  fetch('/analytics/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event: 'cart_add', data: { product_id: productId, product_name: pName, quantity: quantity } })
  }).catch(function() {});
  if (typeof window.addToCartFromChatbot === 'function') {
    window.addToCartFromChatbot(productId, quantity);
  } else {
    // cart.js 미로드 시 직접 Object 형식으로 localStorage 저장
    var cartData = JSON.parse(localStorage.getItem('threestar_cart') || '{}');
    // Array로 저장된 경우 Object로 마이그레이션
    if (Array.isArray(cartData)) cartData = {};
    cartData[productId] = (cartData[productId] || 0) + quantity;
    localStorage.setItem('threestar_cart', JSON.stringify(cartData));
    // navbar 카운트 업데이트
    var totalQty = Object.values(cartData).reduce(function(s, q) { return s + q; }, 0);
    document.querySelectorAll('.btn-cart').forEach(function(btn) {
      btn.textContent = '🛒 Cart (' + totalQty + ')';
    });
    var name = (typeof window.PRODUCTS !== 'undefined' && window.PRODUCTS[productId])
      ? window.PRODUCTS[productId].name : productId;
    cwShowToast('🛒 ' + name + ' ' + quantity +
      (cwLang === 'vi' ? ' đã thêm!' : cwLang === 'en' ? ' added!' : '개 장바구니에 추가!'));
  }
}

// ─── 즐겨찾기 (자체 구현) ───
function cwAddToFavorites(recipeId, recipeName) {
  var favs = JSON.parse(localStorage.getItem('chatbot_favorites') || '[]');
  if (!favs.find(function(f) { return f.id === recipeId; })) {
    favs.push({ id: recipeId, name: recipeName, savedAt: new Date().toISOString() });
    localStorage.setItem('chatbot_favorites', JSON.stringify(favs));
    cwShowToast('⭐ "' + recipeName + '" ' +
      (cwLang === 'vi' ? 'đã thêm!' : cwLang === 'en' ? 'added!' : '즐겨찾기 추가!'));
  } else {
    cwShowToast(cwLang === 'vi' ? 'Đã có trong yêu thích!' : cwLang === 'en' ? 'Already in favorites!' : '이미 즐겨찾기에 있어요!');
  }
}

// ─── 인분 조절 (프론트엔드 계산) ───
function cwAdjustServing(btn, delta) {
  var control = btn.closest('.cw-serving-control');
  var display = control.querySelector('.cw-serv-display');
  var base = parseInt(control.dataset.base) || 2;
  var current = parseInt(display.textContent) || base;
  var next = current + delta;
  if (next < 1 || next > 20) return;
  display.textContent = next;

  // 재료 양 재계산
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
    // ★ 단일 패스로 분수와 일반 숫자를 동시 처리 (이중 곱셈 방지)
    item.textContent = original.replace(/(\d+)\/(\d+)|(\d+\.?\d*)/g, function(match, fNum, fDen, num) {
      if (fNum && fDen) {
        // 분수: 1/4 → (1÷4) × multiplier
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

// ─── 제품 상세보기 ───
function cwShowProduct(productId) {
  // HOME 페이지: 직접 openProduct 호출
  if (window.location.pathname === '/' && typeof window.openProduct === 'function' && typeof window.REVERSE_ID_MAP !== 'undefined') {
    var numId = window.REVERSE_ID_MAP[productId];
    if (numId) { window.openProduct(numId); return; }
  }
  // 다른 페이지: HOME으로 이동 (URL 파라미터)
  window.open('/?product=' + encodeURIComponent(productId), '_blank');
}

// ─── 대화 초기화 ───
function cwReset() {
  cwSetAvatar('thinking');
  var L = CW_LANG[cwLang];
  // 대화 히스토리 초기화
  cwConversationHistory = [];
  // 메시지 영역 비우기
  var messages = document.getElementById('cwMessages');
  if (messages) messages.innerHTML = '';
  // 웰컴 화면 표시
  document.getElementById('cwMessages').style.display = 'none';
  document.getElementById('cwWelcome').style.display = 'block';
  document.getElementById('cwGuided').style.display = 'none';
  // chat 모드로 전환
  cwSetMode('chat');
  // 가이드 선택 초기화
  cwSelectedCat = null;
  cwSelectedTaste = null;
  // 퀵액션 재생성
  cwBuildQuickActions();
  cwBuildGuided();
}

// ─── 레시피 공유 ───
function cwShareRecipe(recipeId, recipeTitle) {
  var L = CW_LANG[cwLang];
  var shareText = recipeTitle + ' - Da-Mi Food Recipe';
  var shareUrl = window.location.origin + '/?recipe=' + recipeId;

  // 레시피 카드 찾기 (가장 마지막 카드)
  var cards = document.querySelectorAll('.cw-recipe-card');
  var card = cards[cards.length - 1];

  if (!card || typeof html2canvas === 'undefined') {
    // html2canvas 없으면 기존 텍스트 공유로 fallback
    _cwShareText(shareText, shareUrl);
    return;
  }

  // 로딩 표시
  cwShowToast({ko: '이미지 생성 중...', vi: 'Đang tạo ảnh...', en: 'Creating image...'}[cwLang] || '...');

  // 복제본 생성 → 전부 펼침 → 캡처 → 삭제
  var clone = card.cloneNode(true);
  clone.style.position = 'absolute';
  clone.style.left = '-9999px';
  clone.style.top = '0';
  clone.style.width = card.offsetWidth + 'px';
  clone.style.background = '#fff';
  clone.style.padding = '16px';

  // 접힌 섹션 전부 펼치기
  clone.querySelectorAll('.cw-collapse-section').forEach(function(sec) {
    sec.classList.add('open');
  });
  // 인분 조절, 퀵리플라이, 액션 버튼 제거 (공유용 깔끔하게)
  clone.querySelectorAll('.cw-serving-control, .cw-quick-replies, .cw-recipe-actions').forEach(function(el) {
    el.remove();
  });

  // 하단에 브랜드 추가
  var brand = document.createElement('p');
  brand.style.cssText = 'text-align:center;color:#888;font-size:12px;margin-top:12px;border-top:1px solid #eee;padding-top:8px;';
  brand.textContent = '🛒 Da-Mi Food | damifood.vn';
  clone.appendChild(brand);

  document.body.appendChild(clone);

  html2canvas(clone, { useCORS: true, scale: 2, backgroundColor: '#ffffff' }).then(function(canvas) {
    document.body.removeChild(clone);

    canvas.toBlob(function(blob) {
      if (!blob) {
        _cwShareText(shareText, shareUrl);
        return;
      }

      // 텍스트 버전 생성
      var textVersion = _cwBuildShareText(card, recipeTitle);

      // 모바일: Web Share API (이미지 + 텍스트)
      var file = new File([blob], recipeId + '.png', { type: 'image/png' });
      var isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
      if (isMobile && navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({
          title: recipeTitle,
          text: textVersion,
          files: [file]
        }).catch(function() {});
        return;
      }

      // 데스크톱: 이미지 클립보드 + 텍스트 클립보드 + 다운로드
      var copied = false;
      if (navigator.clipboard && typeof ClipboardItem !== 'undefined') {
        try {
          navigator.clipboard.write([
            new ClipboardItem({
              'image/png': blob,
              'text/plain': new Blob([textVersion], { type: 'text/plain' })
            })
          ]).then(function() {
            cwShowToast({
              ko: '레시피 이미지+텍스트 복사 완료! Ctrl+V로 붙여넣기',
              vi: 'Đã sao chép! Dán bằng Ctrl+V',
              en: 'Copied! Paste with Ctrl+V'
            }[cwLang] || '복사됨!');
            copied = true;
          }).catch(function() {});
        } catch(e) {}
      }

      // 이미지 다운로드 (항상)
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = recipeId + '.png';
      a.click();
      URL.revokeObjectURL(a.href);

      if (!copied) {
        cwShowToast({
          ko: '레시피 이미지가 저장되었습니다!',
          vi: 'Đã lưu ảnh công thức!',
          en: 'Recipe image saved!'
        }[cwLang] || '저장됨!');
      }
    }, 'image/png');
  }).catch(function() {
    document.body.removeChild(clone);
    _cwShareText(shareText, shareUrl);
  });
}

// 텍스트 전용 공유 (fallback)
function _cwShareText(text, url) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text + '\n' + url).then(function() {
      cwShowToast({ko: '링크가 복사되었습니다!', vi: 'Đã sao chép link!', en: 'Link copied!'}[cwLang] || '복사됨!');
    }).catch(function() {
      cwShowToast({ko: '공유 실패', vi: 'Lỗi chia sẻ', en: 'Share failed'}[cwLang] || '실패');
    });
  }
}

// 레시피 카드에서 공유용 텍스트 추출
function _cwBuildShareText(card, title) {
  var lines = [];
  lines.push('🍜 ' + title);

  var tag = card.querySelector('.cw-product-tag');
  if (tag) lines.push(tag.textContent);

  lines.push('');

  // 재료 추출
  var ingredients = card.querySelectorAll('.cw-ingredient-item');
  if (ingredients.length) {
    lines.push({ko: '📝 재료', vi: '📝 Nguyên liệu', en: '📝 Ingredients'}[cwLang] || '📝 재료');
    ingredients.forEach(function(li) { lines.push('· ' + li.textContent); });
    lines.push('');
  }

  // 조리법 추출
  var steps = card.querySelectorAll('.cw-collapse-content ol li');
  if (steps.length) {
    lines.push({ko: '👨‍🍳 조리법', vi: '👨‍🍳 Cách làm', en: '👨‍🍳 Steps'}[cwLang] || '👨‍🍳 조리법');
    steps.forEach(function(li, i) { lines.push((i+1) + '. ' + li.textContent); });
    lines.push('');
  }

  // 팁 추출
  var tips = card.querySelector('.cw-tips');
  if (tips) lines.push(tips.textContent);

  lines.push('');
  lines.push('🛒 Da-Mi Food | damifood.vn');

  return lines.join('\n');
}

// ─── Toast 알림 ───
function cwShowToast(msg) {
  var el = document.getElementById('toast-message');
  if (el) {
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(function() { el.classList.remove('show'); }, 2500);
  }
}

// ─── 접기/펼치기 제목 생성 ───
function cwCollapseTitle(type, count) {
  if (type === 'ingredients') {
    if (cwLang === 'vi') return '📝 Nguyên liệu (' + count + ')';
    if (cwLang === 'en') return '📝 Ingredients (' + count + ')';
    return '📝 재료 (' + count + '개)';
  }
  if (cwLang === 'vi') return '👨‍🍳 Cách làm (' + count + ' bước)';
  if (cwLang === 'en') return '👨‍🍳 Steps (' + count + ')';
  return '👨‍🍳 조리법 (' + count + '단계)';
}

// ─── 응답 렌더링 ───
function renderCwMessage(data) {
  var L = CW_LANG[cwLang];
  if (data.type === 'recipe') {
    var html = '<div class="cw-recipe-card">';

    if (data.image_url) {
      html += '<img src="' + data.image_url + '" alt="' + (data.title || '') + '" class="cw-recipe-img" loading="lazy">';
      cwSetAvatar('eating');
    }

    html += '<h3>' + (data.title || '') + '</h3>';

    if (data.product) {
      html += '<p class="cw-product-tag">🏷️ ' + data.product + '</p>';
    }

    // ─── 인분 조절 UI (재료 섹션 앞) ───
    var baseServ = data.base_servings || 2;
    html += '<div class="cw-serving-control" data-base="' + baseServ + '">';
    html += '<button class="cw-serv-btn" onclick="cwAdjustServing(this, -1)">−</button>';
    html += '<span class="cw-serv-display">' + baseServ + '</span>';
    var servLabel = {ko: '인분', vi: ' phần', en: ' servings'}[cwLang] || '인분';
    html += '<span class="cw-serv-label">' + servLabel + '</span>';
    html += '<button class="cw-serv-btn" onclick="cwAdjustServing(this, 1)">+</button>';
    html += '</div>';

    // 재료 — 접기/펼치기
    if (data.ingredients && data.ingredients.length) {
      html += '<div class="cw-collapse-section">';
      html += '<button class="cw-collapse-toggle" onclick="this.parentElement.classList.toggle(\'open\')">';
      html += '<span class="cw-collapse-title">' + cwCollapseTitle('ingredients', data.ingredients.length) + '</span>';
      html += '<span class="cw-collapse-arrow">▸</span>';
      html += '</button>';
      html += '<div class="cw-collapse-content"><ul>';
      data.ingredients.forEach(function(i) { html += '<li class="cw-ingredient-item">' + i + '</li>'; });
      html += '</ul></div></div>';
    }

    // 조리법 — 접기/펼치기
    if (data.steps && data.steps.length) {
      html += '<div class="cw-collapse-section">';
      html += '<button class="cw-collapse-toggle" onclick="this.parentElement.classList.toggle(\'open\')">';
      html += '<span class="cw-collapse-title">' + cwCollapseTitle('steps', data.steps.length) + '</span>';
      html += '<span class="cw-collapse-arrow">▸</span>';
      html += '</button>';
      html += '<div class="cw-collapse-content"><ol>';
      data.steps.forEach(function(s) {
        // "1. ", "2. " 등 선행 번호 제거 (<ol>이 자동 번호 부여)
        var cleaned = s.replace(/^\d+\.\s*/, '');
        html += '<li>' + cleaned + '</li>';
      });
      html += '</ol></div></div>';
    }

    // 팁 — 항상 표시
    if (data.tips) {
      var tipsText = '';
      if (Array.isArray(data.tips)) {
        tipsText = data.tips.join(' / ');
      } else {
        tipsText = data.tips;
      }
      html += '<div class="cw-tips">' + L.tips + ': ' + tipsText + '</div>';
    }

    // 액션 버튼
    html += '<div class="cw-recipe-actions">';
    if (data.product_id) {
      html += '<button onclick="cwAddToCart(\'' + data.product_id + '\', 1)" class="cw-action-btn">' + L.cart + '</button>';
    }
    var recipeId = data.recipe_id || data.product_id || '';
    var recipeTitle = (data.title || '').replace(/'/g, "\\'");
    if (recipeId) {
      html += '<button onclick="cwAddToFavorites(\'' + recipeId + '\', \'' + recipeTitle + '\')" class="cw-action-btn">' + L.favorites + '</button>';
    }
    html += '</div>';

    // ─── 퀵리플라이 (새 기능) ───
    var productId = data.product_id || '';
    var qrRecipeTitle = (data.title || '').replace(/'/g, "\\'");
    var qrRecipeId = data.recipe_id || '';
    html += '<div class="cw-quick-replies">';

    // 비슷한 레시피
    var similarMsg = {
      ko: qrRecipeTitle + '과 비슷한 다른 레시피 추천해줘',
      vi: 'Gợi ý món tương tự ' + qrRecipeTitle,
      en: 'Suggest similar recipes to ' + qrRecipeTitle
    }[cwLang] || qrRecipeTitle + '과 비슷한 다른 레시피 추천해줘';
    html += '<button class="cw-qr-btn" onclick="cwSend(\'' + similarMsg.replace(/'/g, "\\'") + '\')">' + CW_QUICK_REPLIES[cwLang][0] + '</button>';

    // 제품 상세보기
    if (productId) {
      html += '<button class="cw-qr-btn" onclick="cwShowProduct(\'' + productId + '\')">' + CW_QUICK_REPLIES[cwLang][1] + '</button>';
    }

    // 레시피 공유
    html += '<button class="cw-qr-btn" onclick="cwShareRecipe(\'' + qrRecipeId + '\', \'' + qrRecipeTitle + '\')">' + CW_QUICK_REPLIES[cwLang][2] + '</button>';

    html += '</div>';

    html += '</div>';
    var recMsgId = cwAppendMessage('bot', html);
    var recImg = document.querySelector('#' + recMsgId + ' .cw-recipe-img');
    if (recImg) {
      if (recImg.complete) {
        cwScrollToTop(recImg);
      } else {
        recImg.onload = function() { cwScrollToTop(recImg); };
      }
    }
  } else {
    var chatHtml = cwMarkdown(data.reply || JSON.stringify(data));
    cwAppendMessage('bot', '<div class="cw-chat-reply">' + chatHtml + '</div>');
  }
}

// ─── 스크롤: 요소를 컨테이너 중앙에 ───
function cwScrollCenter(msgId) {
  var container = document.getElementById('cwMessages');
  var el = document.getElementById(msgId);
  if (!container || !el) return;
  var contRect = container.getBoundingClientRect();
  var elRect = el.getBoundingClientRect();
  var offset = elRect.top - contRect.top + container.scrollTop;
  container.scrollTop = offset - (container.clientHeight - el.offsetHeight) / 2;
}

// ─── 스크롤: 요소를 컨테이너 상단에 ───
function cwScrollToTop(el) {
  var container = document.getElementById('cwMessages');
  if (!container || !el) return;
  var contRect = container.getBoundingClientRect();
  var elRect = el.getBoundingClientRect();
  container.scrollTop += elRect.top - contRect.top;
}

// ─── 메시지 추가 ───
function cwAppendMessage(sender, html) {
  var container = document.getElementById('cwMessages');
  if (!container) return '';

  var id = 'cw-msg-' + (++cwMsgCounter);
  var div = document.createElement('div');
  div.id = id;
  div.className = 'cw-msg cw-msg-' + sender;

  if (sender === 'bot') {
    var avatarSrc = CW_AVATAR_SRCS[CW_AVATAR_STATE] || CW_AVATAR_SRCS.thinking;
    div.innerHTML = '<img src="' + avatarSrc + '" alt="" class="cw-msg-avatar">' +
                    '<div class="cw-bot-text">' + html + '</div>';
  } else {
    div.innerHTML = '<div class="cw-user-text">' + html + '</div>';
  }

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

// ─── 메시지 제거 ───
function cwRemoveMessage(id) {
  var el = document.getElementById(id);
  if (el) el.remove();
}
