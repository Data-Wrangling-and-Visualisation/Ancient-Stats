document.addEventListener('DOMContentLoaded', function() {
    const fetchBtn = document.getElementById('fetchBtn');
    const playerIdInput = document.getElementById('playerId');
    const matchCountInput = document.getElementById('matchCount');
    const statsBody = document.getElementById('statsBody');
    let heroChart = null;
    let heroWinrateGraph = null;
    let currentOpenHeroId = null;

    fetchBtn.addEventListener('click', fetchPlayerStats);

    async function fetchPlayerStats() {
        const accountId = playerIdInput.value.trim();
        const matchCount = matchCountInput.value;
        
        if (!accountId) {
            alert('Please enter a player ID');
            return;
        }

        statsBody.innerHTML = '<tr><td colspan="7" class="text-center">Loading data...</td></tr>';
        
        try {
            const response = await fetch(`http://localhost:5000/api/player/${accountId}/stats?count=${matchCount}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch data');
            }
            
            const data = await response.json();
            
            if (!data.heroes || data.heroes.length === 0) {
                statsBody.innerHTML = '<tr><td colspan="7" class="text-center">No matches found for this player</td></tr>';
                return;
            }

            displayHeroStats(data.heroes);
            
            displayHeroChart(data.heroes);
            
        } catch (error) {
            console.error('Error fetching data:', error);
            //console.log('Response: ', response);
            statsBody.innerHTML = `<tr><td colspan="7" class="text-center">Error: ${error.message}</td></tr>`;
        }
    }

    function displayHeroStats(heroData) {
        statsBody.innerHTML = '';
        
        heroData.forEach(hero => {
            const row = document.createElement('tr');
            row.className = 'hero-row';
            row.dataset.heroId = hero.hero_id;
            
            let winRateClass = '';
            if (hero.win_rate >= 60) winRateClass = 'win-rate-high';
            else if (hero.win_rate >= 45) winRateClass = 'win-rate-medium';
            else winRateClass = 'win-rate-low';
            
            const durationMinutes = Math.floor(hero.avg_duration / 60);
            const durationSeconds = Math.floor(hero.avg_duration % 60);
            const formattedDuration = `${durationMinutes}:${durationSeconds.toString().padStart(2, '0')}`;
            
            row.innerHTML = `
                <td>${hero.name}</td>
                <td>${hero.matches}</td>
                <td class="win-rate-cell ${winRateClass}">${hero.win_rate.toFixed(1)}%</td>
                <td>${hero.avg_kills.toFixed(1)}</td>
                <td>${hero.avg_deaths.toFixed(1)}</td>
                <td>${hero.avg_assists.toFixed(1)}</td>
                <td>${formattedDuration}</td>
            `;
            
            row.addEventListener('click', () => toggleHeroWinrateGraph(hero.hero_id, hero.name));
            statsBody.appendChild(row);
        });
    }

    async function toggleHeroWinrateGraph(heroId, heroName) {
        const container = document.getElementById('heroWinrateGraphContainer');
        const heroNameBadge = document.getElementById('heroNameBadge');
        const rows = document.querySelectorAll('.hero-row');

        heroNameBadge.textContent = heroName;

        rows.forEach(row => {
            if (row.dataset.heroId === heroId.toString()) {
                row.classList.toggle('active-hero-row');
            } else {
                row.classList.remove('active-hero-row');
            }
        });

        if (currentOpenHeroId === heroId) {
            container.style.display = container.style.display === 'none' ? 'block' : 'none';
            return;
        }

        container.style.display = 'block';
        document.getElementById('heroWinrateGraph').innerHTML = '<div class="text-center p-2">Loading winrate data...</div>';
        
        currentOpenHeroId = heroId;
        
        try {
            const response = await fetch(`/api/hero/${heroId}/winrate-by-level`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch winrate data');
            }
            
            const data = await response.json();

            if (currentOpenHeroId === heroId) {
                heroNameBadge.textContent = data.hero_name;
                renderHeroWinrateGraph(data.hero_name, data.levels, data.winrates);
            }
        } catch (error) {
            console.error('Error fetching hero winrate data:', error);
            document.getElementById('heroWinrateGraph').innerHTML = 
                `<div class="text-center p-2 text-danger">Error: ${error.message}</div>`;
        }
    }

    function renderHeroWinrateGraph(heroName, levels, winrates) {
        const ctx = document.getElementById('heroWinrateGraph').getContext('2d');

        if (heroWinrateGraph) {
            heroWinrateGraph.destroy();
        }
        
        heroWinrateGraph = new Chart(ctx, {
            type: 'line',
            data: {
                labels: levels,
                datasets: [{
                    label: `${heroName} Winrate`,
                    data: winrates,
                    borderColor: '#89dbd2',
                    backgroundColor: 'rgba(137, 219, 210, 0.1)',
                    borderWidth: 2,
                    pointBackgroundColor: '#89dbd2',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `${heroName} - Level ${context[0].label}`;
                            },
                            label: function(context) {
                                return `${context.parsed.y.toFixed(1)}% winrate`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Hero Level'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Winrate %'
                        },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    function displayHeroChart(heroData) {
        const ctx = document.getElementById('heroChart').getContext('2d');
        
        const labels = heroData.map(hero => hero.name);
        const data = heroData.map(hero => hero.matches);
        
        const backgroundColors = heroData.map(() => {
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            return `rgba(${r}, ${g}, ${b}, 0.7)`;
        });
        
        if (heroChart) {
            heroChart.destroy();
        }
        
        heroChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
});