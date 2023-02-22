SELECT * FROM CovidDeaths WHERE continent IS NOT NULL ORDER BY 1, 2;
SELECT * FROM CovidVaccins WHERE continent IS NOT NULL ORDER BY 1, 2;

--Data that I'm going to be using

SELECT Location, date, total_cases, new_cases, total_deaths, population
FROM CovidDeaths ORDER BY 1, 2;

-- Total Cases vs Total Deaths in the US

SELECT location, date, total_cases, total_deaths, 
ROUND((total_deaths/total_cases)*100, 3) AS Death_Percentage
FROM CovidDeaths
WHERE location LIKE '%states%' AND  continent IS NOT NULL
ORDER BY 1, 2;

--Total Cases vs Population in the US

SELECT location, date, total_cases, population,
ROUND((total_cases/population)*100, 3) AS Covid_Percentage
FROM CovidDeaths
WHERE location LIKE '%states%' AND  continent IS NOT NULL
ORDER BY 1, 2;

--Ranking Countries By Infection Rate 

SELECT location, population, MAX(total_cases) AS Max_Infection_Count, 
ROUND(MAX((total_cases/population))*100, 3) AS Infection_Rate
FROM CovidDeaths
WHERE continent IS NOT NULL
GROUP BY location, population
ORDER BY Infection_Rate DESC;

-- Ranking Countries By Death Count

SELECT location, MAX(CAST(total_deaths AS BIGINT)) AS Max_Death_Count
FROM CovidDeaths
WHERE continent IS NOT NULL
GROUP BY location
ORDER BY Max_Death_Count DESC;

-- Ranking Continents by Death Counts

SELECT continent, MAX(CAST(total_deaths AS BIGINT)) AS Max_Death_Count
FROM CovidDeaths
WHERE continent IS NOT NULL
GROUP BY continent
ORDER BY Max_Death_Count DESC;

-- Ranking New Cases by Dates

SELECT date, SUM(new_cases) AS New_Cases, SUM(CAST(new_deaths AS BIGINT)) AS New_Deaths,
ROUND(SUM(CAST(new_deaths AS BIGINT))/SUM(new_cases)*100, 3) AS Death_Percentage
FROM CovidDeaths
WHERE Continent IS NOT NULL
GROUP BY date
ORDER BY Death_Percentage DESC;

-- New Vaccinations by Date

SELECT dth.location, dth.date, vcc.new_vaccinations AS New_Vaccinations 
FROM CovidDeaths AS dth JOIN CovidVaccins AS vcc
ON dth.location = vcc.location AND dth.date = vcc.date
WHERE dth.continent IS NOT NULL
ORDER BY 1, 2;

-- New Vaccinations and Total Vaccinations per day

SELECT dth.location, dth.date, dth.population, vcc.new_vaccinations AS New_Vaccinations,
SUM(CONVERT(BIGINT, vcc.new_vaccinations)) OVER
(PARTITION BY dth.location ORDER BY dth.location, dth.date) AS Total_Vaccinations
FROM CovidDeaths AS dth JOIN CovidVaccins AS vcc
ON dth.location = vcc.location AND dth.date = vcc.date
WHERE dth.continent IS NOT NULL
ORDER BY 1, 2;

-- CTE for Percentage of new vaccinations by population

WITH PopVac (location, date, population, new_vaccination, Total_Vaccinations)
AS
(
	SELECT dth.location, dth.date, dth.population, vcc.new_vaccinations AS New_Vaccinations,
	SUM(CONVERT(BIGINT, vcc.new_vaccinations)) OVER
	(PARTITION BY dth.location ORDER BY dth.location, dth.date) AS Total_Vaccinations
	FROM CovidDeaths AS dth JOIN CovidVaccins AS vcc
	ON dth.location = vcc.location AND dth.date = vcc.date
	WHERE dth.continent IS NOT NULL	
)
SELECT *, ROUND((Total_Vaccinations/Population)*100, 3) AS VaccinationPercentage
FROM PopVac;

-- TEMP TABLE for Percentage of new vaccinations by population

CREATE TABLE #Vaccination_Percentage
(
	location nvarchar(255),
	date datetime,
	population numeric,
	new_vaccinations numeric,
	Total_Vaccinations numeric
)
INSERT INTO #Vaccination_Percentage
SELECT dth.location, dth.date, dth.population, vcc.new_vaccinations AS New_Vaccinations,
SUM(CONVERT(BIGINT, vcc.new_vaccinations)) OVER
(PARTITION BY dth.location ORDER BY dth.location, dth.date) AS Total_Vaccinations
FROM CovidDeaths AS dth JOIN CovidVaccins AS vcc
ON dth.location = vcc.location AND dth.date = vcc.date
WHERE dth.continent IS NOT NULL;

SELECT *, ROUND((Total_Vaccinations/Population)*100, 3) AS VaccinationPercentage
FROM #Vaccination_Percentage;

--CREATE VIEW to store data later for visualizations

CREATE VIEW Vaccination_Percentage AS
SELECT dth.location, dth.date, dth.population, vcc.new_vaccinations AS New_Vaccinations,
SUM(CONVERT(BIGINT, vcc.new_vaccinations)) OVER
(PARTITION BY dth.location ORDER BY dth.location, dth.date) AS Total_Vaccinations
FROM CovidDeaths AS dth JOIN CovidVaccins AS vcc
ON dth.location = vcc.location AND dth.date = vcc.date
WHERE dth.continent IS NOT NULL;

SELECT *
FROM Vaccination_Percentage;