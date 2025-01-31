import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose

#Read data from CSV
df = pd.read_csv(r'D:\Downloads\tdt2.csv')

#Removing all rows with NULL values
df.dropna(inplace = True)

#Sorting by the DATE then NAME columns
df.sort_values(by=['DATE', 'NAME'], inplace = True)

#Convert DATE column to datetime format
df['DATE'] = pd.to_datetime(df['DATE'])

#Aggregate data by date (mean precipitation and temperature across all stations)
daily_data = df.groupby('DATE')[['PRCP', 'TAVG']].mean().reset_index()

# Plot time series trends
plt.figure(figsize=(14, 6))
plt.subplot(2, 1, 1)
plt.plot(daily_data['DATE'], daily_data['PRCP'], label='Daily Precipitation (inches)', color='blue')
plt.xlabel('Date')
plt.ylabel('Precipitation')
plt.title('Daily Precipitation Trends (Jun - Sep 2024)')
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(daily_data['DATE'], daily_data['TAVG'], label='Daily Temperature (°F)', color='red')
plt.xlabel('Date')
plt.ylabel('Temperature')
plt.title('Daily Temperature Trends (Jun - Sep 2024)')
plt.legend()

plt.tight_layout()
plt.show()

# Rolling averages for smoothing trends
daily_data['PRCP_rolling'] = daily_data['PRCP'].rolling(window=7).mean()
daily_data['TAVG_rolling'] = daily_data['TAVG'].rolling(window=7).mean()

plt.figure(figsize=(14, 6))
plt.plot(daily_data['DATE'], daily_data['PRCP_rolling'], label='7-day Rolling Avg PRCP', color='blue')
plt.plot(daily_data['DATE'], daily_data['TAVG_rolling'], label='7-day Rolling Avg TAVG', color='red')
plt.xlabel('Date')
plt.ylabel('Values')
plt.title('7-Day Rolling Averages of Precipitation and Temperature')
plt.legend()
plt.show()

# Seasonal decomposition of precipitation
decomposition = seasonal_decompose(daily_data['PRCP'], model='additive', period=30)
decomposition.plot()
plt.suptitle('Seasonal Decomposition of Precipitation')
plt.show()

# Correlation analysis
correlation = daily_data[['PRCP', 'TAVG']].corr()
print("Correlation between Precipitation and Temperature:\n", correlation)

sns.heatmap(correlation, annot=True, cmap='coolwarm', linewidths=0.5)
plt.title('Correlation Heatmap')
plt.show()