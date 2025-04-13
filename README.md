# Ancient Stats

A standalone service to ensure YOUR victory in any match of DOTA 2.

## Project Progress Report

### Current Status

The project is currently in active development, focusing on building a comprehensive DOTA 2 statistics service. We have completed the core API functionality and are working on enhancing the statistical analysis capabilities.

### Completed Milestones

1. **API Development (Completed)**

   - FastAPI backend implementation
   - MongoDB integration
   - Docker containerization
   - Session-based authentication
   - Basic error handling

2. **Data Collection (Completed)**

   - Hero data collection from OpenDota API
   - Match data processing
   - Player statistics aggregation

3. **Statistical Analysis (Completed)**
   - Basic hero statistics
   - Match outcome analysis
   - Player performance metrics
   - GPM/XPM calculations

### Next Steps

1. **Frontend Development**

   - **Interactive Data Visualization (In Progress)**

     - Designing the visually appealing style for analytical panels:
     - Hero win rate trends using D3.js line charts
     - Hero pick rate distribution with D3.js bar charts
     - Player performance radar charts using P5.js
     - Match timeline visualization with D3.js

   - **Technical Implementation**

     - Integrate D3.js for data visualization
     - Implement P5.js for interactive elements

## Features

### Player Statistics

- Detailed player profiles and match history
- Session-based authentication for persistent user data
- Match data retrieval with pagination support
- Real-time player data updates

### Hero Analytics

- Complete database of all 126 DOTA 2 heroes
- Hero statistics across different skill brackets
- Detailed hero performance metrics including:
  - Win rates
  - Pick rates
  - GPM (Gold Per Minute)
  - XPM (Experience Per Minute)
  - Item preferences
  - Synergy statistics (heroes played with/against)

### Match Analysis

- Detailed match information
- Player performance metrics
- Team composition analysis
- Match outcome statistics

## Repository Structure

```
Ancient-Stats/
├── api/                    # Backend API service, main files for running
│   ├── models/            # Data models and managers
│   ├── stats/              # Classes for statistics calculation
│   ├── utils/              # Error handling logic
├── EDA/                   # Exploratory Data Analysis notebooks
├── data/                 # Data storage (initial, in some way not used now)
├── matches/              # Match data
├── testing/              # Tests notes
├── docker-compose.yml    # Docker services configuration
```

## Technical Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Containerization**: Docker
- **API Documentation**: SwaggerUI
- **Frontend**: D3.js (and possibly P5.js)

## API Endpoints

### Player Management

- `POST /set-user-id` - Set user ID in session
- `GET /me` - Get current player data
- `GET /me/matches` - Get current player's matches
- `GET /update_player/{player_id}` - Update player data
- `GET /players/{player_id}` - Get specific player data
- `GET /players/{player_id}/matches` - Get specific player's matches

### Hero Data

- `GET /heroes` - Get all heroes
- `GET /heroes/{hero_id}` - Get specific hero data

### Match Data

- `GET /matches/{match_id}` - Get detailed match data

### Statistics

- `GET /stats/` - Get hero stats for all heroes
- `GET /stats/{hero_id}/` - Get stats for specific hero

Statistics types available:

- `against` - Performance against specific heroes
- `raw` - Raw performance statistics
- `with` - Performance when playing with specific heroes
- `xp` - Experience-related statistics
- `item` - Item usage statistics
- `xpm` - Experience per minute statistics
- `gpm` - Gold per minute statistics

## Installation and Setup

1. Clone the repository
2. Ensure Docker & Docker Compose are installed
3. Run the following commands:

```bash
# Build and start the containers
docker compose -f docker-compose.yml up --build -d

# Or just start if already built
docker compose -f docker-compose.yml up -d
```

The API will be available at `http://localhost:8080` with SwaggerUI documentation at `http://localhost:8080/docs`

## Environment Variables

- `MONGO_URL` - MongoDB connection URL (default: mongodb://localhost:27017)
- `MONGO_DB` - MongoDB database name (default: db)

## Development Status

### Completed Features

- Player data management and retrieval
- Hero statistics and analytics
- Match data processing
- Session-based authentication (kinda: it's only user ID memorization)
- MongoDB integration
- Docker containerization

### In Progress

- Additional statistical analysis
- Performance optimizations
- Enhanced error handling
