// Constants for data visualization
const margin = { top: 50, right: 30, bottom: 50, left: 60 },
    width = 800 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

// Append SVG object to the page
const svg = d3.select("#chart")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

// Define color scale for attributes
const colorScale = d3.scaleOrdinal()
    .domain(["str", "agi", "int", "all"])
    .range(["#ef4444", "#10b981", "#3b82f6", "#8b5cf6"]);

// Format attribute names for display
const formatAttr = (attr) => {
    switch (attr) {
        case 'str': return 'Strength';
        case 'agi': return 'Agility';
        case 'int': return 'Intelligence';
        case 'all': return 'Universal';
        default: return attr;
    }
};

// Tooltip div
const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

// RATING ID - similar to what's used in stats.js
const RATING_ID = 43;

// Fetch data from API endpoints
Promise.all([
    fetch("constants/heroes.json").then(res => res.json()),
    fetch(`http://localhost:8080/stats/?rating_id=${RATING_ID}&types=raw`).then(res => res.json())
])
    .then(([heroesData, winrateData]) => {
        // Process hero data to get win rates by attribute
        const attributeGroups = {
            str: [],
            agi: [],
            int: [],
            all: []
        };

        // Group heroes by primary attribute and calculate win rates
        for (const [heroId, winrate] of Object.entries(winrateData)) {
            const hero = Object.values(heroesData).find(h => h.id == heroId);
            if (hero) {
                const winratePercentage = +(winrate * 100).toFixed(2);

                attributeGroups[hero.primary_attr].push({
                    id: hero.id,
                    name: hero.localized_name,
                    primary_attr: hero.primary_attr,
                    winrate: winratePercentage
                });
            }
        }

        // Calculate attribute averages for the visualization
        const attributeAverages = ['str', 'agi', 'int', 'all'].map(attr => {
            const heroes = attributeGroups[attr];
            const avgWinrate = heroes.length > 0 ?
                heroes.reduce((sum, hero) => sum + hero.winrate, 0) / heroes.length :
                50;

            return {
                attribute: attr,
                attributeName: formatAttr(attr),
                avgWinrate: parseFloat(avgWinrate.toFixed(2)),
                heroes: heroes
            };
        });

        // X-axis: Primary Attribute
        const x = d3.scaleBand()
            .domain(attributeAverages.map(d => d.attribute))
            .range([0, width])
            .padding(0.2);

        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x).tickFormat(d => formatAttr(d)))
            .selectAll("text")
            .attr("class", "axis-label");

        // Y-axis: Win Rate
        const y = d3.scaleLinear()
            .domain([45, 55]) // Reasonable range for win rates
            .range([height, 0]);

        svg.append("g")
            .call(d3.axisLeft(y))
            .selectAll("text")
            .attr("class", "axis-label");

        // Add bars for average win rates
        svg.selectAll(".bar")
            .data(attributeAverages)
            .enter()
            .append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d.attribute))
            .attr("width", x.bandwidth())
            .attr("y", d => y(d.avgWinrate))
            .attr("height", d => height - y(d.avgWinrate))
            .attr("fill", d => colorScale(d.attribute))
            .on("mouseover", (event, d) => {
                tooltip.transition()
                    .duration(200)
                    .style("opacity", 0.9);
                tooltip.html(`<strong>${d.attributeName}</strong><br/>Average Win Rate: ${d.avgWinrate}%<br/>Heroes: ${d.heroes.length}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => {
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            })
            .on("click", (event, d) => {
                // Show heroes of this attribute below the chart
                displayHeroes(d.heroes);
            });

        // Add a title
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", -margin.top / 2)
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("font-weight", "bold")
            .text("Dota 2 Hero Win Rates by Primary Attribute");

        // Add labels
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height + margin.bottom - 10)
            .attr("text-anchor", "middle")
            .attr("class", "axis-label")
            .text("Primary Attribute");

        svg.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", -margin.left + 15)
            .attr("x", -height / 2)
            .attr("text-anchor", "middle")
            .attr("class", "axis-label")
            .text("Win Rate (%)");

        // Function to display heroes below the chart when an attribute is clicked
        function displayHeroes(heroes) {
            // Create or clear the heroes container
            let heroesContainer = d3.select("#heroes-list");
            if (heroesContainer.empty()) {
                heroesContainer = d3.select("body")
                    .append("div")
                    .attr("id", "heroes-list")
                    .style("margin-top", "20px")
                    .style("max-width", width + margin.left + margin.right)
                    .style("margin-left", "auto")
                    .style("margin-right", "auto");
            }

            heroesContainer.html("");

            heroesContainer.append("h3")
                .text(`Heroes (${heroes.length})`);

            const table = heroesContainer.append("table")
                .style("width", "100%")
                .style("border-collapse", "collapse");

            const thead = table.append("thead");
            thead.append("tr")
                .selectAll("th")
                .data(["Hero", "Win Rate"])
                .enter()
                .append("th")
                .text(d => d)
                .style("padding", "8px")
                .style("border-bottom", "1px solid #ddd")
                .style("text-align", "left");

            const tbody = table.append("tbody");

            // Sort heroes by win rate, highest first
            const sortedHeroes = [...heroes].sort((a, b) => b.winrate - a.winrate);

            tbody.selectAll("tr")
                .data(sortedHeroes)
                .enter()
                .append("tr")
                .selectAll("td")
                .data(d => [d.name, d.winrate + "%"])
                .enter()
                .append("td")
                .text(d => d)
                .style("padding", "8px")
                .style("border-bottom", "1px solid #ddd");
        }
    })
    .catch(error => {
        console.error("Error loading hero data:", error);
        d3.select("#chart")
            .append("p")
            .attr("class", "error-message")
            .text("Failed to load hero data. Please try again later.");
    });
