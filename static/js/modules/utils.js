export function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const str = String(text);
  const escapeMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  const pattern = /[&<>"']/g;
  if (!pattern.test(str)) return str;
  return str.replace(pattern, (ch) => escapeMap[ch]);
}

export function getTypologyTooltip(type) {
  const definitions = {
    'Hidden Gem': 'High investment activity but low public attention. A prime innovation opportunity.',
    Hype: 'High public attention but low actual investment and research activity. Use caution.',
    Established: 'High activity and high attention. A mature market.',
    Nascent: 'Low activity and low attention. Early stage or weak signal.',
  };
  return definitions[type] || 'Signal classification based on activity versus attention.';
}
