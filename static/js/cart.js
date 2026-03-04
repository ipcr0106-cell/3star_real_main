/* ★ 쓰리스타 장바구니 — cart.js ★
 * localStorage 기반으로 DB 없이 동작
 * products.json의 id와 매핑됨
 */

// ─── 제품 정보 (products.json과 동일하게 유지) ───
const PRODUCTS = {
  coin_01:   { name: "Beef Yukgaejang Coin Broth",           price: 89000, category: "코인육수" },
  coin_02:   { name: "Anchovy Noodle Soup Coin Broth",       price: 85000, category: "코인육수" },
  coin_03:   { name: "Spicy Vegetable Coin Broth (Vegan)",   price: 85000, category: "코인육수" },
  coin_04:   { name: "Kimchi-Tamarind Fusion Coin Broth",    price: 92000, category: "코인육수" },
  season_01: { name: "K-BBQ Bulgogi Seasoning",              price: 45000, category: "가루시즈닝" },
  season_02: { name: "Pork Bone Soup Seasoning",             price: 45000, category: "가루시즈닝" },
  season_03: { name: "Spicy Chicken Galbi Seasoning",        price: 45000, category: "가루시즈닝" },
  season_04: { name: "Abalone Porridge Seasoning",           price: 55000, category: "가루시즈닝" },
  sauce_01:  { name: "Cheongyang Mayo Sauce",                price: 62000, category: "액체소스" },
  sauce_02:  { name: "Plum Seafood Dipping Sauce",           price: 65000, category: "액체소스" },
  sauce_03:  { name: "Ssamjang Herb Sauce",                  price: 65000, category: "액체소스" },
  sauce_04:  { name: "K-Rose Lemongrass Stir-fry Sauce",     price: 68000, category: "액체소스" },
  sauce_05:  { name: "Bulgogi Coconut BBQ Glaze",            price: 72000, category: "액체소스" },
  sauce_06:  { name: "Mango Gochujang Wing Sauce",           price: 68000, category: "액체소스" },
  food_01:   { name: "Misutgaru Coconut Powder",             price: 55000, category: "푸드" },
  food_02:   { name: "Seaweed Coconut Chip",                 price: 48000, category: "푸드" },
};

const STORAGE_KEY = "threestar_cart"; // localStorage 키 이름

// ─── 장바구니 데이터 로드/저장 ───
function getCart() {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  // 형태: { "coin_01": 2, "sauce_01": 1 } (id: 수량)
}

function saveCart(cart) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
}

// ─── 장바구니에 추가 ───
function addToCart(productId) {
  const cart = getCart();
  cart[productId] = (cart[productId] || 0) + 1;
  saveCart(cart);
  updateCartUI();
  showToast(`✅ 장바구니에 추가했어요! (${PRODUCTS[productId]?.name || productId})`);
}

// ─── 수량 변경 ───
function changeQty(productId, delta) {
  const cart = getCart();
  const newQty = (cart[productId] || 0) + delta;
  if (newQty <= 0) {
    delete cart[productId];
  } else {
    cart[productId] = newQty;
  }
  saveCart(cart);
  renderCartModal();
  updateCartUI();
}

// ─── 장바구니에서 삭제 ───
function removeFromCart(productId) {
  const cart = getCart();
  delete cart[productId];
  saveCart(cart);
  renderCartModal();
  updateCartUI();
}

// ─── 장바구니 비우기 ───
function clearCart() {
  localStorage.removeItem(STORAGE_KEY);
  renderCartModal();
  updateCartUI();
}

// ─── 총 수량 계산 ───
function getTotalCount() {
  const cart = getCart();
  return Object.values(cart).reduce((sum, qty) => sum + qty, 0);
}

// ─── 총 금액 계산 ───
function getTotalPrice() {
  const cart = getCart();
  return Object.entries(cart).reduce((sum, [id, qty]) => {
    return sum + (PRODUCTS[id]?.price || 0) * qty;
  }, 0);
}

// ─── 상단 Cart 버튼 업데이트 ───
function updateCartUI() {
  const count = getTotalCount();
  document.querySelectorAll(".btn-cart").forEach(btn => {
    btn.textContent = `🛒 Cart (${count})`;
    btn.classList.toggle("has-items", count > 0);
  });
}

// ─── 장바구니 모달 렌더링 ───
function renderCartModal() {
  const cart = getCart();
  const container = document.getElementById("cart-items");
  const totalEl = document.getElementById("cart-total");
  if (!container) return;

  const entries = Object.entries(cart);

  if (entries.length === 0) {
    container.innerHTML = `<p class="cart-empty">장바구니가 비어 있어요 🛒</p>`;
    if (totalEl) totalEl.textContent = "₫0";
    return;
  }

  container.innerHTML = entries.map(([id, qty]) => {
    const product = PRODUCTS[id] || { name: id, price: 0 };
    const subtotal = (product.price * qty).toLocaleString();
    return `
      <div class="cart-item">
        <div class="cart-item-info">
          <span class="cart-item-name">${product.name}</span>
          <span class="cart-item-category">${product.category}</span>
        </div>
        <div class="cart-item-controls">
          <button onclick="changeQty('${id}', -1)">−</button>
          <span>${qty}</span>
          <button onclick="changeQty('${id}', +1)">+</button>
        </div>
        <div class="cart-item-price">₫${subtotal}</div>
        <button class="cart-item-remove" onclick="removeFromCart('${id}')">✕</button>
      </div>
    `;
  }).join("");

  if (totalEl) totalEl.textContent = `₫${getTotalPrice().toLocaleString()}`;
}

// ─── 장바구니 모달 열기/닫기 ───
function openCartModal() {
  renderCartModal();
  document.getElementById("cart-modal")?.classList.add("open");
}

function closeCartModal() {
  document.getElementById("cart-modal")?.classList.remove("open");
}

// ─── 구매하기 버튼 (UI만, 결제 미구현) ───
function proceedToCheckout() {
  alert("구매 기능은 준비 중이에요! 곧 연동될 예정입니다. 🙏");
}

// ─── 토스트 알림 ───
function showToast(message) {
  let toast = document.getElementById("toast-message");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast-message";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

// ─── chatbot 연동용 window 노출 ───
if (typeof window !== 'undefined') {
  window.PRODUCTS = PRODUCTS;
  window.addToCartFromChatbot = function(productId, qty) {
    const cart = getCart();
    cart[productId] = (cart[productId] || 0) + (qty || 1);
    saveCart(cart);
    updateCartUI();
    showToast(`✅ 장바구니에 추가했어요! (${PRODUCTS[productId]?.name || productId})`);
  };
}

// ─── 페이지 로드 시 초기화 ───
document.addEventListener("DOMContentLoaded", () => {
  updateCartUI();

  // Cart 버튼 클릭 → 모달 열기
  document.querySelectorAll(".btn-cart").forEach(btn => {
    btn.addEventListener("click", openCartModal);
  });

  // 모달 바깥 클릭 → 닫기
  document.getElementById("cart-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "cart-modal") closeCartModal();
  });
});
