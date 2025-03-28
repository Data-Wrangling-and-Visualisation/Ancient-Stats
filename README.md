# Ancient Stats

A standalone service to ensure YOUR victory in any match of DOTA 2.

## What has been done so far?

- Exploratory Data Analysis (EDA) of characteristics of all 126 heroes with additional information about pick/winrate;
- EDA of pick/winrate of heroes based on their rank/division.

### Our API details

Our API currently supports:

- User's general data
- User's match details with possible ranging of number retrieved

General features:

- All retrieved data is stored in MongoDB
- User's ID is stored in session way, so user could not enter it every time for checking diffent pages / data boards

## Running our app

We propose running our application via Docker (currently only API). You can run following commands in the project root:

```bash
# Building container
docker compose -f docker-compose.yml up --build -d
```

```bash
# Running
docker compose -f docker-compose.yml up -d
```

You can check our API functianality in the SwaggerUI at `http://localhost:8080/docs#`
