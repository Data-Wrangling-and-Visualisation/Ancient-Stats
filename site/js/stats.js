let heroStats = [];
let originalOrder = [];
let heroesData = [];
let currentSort = { column: null, direction: 0 };

const tableBody = document.querySelector("#hero-stats tbody");
const RATING_ID = 43;

Promise.all([
  fetch("constants/heroes.json").then(res => res.json()),
  fetch(`http://localhost:5000/?rating_id=${RATING_ID}&types=xpm`).then(res => res.json()),
  fetch(`http://localhost:5000/?rating_id=${RATING_ID}&types=gpm`).then(res => res.json()),
  fetch(`http://localhost:5000/?rating_id=${RATING_ID}&types=raw`).then(res => res.json())
])
.then(([heroesJson, xpmData, gpmData, winrateRaw]) => {
  heroesData = Object.values(heroesJson);

  const winrate = {};
  for (const [heroId, rate] of Object.entries(winrateRaw)) {
      winrate[heroId] = rate;
  }

  heroStats = Object.keys(xpmData).map(heroId => {
    const id = parseInt(heroId);
    return {
      hero_id: id,
      name: heroesData.find(h => h.id === id)?.localized_name || "Unknown",
      xpm: Math.round(xpmData[heroId]),
      gpm: Math.round(gpmData[heroId]),
      winrate: +(winrate[heroId] * 100).toFixed(1)
    };
  });

  originalOrder = [...heroStats];
  renderTable(heroStats);
});

function renderTable(stats) {
  tableBody.innerHTML = "";

  const maxWinrate = Math.max(...heroStats.map(h => h.winrate));
  const maxXpm = Math.max(...heroStats.map(h => h.xpm));
  const maxGpm = Math.max(...heroStats.map(h => h.gpm));

  stats.forEach(stat => {
    const hero = heroesData.find(h => h.id === stat.hero_id);
    const imgUrl = hero ? `https://cdn.cloudflare.steamstatic.com${hero.img}` : "";

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>
        <div class="hero-info">
          <img src="${imgUrl}" alt="${stat.name}" />
          <span>${stat.name}</span>
        </div>
      </td>
      <td>
        <div class="stat-cell">
          ${stat.winrate}%
          <div class="stat-bar">
            <div class="stat-bar-fill winrate-bar" style="width: ${(stat.winrate / maxWinrate) * 100}%"></div>
          </div>
        </div>
      </td>
      <td>
        <div class="stat-cell">
          ${stat.xpm}
          <div class="stat-bar">
            <div class="stat-bar-fill xpm-bar" style="width: ${(stat.xpm / maxXpm) * 100}%"></div>
          </div>
        </div>
      </td>
      <td>
        <div class="stat-cell">
          ${stat.gpm}
          <div class="stat-bar">
            <div class="stat-bar-fill gpm-bar" style="width: ${(stat.gpm / maxGpm) * 100}%"></div>
          </div>
        </div>
      </td>
    `;
    tableBody.appendChild(row);
  });

  updateSortIndicators();
}

function handleSort(column) {
  if (currentSort.column === column) {
    currentSort.direction = (currentSort.direction + 1) % 3;
  } else {
    currentSort.column = column;
    currentSort.direction = 1;
  }

  if (currentSort.direction === 0) {
    renderTable(originalOrder);
  } else {
    const sorted = [...heroStats].sort((a, b) => {
      return currentSort.direction === 1
        ? b[column] - a[column]
        : a[column] - b[column];
    });
    renderTable(sorted);
  }
}

function updateSortIndicators() {
  document.querySelectorAll("th[data-key]").forEach(th => {
    const key = th.dataset.key;

    th.classList.add("sortable");
    const oldIndicator = th.querySelector(".sort-indicator");
    if (oldIndicator) oldIndicator.remove();

    if (key === currentSort.column && currentSort.direction !== 0) {
      const arrow = currentSort.direction === 1 ? "▼" : "▲";
      const indicator = document.createElement("span");
      indicator.className = "sort-indicator";
      indicator.textContent = arrow;
      th.appendChild(indicator);
    }
  });
}

document.querySelectorAll("th[data-key]").forEach(th => {
  th.addEventListener("click", () => {
    handleSort(th.dataset.key);
  });
});