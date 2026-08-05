/* 概览页逻辑（函数模块，供 Flask 页面与静态页路由复用） */
window.Pages = window.Pages || {};
window.Pages.overview = async function () {
  try {
    const data = await API.get('/api/overview');
    animateNumber('m-lines', data.total_lines);
    animateNumber('m-events', data.total_events);
    animateNumber('m-sources', data.total_sources);
    animateNumber('m-speakers', data.total_speakers);
  } catch (e) {
    Util.showError('metricsGrid', '加载概览数据失败: ' + e.message);
  }

  function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 800;
    const start = performance.now();
    function step(now) {
      const p = Math.min((now - start) / duration, 1);
      el.textContent = Math.floor(target * p).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  }
};
