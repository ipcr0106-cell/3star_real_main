/**
 * chatbot-widget.js — 다국어 라벨, 장바구니 연동, 즐겨찾기, history JSON 계약
 */

// ─── 다국어 라벨 ───
const LANG = {
    ko: {
        categories: ["🍲 국물·탕", "🍜 면·볶음면", "🥩 구이·볶음", "🥗 쌈·샐러드", "🍚 밥·죽", "🧋 간식·음료"],
        tastes: ["🌶️ 매운", "🥜 고소", "💧 담백", "🍯 달콤", "🍋 새콤", "🧂 짭짤", "🍘 바삭", "✨ 감칠맛", "🔥 얼큰"],
        selectCategory: "카테고리를 선택하세요:",
        selectTaste: "어떤 맛을 원하세요?",
        placeholder: "메시지를 입력하세요...",
        send: "전송 🚀",
        loading: "🔄 응답 생성 중...",
        error: "⚠️ 오류가 발생했어요. 다시 시도해 주세요.",
    },
    vi: {
        categories: ["🍲 Canh·Lẩu", "🍜 Mì·Bún", "🥩 Nướng·Xào", "🥗 Cuốn·Salad", "🍚 Cơm·Cháo", "🧋 Snack·Đồ uống"],
        tastes: ["🌶️ Cay", "🥜 Béo", "💧 Thanh", "🍯 Ngọt", "🍋 Chua", "🧂 Mặn", "🍘 Giòn", "✨ Umami", "🔥 Nóng"],
        selectCategory: "Chọn loại món:",
        selectTaste: "Bạn muốn vị gì?",
        placeholder: "Nhập tin nhắn...",
        send: "Gửi 🚀",
        loading: "🔄 Đang tạo phản hồi...",
        error: "⚠️ Đã xảy ra lỗi. Vui lòng thử lại.",
    },
    en: {
        categories: ["🍲 Soup", "🍜 Noodle", "🥩 Grill·Stir-fry", "🥗 Wrap·Salad", "🍚 Rice·Porridge", "🧋 Snack·Drink"],
        tastes: ["🌶️ Spicy", "🥜 Nutty", "💧 Light", "🍯 Sweet", "🍋 Sour", "🧂 Salty", "🍘 Crispy", "✨ Umami", "🔥 Hot"],
        selectCategory: "Choose a category:",
        selectTaste: "What flavor do you want?",
        placeholder: "Type a message...",
        send: "Send 🚀",
        loading: "🔄 Generating response...",
        error: "⚠️ An error occurred. Please try again.",
    }
};

const CATEGORY_VALUES = ["국물탕", "면볶음면", "구이볶음", "쌈샐러드", "밥죽", "간식음료"];
const TASTE_VALUES = ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"];


// ─── 대화 히스토리 (JSON 계약) ───
let conversationHistory = [];


// ─── 장바구니 연동 ───
function addToCart(productId, quantity) {
    quantity = quantity || 1;
    if (typeof window.addToCartFromChatbot === 'function') {
        window.addToCartFromChatbot(productId, quantity);
    } else if (typeof window.PRODUCTS !== 'undefined' && window.PRODUCTS[productId]) {
        console.log('Added to cart:', productId, 'x' + quantity);
        showToast('🛒 ' + (window.PRODUCTS[productId].name || productId) + ' ' + quantity + '개 장바구니에 추가!');
    } else {
        showToast('🛒 ' + productId + ' 장바구니에 추가!');
    }
}


// ─── 즐겨찾기 ───
let favorites = JSON.parse(localStorage.getItem('chatbot_favorites') || '[]');

function addToFavorites(recipeId, recipeName) {
    if (!favorites.find(function(f) { return f.id === recipeId; })) {
        favorites.push({id: recipeId, name: recipeName, savedAt: new Date().toISOString()});
        localStorage.setItem('chatbot_favorites', JSON.stringify(favorites));
        showToast('⭐ "' + recipeName + '" 즐겨찾기 추가!');
    } else {
        showToast('이미 즐겨찾기에 있어요!');
    }
}

