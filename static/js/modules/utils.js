export function getTypologyTooltip(type) {
  const definitions = {
    'Hidden Gem': 'High investment activity but low public attention. A prime innovation opportunity.',
    Hype: 'High public attention but low actual investment and research activity. Use caution.',
    Established: 'High activity and high attention. A mature market.',
    Nascent: 'Low activity and low attention. Early stage or weak signal.',
  };
  return definitions[type] || 'Signal classification based on activity versus attention.';
}
