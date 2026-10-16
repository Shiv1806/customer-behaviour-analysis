/*
Customer Behaviour Analysis
SQL Server / T-SQL queries
Prerequisite: load the cleaned dataset into dbo.Customers.
*/

-- 1. Total purchase revenue by gender
SELECT
    gender,
    SUM(purchase_amount) AS total_revenue
FROM dbo.Customers
GROUP BY gender
ORDER BY total_revenue DESC;

-- 2. Customers who used a discount and spent more than the overall average
SELECT
    customer_id,
    gender,
    purchase_amount,
    discount_applied
FROM dbo.Customers
WHERE purchase_amount > (SELECT AVG(purchase_amount) FROM dbo.Customers)
  AND LOWER(LTRIM(RTRIM(discount_applied))) = 'yes'
ORDER BY purchase_amount DESC;

-- 3. Five products with the highest average review rating
SELECT TOP (5)
    item_purchased,
    ROUND(AVG(review_rating), 2) AS average_rating,
    COUNT(*) AS review_count
FROM dbo.Customers
WHERE review_rating IS NOT NULL
GROUP BY item_purchased
ORDER BY AVG(review_rating) DESC, COUNT(*) DESC;

-- 4. Average purchase amount by shipping type
SELECT
    shipping_type,
    ROUND(AVG(purchase_amount), 2) AS average_purchase_amount,
    COUNT(*) AS customer_count
FROM dbo.Customers
GROUP BY shipping_type
ORDER BY average_purchase_amount DESC;

-- 5. Subscription comparison: customers, revenue, and average spend
SELECT
    subscription_status,
    COUNT(*) AS customer_count,
    SUM(purchase_amount) AS total_revenue,
    ROUND(AVG(purchase_amount), 2) AS average_purchase_amount
FROM dbo.Customers
GROUP BY subscription_status
ORDER BY total_revenue DESC;

-- 6. Five products with the highest percentage of discounted purchases
SELECT TOP (5)
    item_purchased,
    COUNT(CASE WHEN LOWER(LTRIM(RTRIM(discount_applied))) = 'yes' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0) AS discount_percentage,
    COUNT(*) AS purchase_count
FROM dbo.Customers
GROUP BY item_purchased
ORDER BY discount_percentage DESC, purchase_count DESC;

-- 7. Segment customers by previous-purchase count
-- These rule-based thresholds are illustrative and can be adjusted.
WITH CustomerSegments AS (
    SELECT
        customer_id,
        previous_purchases,
        CASE
            WHEN previous_purchases <= 1 THEN 'New Customer'
            WHEN previous_purchases < 11 THEN 'Returning Customer'
            ELSE 'Loyal Customer'
        END AS customer_category
    FROM dbo.Customers
)
SELECT
    customer_category,
    COUNT(*) AS customer_count
FROM CustomerSegments
GROUP BY customer_category
ORDER BY customer_count DESC;

-- 8. Three most-purchased products within each product category
WITH ProductPurchases AS (
    SELECT
        category,
        item_purchased,
        COUNT(*) AS number_of_purchases,
        ROW_NUMBER() OVER (
            PARTITION BY category
            ORDER BY COUNT(*) DESC, item_purchased
        ) AS row_num
    FROM dbo.Customers
    GROUP BY category, item_purchased
)
SELECT category, item_purchased, number_of_purchases
FROM ProductPurchases
WHERE row_num <= 3
ORDER BY category, number_of_purchases DESC;

-- 9. Subscription status among customers with more than five previous purchases
SELECT
    subscription_status,
    COUNT(*) AS repeat_customer_count,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS share_of_repeat_customers_pct
FROM dbo.Customers
WHERE previous_purchases > 5
GROUP BY subscription_status
ORDER BY repeat_customer_count DESC;

-- 10. Revenue contribution by age group
SELECT
    age_group,
    SUM(purchase_amount) AS total_revenue,
    ROUND(AVG(purchase_amount), 2) AS average_purchase_amount
FROM dbo.Customers
GROUP BY age_group
ORDER BY total_revenue DESC;

-- 11. Purchase revenue by season
SELECT
    season,
    SUM(purchase_amount) AS total_revenue,
    COUNT(*) AS purchase_count
FROM dbo.Customers
GROUP BY season
ORDER BY total_revenue DESC;
