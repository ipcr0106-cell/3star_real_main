/* ★ 쓰리스타 B2C 자사몰 JavaScript ★ */

let cart = JSON.parse(localStorage.getItem('threestar_cart') || '[]');

function addToCart(productId) {
    cart.push(productId);
    localStorage.setItem('threestar_cart', JSON.stringify(cart));
    updateCartCount();
    alert('Added to cart! 🛒');
}

function updateCartCount() {
    document.querySelectorAll('.btn-cart').forEach(btn => {
        btn.textContent = `🛒 Cart (${cart.length})`;
    });
}

document.addEventListener('DOMContentLoaded', updateCartCount);