function showFavorites() {
    if (favorites.length === 0) {
        showToast('즐겨찾기가 비어있어요!');
        return;
    }
    var html = '<div class="favorites-list"><h4>⭐ 즐겨찾기</h4><ul>';
    favorites.forEach(function(f) {
        html += '<li>' + f.name + ' <small>(' + f.savedAt.slice(0, 10) + ')</small></li>';
    });
    html += '</ul></div>';
    appendMessage('bot', html);
}


// ─── 서버 응답 처리 (JSON 계약) ───
function handleResponse(data, loadingId) {
    // 로딩 메시지 제거
    if (loadingId) {
        var loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
    }

    // 렌더링은 formatted data 사용
    renderMessage(data);

    // 히스토리는 _raw (GPT 원본) 보존
    var rawContent = data._raw || data;
    conversationHistory.push({
        role: "assistant",
        content: JSON.stringify(rawContent)
    });
}


// ─── 응답 렌더링 (레시피 카드 + 액션 버튼) ───
function renderMessage(data) {
    if (data.type === 'recipe') {
        var html = '<div class="recipe-card">';
        html += '<h3>' + (data.title || '') + '</h3>';
        if (data.title_vn) html += '<p class="vn-name">' + data.title_vn + '</p>';
        if (data.product) html += '<p class="product-tag">🏷️ ' + data.product + '</p>';

        // 이미지
        if (data.image_url) {
            html += '<img src="' + data.image_url + '" alt="' + (data.title || '') + '" class="recipe-image" loading="lazy">';
        }

        // 재료
        if (data.ingredients && data.ingredients.length) {
            html += '<div class="ingredients"><h4>재료</h4><ul>';
            data.ingredients.forEach(function(i) { html += '<li>' + i + '</li>'; });
            html += '</ul></div>';
        }

        // 조리법
        if (data.steps && data.steps.length) {
            html += '<div class="steps"><h4>조리법</h4><ol>';
            data.steps.forEach(function(s) { html += '<li>' + s + '</li>'; });
            html += '</ol></div>';
        }

        // 팁
        if (data.tips && data.tips.length) {
            html += '<div class="tips"><h4>💡 팁</h4><ul>';
            if (Array.isArray(data.tips)) {
                data.tips.forEach(function(t) { html += '<li>' + t + '</li>'; });
            } else {
                html += '<li>' + data.tips + '</li>';
            }
            html += '</ul></div>';
        }

        // 액션 버튼
        html += '<div class="recipe-actions">';
        if (data.product_id) {
            html += '<button onclick="addToCart(\'' + data.product_id + '\', 1)" class="cart-btn">🛒 장바구니</button>';
        }
        var recipeId = data.recipe_id || data.product_id || '';
        var recipeTitle = (data.title || '').replace(/'/g, "\\'");
        if (recipeId) {
            html += '<button onclick="addToFavorites(\'' + recipeId + '\', \'' + recipeTitle + '\')" class="fav-btn">⭐ 즐겨찾기</button>';
        }
        html += '</div>';

        // links
        if (data.links && data.links.length) {
            html += '<div class="recipe-links">';
            data.links.forEach(function(l) { html += '<a href="' + l.url + '">' + l.label + '</a> '; });
            html += '</div>';
        }

        html += '</div>';
        appendMessage('bot', html);
    } else {
        // chat 타입
        appendMessage('bot', data.reply || JSON.stringify(data));
    }
}


// ─── 메시지 추가 헬퍼 ───
var _msgCounter = 0;
function appendMessage(sender, html) {
    var win = document.getElementById('chatWindow');
    if (!win) return '';
    var id = 'msg-' + (++_msgCounter);
    var div = document.createElement('div');
    div.id = id;
    div.className = 'msg msg-' + (sender === 'user' ? 'user' : 'bot');
    div.innerHTML = html;
    win.appendChild(div);
    win.scrollTop = win.scrollHeight;
    return id;
}


// ─── Toast 알림 ───
function showToast(msg) {
    // cart.js의 showToast가 있으면 사용
    var existing = document.getElementById('toast-message');
    if (existing && typeof existing.classList !== 'undefined') {
        existing.textContent = msg;
        existing.classList.add('show');
        setTimeout(function() { existing.classList.remove('show'); }, 2500);
        return;
    }
    // fallback
    var toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3000);
}
