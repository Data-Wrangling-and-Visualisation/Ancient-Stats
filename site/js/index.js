document.addEventListener('DOMContentLoaded', function () {
  // Загрузка данных героев
  fetch('constants/heroes.json')
    .then(response => response.json())
    .then(heroesData => {
      const heroes = Object.values(heroesData);

      // Сортировка по имени
      heroes.sort((a, b) => a.localized_name.localeCompare(b.localized_name));

      // Распределение героев по атрибутам
      const strHeroes = heroes.filter(hero => hero.primary_attr === 'str');
      const agiHeroes = heroes.filter(hero => hero.primary_attr === 'agi');
      const intHeroes = heroes.filter(hero => hero.primary_attr === 'int');
      const universalHeroes = heroes.filter(hero => hero.primary_attr === 'all');

      // Отображение героев
      displayHeroes(strHeroes, 'str-heroes', 'str-hero');
      displayHeroes(agiHeroes, 'agi-heroes', 'agi-hero');
      displayHeroes(intHeroes, 'int-heroes', 'int-hero');
      displayHeroes(universalHeroes, 'universal-heroes', 'universal-hero');
    });

  function displayHeroes(heroes, containerId, heroClass) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    heroes.forEach(hero => {
      const heroCard = document.createElement('div');
      heroCard.className = `hero-card ${heroClass}`;

      heroCard.innerHTML = `
        <img src="https://cdn.cloudflare.steamstatic.com${hero.img}" alt="${hero.localized_name}">
        <div class="hero-name">${hero.localized_name}</div>
      `;

      container.appendChild(heroCard);
    });
  }
});