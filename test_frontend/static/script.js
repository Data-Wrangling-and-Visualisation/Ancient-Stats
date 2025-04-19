document.addEventListener('DOMContentLoaded', function() {
    const fetchBtn = document.getElementById('fetchBtn');
    const playerIdInput = document.getElementById('playerId');
    const matchCountInput = document.getElementById('matchCount');
    const statsBody = document.getElementById('statsBody');
    let heroChart = null;

    fetchBtn.addEventListener('click', fetchPlayerStats);

    async function fetchPlayerStats() {
        const accountId = playerIdInput.value.trim();
        const matchCount = matchCountInput.value;
        
        if (!accountId) {
            alert('Please enter a player ID');
            return;
        }

        // Show loading state
        statsBody.innerHTML = '<tr><td colspan="7" class="text-center">Loading data...</td></tr>';
        
        try {
            // Fetch data from our Flask API
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

            // Display data in table
            displayHeroStats(data.heroes);
            
            // Display pie chart
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
            
            // Determine win rate class for coloring
            let winRateClass = '';
            if (hero.win_rate >= 60) winRateClass = 'win-rate-high';
            else if (hero.win_rate >= 45) winRateClass = 'win-rate-medium';
            else winRateClass = 'win-rate-low';
            
            // Format duration (seconds to minutes:seconds)
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
            
            statsBody.appendChild(row);
        });
    }
    
    function displayHeroChart(heroData) {
        const ctx = document.getElementById('heroChart').getContext('2d');
        
        // Prepare data for chart
        const labels = heroData.map(hero => hero.name);
        const data = heroData.map(hero => hero.matches);
        
        // Generate random colors for each hero
        const backgroundColors = heroData.map(() => {
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            return `rgba(${r}, ${g}, ${b}, 0.7)`;
        });
        
        // Destroy previous chart if it exists
        if (heroChart) {
            heroChart.destroy();
        }
        
        // Create new chart
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