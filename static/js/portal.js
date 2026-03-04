/* ★ DA-MI FOOD B2B 포탈 — portal.js ★ */
console.log('★ DA-MI FOOD Portal loaded');

/*
 * 시계 담당: 이 파일만 #gnbClock을 업데이트함
 * - dashboard 페이지: 자체 #time-kr / #time-vn을 쓰므로 스킵
 * - 그 외 모든 페이지: VN | KR 듀얼 타임 표시
 */
(function initClock() {
  if (document.body.classList.contains('page-dashboard')) return;

  const el  = document.getElementById('gnbClock');
  if (!el) return;

  const pad = n => String(n).padStart(2, '0');

  function tick() {
    const now = new Date();

    const vn  = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Ho_Chi_Minh' }));
    const vnH = vn.getHours(), vnM = vn.getMinutes(), vnS = vn.getSeconds();
    const vnAP = vnH >= 12 ? 'PM' : 'AM';
    const vnH12 = vnH % 12 || 12;

    const kr  = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
    const krH = kr.getHours(), krM = kr.getMinutes(), krS = kr.getSeconds();
    const krAP = krH >= 12 ? 'PM' : 'AM';
    const krH12 = krH % 12 || 12;

    el.textContent =
      `VN ${pad(vnH12)}:${pad(vnM)}:${pad(vnS)} ${vnAP}  |  KR ${pad(krH12)}:${pad(krM)}:${pad(krS)} ${krAP}`;
  }

  tick();
  setInterval(tick, 1000);
})();