// 부업 수익 시뮬레이터
// 시간당 단가 x 주당 투입 시간 x 4.345주(월평균) - 유형별 경비 추정치
(function () {
  const rateEl = document.getElementById('calc-rate');
  const hoursEl = document.getElementById('calc-hours');
  const typeEl = document.getElementById('calc-type');
  const resultEl = document.getElementById('calc-result');
  const noteEl = document.getElementById('calc-note');

  function formatWon(n) {
    return Math.round(n).toLocaleString('ko-KR') + '원';
  }

  function compute() {
    const rate = Number(rateEl.value) || 0;
    const hours = Number(hoursEl.value) || 0;
    const type = typeEl.value; // 'freelance' | 'content' | 'resale'

    const monthlyGross = rate * hours * 4.345;

    const expenseRatio = { freelance: 0.033, content: 0.0, resale: 0.15 }[type] ?? 0.033;
    const net = monthlyGross * (1 - expenseRatio);

    resultEl.textContent = formatWon(net);

    const noteByType = {
      freelance: '사업소득세 3.3% 원천징수 가정 (실제는 종합소득세 신고 시 정산)',
      content: '광고/제휴 수익은 플랫폼 지급 기준에 따라 변동될 수 있음',
      resale: '판매수수료·배송비 등 경비 15% 가정 (실제 마진율에 따라 달라짐)',
    };
    noteEl.textContent = noteByType[type] ?? '';
  }

  [rateEl, hoursEl, typeEl].forEach((el) => el && el.addEventListener('input', compute));
  compute();
})();
