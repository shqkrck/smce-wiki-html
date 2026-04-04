function filterNav(){
  const q = (document.getElementById('navSearch')?.value || '').toLowerCase();
  document.querySelectorAll('[data-nav-item]').forEach(el => {
    const text = el.getAttribute('data-nav-item').toLowerCase();
    el.style.display = text.includes(q) ? '' : 'none';
  });
}
