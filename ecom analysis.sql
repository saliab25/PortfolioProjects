-- 1. Total Sales by Product Category: This query calculates the total sales (Net Amount) for each product category.

SELECT 
    `Product Category`, 
    SUM(`Net Amount`) AS Total_Sales
FROM 
    ecommerce_data
GROUP BY 
    `Product Category`
ORDER BY 
    Total_Sales DESC;

-- 2. Average Discount Amount by Location: This query calculates the average discount amount availed by customers in each city.

SELECT 
    Location, 
    AVG(`Discount Amount (INR)`) AS Avg_Discount_Amount
FROM 
    ecommerce_data
WHERE 
    `Discount Availed` = 'Yes'
GROUP BY 
    Location
ORDER BY 
    Avg_Discount_Amount DESC;

-- 3. Top 5 Cities with Highest Sales: This query identifies the top 5 cities with the highest total sales (Net Amount).

SELECT 
    Location, 
    SUM(`Net Amount`) AS Total_Sales
FROM 
    ecommerce_data
GROUP BY 
    Location
ORDER BY 
    Total_Sales DESC
LIMIT 5;

-- 4. Discount Usage by Purchase Method: This query analyzes how often discounts are used with each purchase method.

SELECT 
    `Purchase Method`, 
    COUNT(*) AS Total_Transactions,
    SUM(CASE WHEN `Discount Availed` = 'Yes' THEN 1 ELSE 0 END) AS Discount_Transactions,
    (SUM(CASE WHEN `Discount Availed` = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS Discount_Usage_Percentage
FROM 
    ecommerce_data
GROUP BY 
    `Purchase Method`
ORDER BY 
    Discount_Usage_Percentage DESC;

-- 5. Total Revenue Before and After Discount: This query calculates the total revenue before (Gross Amount) and after (Net Amount) applying discounts.

SELECT 
    SUM(`Gross Amount`) AS Total_Gross_Revenue,
    SUM(`Net Amount`) AS Total_Net_Revenue,
    SUM(`Gross Amount` - `Net Amount`) AS Total_Discount_Given
FROM 
    ecommerce_data;

-- 6. Most Popular Discounts: This query identifies the most popular discounts based on how often they were used.

SELECT 
    `Discount Name`, 
    COUNT(*) AS Usage_Count
FROM 
    ecommerce_data
WHERE 
    `Discount Availed` = 'Yes'
GROUP BY 
    `Discount Name`
ORDER BY 
    Usage_Count DESC;

-- 7. Monthly Sales Trend: This query calculates the total sales (Net Amount) for each month.

SELECT 
    DATE_FORMAT(`Purchase Date`, '%Y-%m') AS Month, 
    SUM(`Net Amount`) AS Total_Sales
FROM 
    ecommerce_data
GROUP BY 
    DATE_FORMAT(`Purchase Date`, '%Y-%m')
ORDER BY 
    Month;

-- 8. Average Gross and Net Amount by Product Category: This query calculates the average Gross Amount and Net Amount for each product category.

SELECT 
    `Product Category`, 
    AVG(`Gross Amount`) AS Avg_Gross_Amount,
    AVG(`Net Amount`) AS Avg_Net_Amount
FROM 
    ecommerce_data
GROUP BY 
    `Product Category`
ORDER BY 
    Avg_Net_Amount DESC;

-- 9. Discount Impact on Sales: This query analyzes the impact of discounts on sales by comparing the average Net Amount for transactions with and without discounts.

SELECT 
    `Discount Availed`, 
    AVG(`Net Amount`) AS Avg_Net_Amount
FROM 
    ecommerce_data
GROUP BY 
    `Discount Availed`;

-- 10. Top 10 Customers by Total Spending: This query identifies the top 10 customers based on their total spending (Net Amount).

SELECT 
    CID, 
    SUM(`Net Amount`) AS Total_Spending
FROM 
    ecommerce_data
GROUP BY 
    CID
ORDER BY 
    Total_Spending DESC
LIMIT 10;

-- 11. Discount Amount Distribution by Product Category: This query calculates the total discount amount availed for each product category.

SELECT 
    `Product Category`, 
    SUM(`Discount Amount (INR)`) AS Total_Discount_Amount
FROM 
    ecommerce_data
WHERE 
    `Discount Availed` = 'Yes'
GROUP BY 
    `Product Category`
ORDER BY 
    Total_Discount_Amount DESC;

-- 12. Purchase Method Distribution: This query analyzes the distribution of purchase methods used by customers.

SELECT 
    `Purchase Method`, 
    COUNT(*) AS Transaction_Count
FROM 
    ecommerce_data
GROUP BY 
    `Purchase Method`
ORDER BY 
    Transaction_Count DESC;

-- 13. Discount Usage by Product Category: This query analyzes how often discounts are used for each product category.

SELECT 
    `Product Category`, 
    COUNT(*) AS Total_Transactions,
    SUM(CASE WHEN `Discount Availed` = 'Yes' THEN 1 ELSE 0 END) AS Discount_Transactions,
    (SUM(CASE WHEN `Discount Availed` = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS Discount_Usage_Percentage
FROM 
    ecommerce_data
GROUP BY 
    `Product Category`
ORDER BY 
    Discount_Usage_Percentage DESC;

-- 14. Total Sales by Day of the Week: This query calculates the total sales (Net Amount) for each day of the week.

SELECT 
    DAYNAME(`Purchase Date`) AS Day_of_Week, 
    SUM(`Net Amount`) AS Total_Sales
FROM 
    ecommerce_data
GROUP BY 
    DAYNAME(`Purchase Date`)
ORDER BY 
    Total_Sales DESC;

-- 15. Discount Amount vs. Gross Amount Analysis: This query analyzes the relationship between the discount amount and the gross amount.

SELECT 
    `Discount Amount (INR)`, 
    AVG(`Gross Amount`) AS Avg_Gross_Amount
FROM 
    ecommerce_data
WHERE 
    `Discount Availed` = 'Yes'
GROUP BY 
    `Discount Amount (INR)`
ORDER BY 
    `Discount Amount (INR)`;