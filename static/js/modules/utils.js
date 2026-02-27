export function getTypologyTooltip(type) {
  const definitions = {
    'Hidden Gem': 'High investment activity but low public attention. A prime innovation opportunity.',
    Hype: 'High public attention but low actual investment and research activity. Use caution.',
    Established: 'High activity and high attention. A mature market.',
    Nascent: 'Low activity and low attention. Early stage or weak signal.',
  };
  return definitions[type] || 'Signal classification based on activity versus attention.';
}

export function escapeHtml(unsafe) {
  if (unsafe === null || unsafe === undefined) return '';
  const str = String(unsafe);
  const escapeMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return str.replace(/[&<>"']/g, (char) => escapeMap[char]);
}

export function sanitizeUrl(url) {
  if (!url) return '#';

  try {
    const parsedUrl = new URL(String(url).trim(), window.location.origin);
    const allowedProtocols = ['http:', 'https:', 'mailto:'];
    return allowedProtocols.includes(parsedUrl.protocol) ? parsedUrl.href : '#';
  } catch {
    return '#';
  }
}
