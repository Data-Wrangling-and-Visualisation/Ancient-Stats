document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const heroId = params.get('id');

  // Добавим id героя в ссылку на hero-synergy
  const synergyLink = document.getElementById('synergy-link');
  if (synergyLink && heroId) {
    synergyLink.href = `hero-synergy.html?id=${heroId}`;
  }

  const infoLink = document.getElementById('info-link');
  if (infoLink && heroId) {
    infoLink.href = `hero-info.html?id=${heroId}`;
  }

  fetch('constants/heroes.json')
    .then(res => res.json())
    .then(data => {
      const hero = Object.values(data).find(h => h.id == heroId);
      if (!hero) return;

      document.getElementById('hero-info-name').textContent = hero.localized_name;
      document.getElementById('hero-info-img').src = `https://cdn.cloudflare.steamstatic.com${hero.img}`;
      document.getElementById('hero-info-attribute').textContent = `Attribute: ${formatAttr(hero.primary_attr)}`;
      document.getElementById('hero-info-roles').textContent = `Roles: ${hero.roles.join(', ')}`;

      const statsList = document.getElementById('hero-info-stats-list');
      const stats = [
        [`Attack Type`, hero.attack_type],
        [`Base Health`, hero.base_health],
        [`Health Regen`, hero.base_health_regen],
        [`Base Mana`, hero.base_mana],
        [`Mana Regen`, hero.base_mana_regen],
        [`Armor`, hero.base_armor],
        [`Magic Resist`, hero.base_mr + '%'],
        [`Attack Damage`, `${hero.base_attack_min} - ${hero.base_attack_max}`],
        [`STR`, `${hero.base_str} (+${hero.str_gain})`],
        [`AGI`, `${hero.base_agi} (+${hero.agi_gain})`],
        [`INT`, `${hero.base_int} (+${hero.int_gain})`],
        [`Attack Range`, hero.attack_range],
        [`Move Speed`, hero.move_speed],
        [`Day Vision`, hero.day_vision],
        [`Night Vision`, hero.night_vision]
      ];

      stats.forEach(([label, value]) => {
        const li = document.createElement('li');
        li.textContent = `${label}: ${value}`;
        statsList.appendChild(li);
      });
    });

  function formatAttr(attr) {
    switch (attr) {
      case 'str': return 'Strength';
      case 'agi': return 'Agility';
      case 'int': return 'Intelligence';
      case 'all': return 'Universal';
      default: return attr;
    }
  }
});
