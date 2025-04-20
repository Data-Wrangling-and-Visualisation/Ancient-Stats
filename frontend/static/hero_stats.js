document.addEventListener('DOMContentLoaded', function() {
    const fetchBtn = document.getElementById('fetchBtn');
    const heroIdInput = document.getElementById('heroId');
    const ratingIdInput = document.getElementById('ratingId');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const heroInfo = document.getElementById('heroInfo');
    const chartsContainer = document.getElementById('chartsContainer');
    
    let xpChart = null;
    let withChart = null;
    let itemChart = null;
    let allHeroesCache = null;

    fetchBtn.addEventListener('click', fetchHeroStats);

    async function fetchHeroStats() {
        const heroId = heroIdInput.value;
        const ratingId = ratingIdInput.value;
        
        if (!heroId || heroId < 1 || heroId > 145) {
            alert('Please enter a valid hero ID (1-145)');
            return;
        }
        
        if (!ratingId || ratingId < 11 || ratingId > 43) {
            alert('Please enter a valid rank (11-43)');
            return;
        }

        // Show loading state
        loadingIndicator.style.display = 'block';
        chartsContainer.style.display = 'none';
        heroInfo.style.display = 'none';
        
        try {
            // First fetch hero name
            const heroName = await getHeroName(heroId);
            document.getElementById('heroNameDisplay').textContent = `${heroName} (ID: ${heroId}) at Rank ${ratingId}`;
            heroInfo.style.display = 'block';
            
            // Fetch all three data types in parallel
            const [xpData, withData, itemData] = await Promise.all([
                fetchHeroData(heroId, ratingId, 'xp'),
                fetchHeroData(heroId, ratingId, 'with'),
                fetchHeroData(heroId, ratingId, 'item')
            ]);
            
            // Render all charts
            renderXpChart(xpData);
            renderWithChart(withData);
            renderItemChart(itemData);
            
            // Show results
            chartsContainer.style.display = 'block';
        } catch (error) {
            console.error('Error fetching hero stats:', error);
            alert(`Error: ${error.message}`);
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }
    
    async function fetchHeroData(heroId, ratingId, type) {
        const response = await fetch(`/api/hero/${heroId}/stats/${ratingId}/${type}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${type} data`);
        }
        return await response.json();
    }
    
    async function getHeroName(heroId) {
        if (!allHeroesCache) {
            const response = await fetch('/api/heroes');
            if (!response.ok) throw new Error('Failed to fetch heroes list');
            allHeroesCache = await response.json();
        }
        
        const hero = allHeroesCache.find(h => h.id == heroId);
        return hero ? hero.name : `Hero ${heroId}`;
    }
    
    function renderXpChart(data) {
        const ctx = document.getElementById('xpChart').getContext('2d');
        const sortedLevels = Object.keys(data).map(Number).sort((a, b) => a - b);
        const winrates = sortedLevels.map(level => data[level] * 100);
        
        if (xpChart) xpChart.destroy();
        
        xpChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sortedLevels,
                datasets: [{
                    label: 'Winrate %',
                    data: winrates,
                    backgroundColor: 'rgba(137, 219, 210, 0.7)',
                    borderColor: 'rgba(137, 219, 210, 1)',
                    borderWidth: 1
                }]
            },
            options: getChartOptions('Hero Level', 'Winrate %')
        });
    }
    
    async function renderWithChart(data) {
        const ctx = document.getElementById('withChart').getContext('2d');
        
        // First get all heroes if not already cached
        if (!allHeroesCache) {
            const response = await fetch('/api/heroes');
            if (!response.ok) throw new Error('Failed to fetch heroes list');
            allHeroesCache = await response.json();
        }
        
        // Process and sort data
        const entries = Object.entries(data).map(([heroId, winrate]) => ({
            heroId: parseInt(heroId),
            winrate: winrate * 100, // Convert to percentage
            heroName: allHeroesCache.find(h => h.id == heroId)?.name || `Hero ${heroId}`
        }));
        
        // Sort by winrate descending and take top 20
        entries.sort((a, b) => b.winrate - a.winrate);
        const topEntries = entries.slice(0, 20);
        
        if (withChart) withChart.destroy();
        
        withChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topEntries.map(entry => entry.heroName),
                datasets: [{
                    label: 'Winrate %',
                    data: topEntries.map(entry => entry.winrate),
                    backgroundColor: 'rgba(137, 219, 210, 0.7)',
                    borderColor: 'rgba(137, 219, 210, 1)',
                    borderWidth: 1
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
                            text: 'Hero Name'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            autoSkip: false,
                            font: {
                                size: 10
                            }
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
    
    function renderItemChart(data) {
        const ctx = document.getElementById('itemChart').getContext('2d');
        const sortedData = sortAndProcessData(data);
        
        if (itemChart) itemChart.destroy();
        
        itemChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sortedData.labels,
                datasets: [{
                    label: 'Winrate %',
                    data: sortedData.values,
                    backgroundColor: 'rgba(137, 219, 210, 0.7)',
                    borderColor: 'rgba(137, 219, 210, 1)',
                    borderWidth: 1
                }]
            },
            options: getChartOptions('Item ID', 'Winrate %')
        });
    }
    
    function sortAndProcessData(data) {
        // Convert to array and sort by winrate descending
        const entries = Object.entries(data).map(([key, value]) => ({
            key,
            value: value * 100 // Convert to percentage
        }));
        
        entries.sort((a, b) => b.value - a.value);
        
        // Limit to top 20 items for better readability
        const topEntries = entries.slice(0, 20);
        
        return {
            labels: topEntries.map(entry => entry.key),
            values: topEntries.map(entry => entry.value)
        };
    }
    
    function getChartOptions(xLabel, yLabel) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
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
                        text: xLabel
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yLabel
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
        };
    }
});