import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

#Loading the dataset
df = pd.read_csv(r'D:\Downloads\nycwq.csv')

#Dropping columns
df.drop(['Sample Number', 'Sample Time', 'Sample class', 'Coliform (Quanti-Tray) (MPN /100mL)', 'E.coli(Quanti-Tray) (MPN/100mL)'], axis=1, inplace=True)

#Removing all rows with NULL values
df.dropna(inplace=True)


# Convert numerical columns to float (handling errors by coercion)
num_cols = ['Residual Free Chlorine (mg/L)', 'Turbidity (NTU)', 'Fluoride (mg/L)']
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')

# Check if there are any NaN values after conversion
print(df[num_cols].isna().sum())  # This will show any problematic rows

df.dropna(subset=num_cols, inplace=True)  # Remove rows with invalid numbers


#Convert "Sample Date" column to datetime format
df['Sample Date'] = pd.to_datetime(df['Sample Date'])

#Define EPA Maximum Contaminant Levels (MCLs) for drinking water
EPA_LIMITS = {
    'Residual Free Chlorine (mg/L)': 4.0,  # Maximum allowed chlorine level
    'Turbidity (NTU)': 1.0,  # Should not exceed 1 NTU
    'Fluoride (mg/L)': 4.0  # Maximum allowed fluoride level
}

#Create violation columns
df['Chlorine_Violation'] = df['Residual Free Chlorine (mg/L)'] > EPA_LIMITS['Residual Free Chlorine (mg/L)']
df['Turbidity_Violation'] = df['Turbidity (NTU)'] > EPA_LIMITS['Turbidity (NTU)']
df['Fluoride_Violation'] = df['Fluoride (mg/L)'] > EPA_LIMITS['Fluoride (mg/L)']

# Calculate violation percentages
violation_summary = {
    'Chlorine': df['Chlorine_Violation'].mean() * 100,
    'Turbidity': df['Turbidity_Violation'].mean() * 100,
    'Fluoride': df['Fluoride_Violation'].mean() * 100
}

# Print violation summary
print("Water Quality Violation Summary:")
for contaminant, percent in violation_summary.items():
    print(f"{contaminant} violations: {percent:.2f}% of days")

# Plot violations over time
plt.figure(figsize=(14, 6))
sns.lineplot(data=df, x='Sample Date', y='Residual Free Chlorine (mg/L)', label='Chlorine', color='blue')
sns.lineplot(data=df, x='Sample Date', y='Turbidity (NTU)', label='Turbidity', color='red')
sns.lineplot(data=df, x='Sample Date', y='Fluoride (mg/L)', label='Fluoride', color='green')
plt.axhline(EPA_LIMITS['Residual Free Chlorine (mg/L)'], color='blue', linestyle='dashed', label='Chlorine Limit')
plt.axhline(EPA_LIMITS['Turbidity (NTU)'], color='red', linestyle='dashed', label='Turbidity Limit')
plt.axhline(EPA_LIMITS['Fluoride (mg/L)'], color='green', linestyle='dashed', label='Fluoride Limit')
plt.xlabel('Date')
plt.ylabel('Concentration')
plt.title('NYC Water Quality vs. EPA Standards')
plt.legend()
plt.show()
