# Import necessary libraries
import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, f_oneway, pearsonr, chi2_contingency
import statsmodels.api as sm

# Load the dataset
file_path = r'C:\Users\berth\.cache\kagglehub\datasets\bhadramohit\smartphone-usage-and-behavioral-dataset\versions\1\mobile_usage_behavioral_analysis.csv'
df = pd.read_csv(file_path)

# Check the dataset
print(df.head())
print(df.info())

# A/B Test: Comparing Screen Time by Gender
group1 = df[df['Gender'] == 'Male']['Daily_Screen_Time_Hours']
group2 = df[df['Gender'] == 'Female']['Daily_Screen_Time_Hours']

# Perform an independent t-test
t_stat, p_value = ttest_ind(group1, group2, equal_var=False)  # Welch’s t-test
print(f"T-statistic: {t_stat}, P-value: {p_value}")

if p_value < 0.05:
    print("Reject the null hypothesis: There is a significant difference in screen time between genders.")
else:
    print("Fail to reject the null hypothesis: No significant difference in screen time between genders.")

# Correlation Analysis: Age vs. Total App Usage
corr, corr_p_value = pearsonr(df['Age'], df['Total_App_Usage_Hours'])
print(f"Correlation between Age and Total App Usage: {corr}, P-value: {corr_p_value}")

# ANOVA: Comparing Social Media Usage Across Locations
anova_groups = [group['Social_Media_Usage_Hours'].dropna() for _, group in df.groupby('Location')]
f_stat, anova_p_value = f_oneway(*anova_groups)
print(f"ANOVA F-statistic: {f_stat}, P-value: {anova_p_value}")

# Chi-Square Test: Gender vs. Gaming Usage
df['Gaming_Category'] = pd.cut(df['Gaming_App_Usage_Hours'], bins=[0, 1, 5, 10, np.inf], labels=['Low', 'Medium', 'High', 'Very High'])
contingency_table = pd.crosstab(df['Gender'], df['Gaming_Category'])
chi2, chi2_p, dof, expected = chi2_contingency(contingency_table)
print(f"Chi-Square Test Statistic: {chi2}, P-value: {chi2_p}")

# Regression Analysis: Predict Total App Usage
# Prepare the data
X = df[['Age', 'Daily_Screen_Time_Hours', 'Social_Media_Usage_Hours', 'Productivity_App_Usage_Hours', 'Gaming_App_Usage_Hours']]
y = df['Total_App_Usage_Hours']

# Add a constant for the intercept
X = sm.add_constant(X)

# Fit the regression model
model = sm.OLS(y, X).fit()
print(model.summary())
