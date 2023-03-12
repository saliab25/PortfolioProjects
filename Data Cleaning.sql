/****** Script for SelectTopNRows command from SSMS  ******/
/*
SELECT TOP (1000) [UniqueID ]
      ,[ParcelID]
      ,[LandUse]
      ,[PropertyAddress]
      ,[SaleDate]
      ,[SalePrice]
      ,[LegalReference]
      ,[SoldAsVacant]
      ,[OwnerName]
      ,[OwnerAddress]
      ,[Acreage]
      ,[TaxDistrict]
      ,[LandValue]
      ,[BuildingValue]
      ,[TotalValue]
      ,[YearBuilt]
      ,[Bedrooms]
      ,[FullBath]
      ,[HalfBath]
  FROM [PortProjClean].[dbo].[NashvilleHousing]\
  */

  SELECT *
  FROM PortProjClean.dbo.NashvilleHousing

  -- Standard Date Format

SELECT SaleDateConvert, CONVERT(Date, SaleDate)
	FROM PortProjClean.dbo.NashvilleHousing
	
	UPDATE PortProjClean.dbo.NashvilleHousing
	SET SaleDate = CONVERT(Date, SaleDate)
	
	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD SaleDateConvert Date;

	UPDATE PortProjClean.dbo.NashvilleHousing
	SET SaleDateConvert = CONVERT(Date, SaleDate)

-- Property Address

SELECT *
FROM PortProjClean.dbo.NashvilleHousing
--WHERE PropertyAddress IS NULL
ORDER BY ParcelID

SELECT a.ParcelID, a.PropertyAddress, b.ParcelID, b.PropertyAddress, ISNULL(a.PropertyAddress, b.PropertyAddress)
FROM PortProjClean.dbo.NashvilleHousing a
JOIN PortProjClean.dbo.NashvilleHousing b 
	ON a.ParcelID = b.ParcelID
	AND a.[UniqueID ] <> b.[UniqueID ]
WHERE a.PropertyAddress IS NULL

UPDATE a
SET PropertyAddress = ISNULL(a.PropertyAddress, b.PropertyAddress)
FROM PortProjClean.dbo.NashvilleHousing a
JOIN PortProjClean.dbo.NashvilleHousing b 
	ON a.ParcelID = b.ParcelID
	AND a.[UniqueID ] <> b.[UniqueID ]
WHERE a.PropertyAddress IS NULL

-- Dividing Address Into Separate Columns (Address, City, State)

SELECT PropertyAddress
FROM PortProjClean.dbo.NashvilleHousing
--WHERE PropertyAddress IS NULL
--ORDER BY ParcelID

SELECT 
SUBSTRING(PropertyAddress, 1, CHARINDEX(',', PropertyAddress) -1) AS Address
, SUBSTRING(PropertyAddress, CHARINDEX(',', PropertyAddress) + 1 , LEN(PropertyAddress)) AS Address

FROM PortProjClean.dbo.NashvilleHousing

	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD PropertySplitAddress NVarChar(255);

	UPDATE PortProjClean.dbo.NashvilleHousing
	SET PropertySplitAddress = SUBSTRING(PropertyAddress, 1, CHARINDEX(',', PropertyAddress) -1)

	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD PropertySplitCity NVarChar(255);

	UPDATE PortProjClean.dbo.NashvilleHousing
	SET PropertySplitCity = SUBSTRING(PropertyAddress, CHARINDEX(',', PropertyAddress) + 1 , LEN(PropertyAddress))

SELECT *
FROM PortProjClean.dbo.NashvilleHousing

SELECT OwnerAddress
FROM PortProjClean.dbo.NashvilleHousing

SELECT 
PARSENAME(REPLACE(OwnerAddress, ',', '.'), 3)
,PARSENAME(REPLACE(OwnerAddress, ',', '.'), 2)
,PARSENAME(REPLACE(OwnerAddress, ',', '.'), 1)
FROM PortProjClean.dbo.NashvilleHousing

	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD OwnerSplitAddress NVarChar(255);
	UPDATE PortProjClean.dbo.NashvilleHousing
	SET OwnerSplitAddress = PARSENAME(REPLACE(OwnerAddress, ',', '.'), 3)

	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD OwnerSplitCity NVarChar(255);
	UPDATE PortProjClean.dbo.NashvilleHousing
	SET OwnerSplitCity = PARSENAME(REPLACE(OwnerAddress, ',', '.'), 2)

	ALTER TABLE PortProjClean.dbo.NashvilleHousing
	ADD OwnerSplitState NVarChar(255);
	UPDATE PortProjClean.dbo.NashvilleHousing
	SET OwnerSplitState = PARSENAME(REPLACE(OwnerAddress, ',', '.'), 1)

SELECT *
FROM PortProjClean.dbo.NashvilleHousing

--Change Y and N to Yes and No in "Sold as Vacant" column

SELECT DISTINCT(SoldAsVacant), COUNT(SoldAsVacant)
FROM PortProjClean.dbo.NashvilleHousing
GROUP BY SoldAsVacant
ORDER BY 2

SELECT SoldAsVacant
, CASE WHEN SoldAsVacant = 'Y' THEN 'Yes'
	   WHEN SoldAsVacant = 'N' THEN 'No'
	   ELSE SoldAsVacant
	   END
FROM PortProjClean.dbo.NashvilleHousing

UPDATE PortProjClean.dbo.NashvilleHousing
SET SoldAsVacant = CASE WHEN SoldAsVacant = 'Y' THEN 'Yes'
	   WHEN SoldAsVacant = 'N' THEN 'No'
	   ELSE SoldAsVacant
	   END

-- Removing Duplicates

WITH RowNumCTE AS(
SELECT *,
	ROW_NUMBER() OVER (
	PARTITION BY ParcelID,
				 PropertyAddress,
				 SalePrice,
				 SaleDate,
				 LegalReference
				 ORDER BY
					UniqueID
					) row_num

FROM PortProjClean.dbo.NashvilleHousing
)
SELECT *
FROM RowNumCTE
WHERE row_num > 1
ORDER BY PropertyAddress

-- Deleting Useless Columns

SELECT *
FROM PortProjClean.dbo.NashvilleHousing

ALTER TABLE PortProjClean.dbo.NashvilleHousing
DROP COLUMN OwnerAddress, TaxDistrict, PropertyAddress, SaleDate