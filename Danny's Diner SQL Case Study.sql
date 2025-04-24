-- Danny's Diner SQL Case Study
-- Website link: https://8weeksqlchallenge.com/case-study-1/

/* --------------------
   Case Study Questions
   --------------------*/

-- 1. What is the total amount each customer spent at the restaurant?
-- 2. How many days has each customer visited the restaurant?
-- 3. What was the first item from the menu purchased by each customer?
-- 4. What is the most purchased item on the menu and how many times was it purchased by all customers?
-- 5. Which item was the most popular for each customer?
-- 6. Which item was purchased first by the customer after they became a member?
-- 7. Which item was purchased just before the customer became a member?
-- 8. What is the total items and amount spent for each member before they became a member?
-- 9.  If each $1 spent equates to 10 points and sushi has a 2x points multiplier - how many points would each customer have?
-- 10. In the first week after a customer joins the program (including their join date) they earn 2x points on all items, not just sushi - how many points do customer A and B have at the end of January?

-- Example Query:
/*SELECT
	product_id,
    	product_name,
    	price
FROM dannys_diner.menu
ORDER BY price DESC
LIMIT 5;*/

CREATE SCHEMA dannys_diner;
SET search_path = dannys_diner;

CREATE TABLE sales (
  	"customer_id" VARCHAR(1),
  	"order_date" DATE,
  	"product_id" INTEGER
);

INSERT INTO sales
  	("customer_id", "order_date", "product_id")
VALUES
  	('A', '2021-01-01', '1'),
  	('A', '2021-01-01', '2'),
  	('A', '2021-01-07', '2'),
  	('A', '2021-01-10', '3'),
  	('A', '2021-01-11', '3'),
  	('A', '2021-01-11', '3'),
  	('B', '2021-01-01', '2'),
  	('B', '2021-01-02', '2'),
  	('B', '2021-01-04', '1'),
  	('B', '2021-01-11', '1'),
  	('B', '2021-01-16', '3'),
  	('B', '2021-02-01', '3'),
  	('C', '2021-01-01', '3'),
  	('C', '2021-01-01', '3'),
  	('C', '2021-01-07', '3');
 

CREATE TABLE menu (
  	"product_id" INTEGER,
  	"product_name" VARCHAR(5),
  	"price" INTEGER
);

INSERT INTO menu
  	("product_id", "product_name", "price")
VALUES
  	('1', 'sushi', '10'),
  	('2', 'curry', '15'),
  	('3', 'ramen', '12');
  

CREATE TABLE members (
  	"customer_id" VARCHAR(1),
  	"join_date" DATE
);

INSERT INTO members
  	("customer_id", "join_date")
VALUES
  	('A', '2021-01-07'),
  	('B', '2021-01-09');

-- 1. What is the total amount each customer spent at the restaurant?

SELECT s.customer_id, SUM(m.price) AS total_spent
FROM sales s
JOIN menu m ON s.product_id = m.product_id
GROUP BY s.customer_id
ORDER BY s.customer_id;


-- 2. How many days has each customer visited the restaurant?

SELECT customer_id, COUNT(DISTINCT order_date) AS order_days
FROM sales
GROUP BY customer_id
ORDER BY customer_id;

-- 3. What was the first item from the menu purchased by each customer?

SELECT customer_id, product_name, order_date 
FROM (
	SELECT 	s.customer_id, 
	   	m.product_name, 
       		s.order_date, 
       		RANK() OVER (PARTITION BY s.customer_id ORDER BY s.order_date) AS rnk 
	FROM sales s
	JOIN menu m
	ON m.product_id = s.product_id
) AS sub
WHERE rnk = 1;

-- 4. What is the most purchased item on the menu and how many times was it purchased by all customers?

SELECT s.product_id, m.product_name, COUNT(s.customer_id)
FROM sales s
JOIN menu m
ON s.product_id = m.product_id
GROUP BY m.product_name, s.product_id
ORDER BY COUNT(s.customer_id) DESC
LIMIT 1;

-- 5. Which item was the most popular for each customer?

SELECT customer_id, product_name, prc
FROM (
	SELECT 	s.customer_id, m.product_name, COUNT(s.product_id) AS prc, 
		RANK() OVER (PARTITION BY s.customer_id ORDER BY COUNT(s.product_id) DESC) AS rnk
	FROM sales s
	JOIN menu m
	ON m.product_id = s.product_id
	GROUP BY s.customer_id, m.product_name
	ORDER BY s.customer_id, prc DESC
) sub
WHERE rnk = 1;

-- 6. Which item was purchased first by the customer after they became a member?

SELECT sub.customer_id, mn.product_name, sub.order_date 
FROM (
	SELECT 	s.customer_id, s.product_id, s.order_date,
 		RANK() OVER (PARTITION BY s.customer_id ORDER BY s.order_date) AS rnk
	FROM sales s
	JOIN members mb
	ON mb.customer_id = s.customer_id
	WHERE s.order_date > mb.join_date 
	ORDER BY rnk
) sub
JOIN menu mn
ON sub.product_id = mn.product_id
WHERE sub.rnk = 1;

-- 7. Which item was purchased just before the customer became a member?

SELECT sub.customer_id, mn.product_name, sub.order_date
FROM (
	SELECT 	s.customer_id, s.product_id, s.order_date, RANK() OVER (PARTITION BY s.customer_id ORDER BY s.order_date) AS rnk
	FROM sales s
	JOIN members mb
	ON s.customer_id = mb.customer_id
	WHERE s.order_date < mb.join_date
) sub
JOIN menu mn
ON sub.product_id = mn.product_id
WHERE sub.rnk = 1;

-- 8. What is the total items and amount spent for each member before they became a member?

SELECT sub.customer_id, COUNT(sub.product_id), SUM(mn.price)
FROM (
  	SELECT 	s.*, mb.join_date 
  	FROM sales s
  	JOIN members mb
  	ON s.customer_id = mb.customer_id
  	WHERE s.order_date < mb.join_date
) sub
JOIN menu mn
ON sub.product_id = mn.product_id
GROUP BY sub.customer_id;

-- 9.  If each $1 spent equates to 10 points and sushi has a 2x points multiplier - how many points would each customer have?

SELECT s.customer_id, SUM(CASE 	WHEN s.product_id = 1 THEN 20*10
				WHEN s.product_id = 2 THEN 10*15
                                WHEN s.product_id = 3 THEN 10*12
                                ELSE NULL END) AS total_points
FROM sales s
JOIN menu m
ON s.product_id = m.product_id
GROUP BY s.customer_id
ORDER BY s.customer_id;

-- 10. In the first week after a customer joins the program (including their join date) they earn 2x points on all items, not just sushi - how many points do customer A and B have at the end of January?

SELECT sub.customer_id, SUM(CASE WHEN sub.product_id = 1 THEN 20*10
                                 WHEN sub.product_id = 2 AND sub.order_date >= sub.join_date AND sub.order_date < sub.join_date+7 THEN 20*15
                            	 WHEN sub.product_id = 3 AND sub.order_date >= sub.join_date AND sub.order_date < sub.join_date+7 THEN 20*15
				 WHEN sub.product_id = 2 THEN 10*15
                                 WHEN sub.product_id = 3 THEN 10*12                                                  
				 ELSE NULL END) AS total_points
FROM (
  	SELECT 	s.*, mb.join_date
  	FROM sales s
  	FULL JOIN members mb
  	ON s.customer_id = mb.customer_id
) sub
JOIN menu m
ON sub.product_id = m.product_id
GROUP BY sub.customer_id
ORDER BY sub.customer_id;
