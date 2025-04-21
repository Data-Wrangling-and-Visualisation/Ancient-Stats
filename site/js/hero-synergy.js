document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const heroId = params.get('id');

  // Загружаем данные о героях и синергии
  Promise.all([
    fetch('constants/heroes.json').then(res => res.json()),
    fetch(`http://localhost:8080/?rating_id=43&types=with&hero_id=${heroId}`).then(res => res.json()),
    fetch(`http://localhost:8080/?rating_id=43&types=against&hero_id=${heroId}`).then(res => res.json())
  ])
  .then(([heroesData, withData, againstData]) => {
    // Находим текущего героя
    const hero = Object.values(heroesData).find(h => h.id == heroId);
    if (!hero) return;

    // Обновляем информацию о герое
    document.getElementById('hero-info-name').textContent = hero.localized_name;
    document.getElementById('hero-info-img').src = `https://cdn.cloudflare.steamstatic.com${hero.img}`;
    document.getElementById('hero-info-attribute').textContent = `Attribute: ${formatAttr(hero.primary_attr)}`;
    document.getElementById('hero-info-roles').textContent = `Roles: ${hero.roles.join(', ')}`;

    // Формируем данные для таблицы
    const synergyData = prepareSynergyData(heroesData, withData, againstData);
    initTable(synergyData);
  })
  .catch(error => {
    console.error('Error loading data:', error);
    document.getElementById('synergy-data').innerHTML = `
      <tr>
        <td colspan="3" style="text-align: center; color: #ef4444;">
          Error loading data. Please try again later.
        </td>
      </tr>
    `;
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

  // Функция для обработки значений winrate
  function processWinrateValue(value) {
    // Если значение отсутствует, null, undefined, 'N/A' или не число - возвращаем 50%
    if (value === null || value === undefined || value === 'N/A' || isNaN(value)) {
      return 50.0; // 50% по умолчанию
    }
    // Если значение есть - конвертируем в проценты (если оно от 0 до 1)
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return numValue <= 1.0 ? numValue * 100 : numValue;
  }

  // Подготовка данных для таблицы синергии
  function prepareSynergyData(heroesData, withData, againstData) {
    const result = [];

    // Собираем всех уникальных героев из обоих наборов данных
    const allHeroIds = new Set([
      ...Object.keys(withData),
      ...Object.keys(againstData)
    ]);

    allHeroIds.forEach(heroId => {
      const heroInfo = Object.values(heroesData).find(h => h.id == heroId);
      if (!heroInfo) return;

      result.push({
        heroId: heroId,
        hero: heroInfo.localized_name,
        winrateWith: processWinrateValue(withData[heroId]),
        winrateAgainst: processWinrateValue(againstData[heroId])
      });
    });

    return result;
  }

  // Инициализация таблицы
  function initTable(synergyData) {
    const synergyTbody = document.getElementById('synergy-data');
    let currentSort = { column: null, direction: null };

    // Инициализация заголовков
    const headerRow = document.querySelector('.synergy-table thead tr');
    headerRow.innerHTML = `
      <th>Hero</th>
      <th class="sortable" data-column="winrateWith">Winrate With <span class="sort-indicator"></span></th>
      <th class="sortable" data-column="winrateAgainst">Winrate Against <span class="sort-indicator"></span></th>
    `;

    // Обработчики сортировки
    document.querySelectorAll('.sortable').forEach(header => {
      header.addEventListener('click', () => {
        const column = header.getAttribute('data-column');
        toggleSort(column);
      });
    });

    // Функция переключения сортировки
    function toggleSort(column) {
      if (currentSort.column !== column) {
        currentSort.column = column;
        currentSort.direction = 'desc';
      } else {
        if (currentSort.direction === 'desc') {
          currentSort.direction = 'asc';
        } else if (currentSort.direction === 'asc') {
          currentSort.column = null;
          currentSort.direction = null;
        }
      }
      updateSortIndicators();
      renderTable();
    }

    // Обновление индикаторов сортировки
    function updateSortIndicators() {
      document.querySelectorAll('.sort-indicator').forEach(indicator => {
        indicator.textContent = '';
        indicator.style.opacity = '0.5';
      });

      if (currentSort.column) {
        const activeHeader = document.querySelector(`.sortable[data-column="${currentSort.column}"] .sort-indicator`);
        if (activeHeader) {
          activeHeader.textContent = currentSort.direction === 'asc' ? '▲' : '▼';
          activeHeader.style.opacity = '1';
        }
      }
    }

    // Рендеринг таблицы
    function renderTable() {
      synergyTbody.innerHTML = '';

      let dataToRender = [...synergyData];

      // Находим максимальные значения для масштабирования (исключая 50% по умолчанию)
      const maxWith = Math.max(...dataToRender
        .map(item => item.winrateWith)
        .filter(val => val !== 50.0));

      const maxAgainst = Math.max(...dataToRender
        .map(item => item.winrateAgainst)
        .filter(val => val !== 50.0));

      // Если все значения 50%, устанавливаем максимум в 50%
      const effectiveMaxWith = maxWith > 0 ? maxWith : 50.0;
      const effectiveMaxAgainst = maxAgainst > 0 ? maxAgainst : 50.0;

      // Сортировка
      if (currentSort.column) {
        dataToRender.sort((a, b) => {
          const valA = a[currentSort.column];
          const valB = b[currentSort.column];

          if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
          if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
          return 0;
        });
      }

      // Заполняем таблицу
      dataToRender.forEach(item => {
        const isDefaultWith = item.winrateWith === 50.0;
        const isDefaultAgainst = item.winrateAgainst === 50.0;

        const row = document.createElement('tr');
        row.innerHTML = `
          <td class="no-highlight">
            <div class="hero-synergy-info">
              <img src="https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/${item.hero.replace(/\s+/g, '_').toLowerCase()}.png" alt="${item.hero}">
              ${item.hero}
            </div>
          </td>
          <td class="winrate-with no-highlight">
            <div class="winrate-cell">
              ${item.winrateWith.toFixed(1)}%
              <div class="winrate-bar" title="${isDefaultWith ? 'Default value (no data)' : 'Absolute value: ' + item.winrateWith.toFixed(1) + '%'}">
                <div class="winrate-bar-fill ${isDefaultWith ? 'default-value' : ''}" 
                     style="width: ${(item.winrateWith / effectiveMaxWith) * 100}%"></div>
              </div>
            </div>
          </td>
          <td class="winrate-against no-highlight">
            <div class="winrate-cell">
              ${item.winrateAgainst.toFixed(1)}%
              <div class="winrate-bar" title="${isDefaultAgainst ? 'Default value (no data)' : 'Absolute value: ' + item.winrateAgainst.toFixed(1) + '%'}">
                <div class="winrate-bar-fill ${isDefaultAgainst ? 'default-value' : ''}" 
                     style="width: ${(item.winrateAgainst / effectiveMaxAgainst) * 100}%"></div>
              </div>
            </div>
          </td>
        `;
        synergyTbody.appendChild(row);
      });
    }

    // Первоначальный рендеринг
    renderTable();
  }

  // Обновление ссылок в подменю
  const submenuLinks = document.querySelectorAll('.submenu-item');
  submenuLinks.forEach(link => {
    const base = link.getAttribute('href').split('?')[0];
    link.setAttribute('href', `${base}?id=${heroId}`);
  });
});