/* ★ 쓰리스타 B2C 자사몰 JavaScript ★
 * 장바구니 기능은 cart.js가 담당 (addToCart, updateCartUI 등)
 * main.js는 cart.js 외 추가 B2C 로직만 관리
 */

// 페이지 로드 시 cart.js의 updateCartUI 호출 (중복 안전)
document.addEventListener('DOMContentLoaded', function() {
  if (typeof updateCartUI === 'function') {
    updateCartUI();
  }
});
