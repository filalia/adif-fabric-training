-- Declare and set the variables in the same statement using placeholder format
DECLARE @SourceName VARCHAR(50) = '<%=$sourcename%>'  -- Example: Source name placeholder
DECLARE @SourceSchema VARCHAR(50) = '<%=$sourceschema%>'  -- Example: Schema name placeholder
DECLARE @SourceObject VARCHAR(50) = '<%=$sourceobject%>'  -- Example: Object name placeholder
DECLARE @TargetSchema Varchar(50) = '<%=$targetschema%>'
DECLARE @TargetObject Varchar(50) = '<%=$targetobject%>'
-- Declare and set variables for Standardization table columns using placeholders
DECLARE @SourceColumn VARCHAR(100) = '<%=$sourcecolumn%>'  -- Placeholder for Source Column Name
DECLARE @TargetColumn VARCHAR(100) = '<%=$targetcolumn%>'  -- Placeholder for Target Column Name
DECLARE @isKey VARCHAR(1) = '<%=$iskey%>'  -- 'Y' if key Placeholder for Target Column Name
DECLARE @ReplaceNull VARCHAR(MAX) = '<%=$replacenulls%>'  -- Placeholder for Replace Null value
DECLARE @ReplaceValues VARCHAR(MAX) = '<%=$replacevalues%>'  -- Placeholder for Replace Values
DECLARE @CustomCalculation VARCHAR(MAX) = '<%=$customcalculation%>'  -- Placeholder for Custom Calculation
DECLARE @Nullable VARCHAR(20) = '<%=$nullable%>'  -- Placeholder for Nullable
DECLARE @ValidationFormula VARCHAR(MAX) = '<%=$customvalidationformula%>'  -- Placeholder for Validation Formula
DECLARE @ValidationOutput VARCHAR(50) = '<%=$validationoutput%>'  -- Placeholder for Validation Output
Declare @watermarkvalue datetime='1900-01-01'
DECLARE @DataType VARCHAR(50) = '<%=$datatype%>'  -- Placeholder for DataType


-- Check if a row exists in the Standardization table with the given SourceObjectID and SourceColumn
IF EXISTS (SELECT 1 FROM [dbo].[Standardization] 
           WHERE SourceObject = @SourceObject 
             AND SourceName= @SourceName
             AND SourceSchema = @SourceSchema
             AND SourceColumn = @SourceColumn
             )
BEGIN
    -- Update the existing row
    UPDATE [dbo].[Standardization]
    SET 
        TargetColumn = @TargetColumn,
        TARGETSchema = @TargetSchema,
        TARGETObject = @TargetObject,
        ReplaceNull = @ReplaceNull,
        ReplaceValues = @ReplaceValues,
        CustomCalculation = @CustomCalculation,
        isKey = @isKey,
        Nullable = @Nullable,
        ValidationFormula = @ValidationFormula,
        validationOutput = @ValidationOutput
    WHERE    SourceObject = @SourceObject 
             AND SourceName= @SourceName
             AND isnull(SourceSchema, '-1') = isnull(@SourceSchema, '-1')
             AND SourceColumn = @SourceColumn

        -- Update only if any value has changed, handling NULLs with ISNULL
         AND (
            ISNULL(TargetColumn, '-1') <> ISNULL(@TargetColumn, '-1')
         OR ISNULL(TARGETSchema, '-1') <> ISNULL(@TargetSchema, '-1')
            OR ISNULL(TARGETObject, '-1') <> ISNULL(@TargetObject, '-1')
             OR ISNULL(ReplaceNull, '-1') <> ISNULL(@ReplaceNull, '-1')
         OR ISNULL(ReplaceValues, '-1') <> ISNULL(@ReplaceValues, '-1')
         OR ISNULL(CustomCalculation, '-1') <> ISNULL(@CustomCalculation, '-1')
         OR ISNULL(Nullable, '-1') <> ISNULL(@Nullable, '-1')
         OR ISNULL(ValidationFormula, '-1') <> ISNULL(@ValidationFormula, '-1')
         OR ISNULL(validationOutput, '-1') <> ISNULL(@ValidationOutput, '-1'))
END
ELSE
BEGIN
    -- Insert a new row
    INSERT INTO [dbo].[Standardization] 
    (  SourceName, SourceObject,SourceSchema, SourceColumn, TargetColumn, TARGETSchema, TARGETObject, isKey, ReplaceNull, ReplaceValues, CustomCalculation, Nullable, ValidationFormula,  validationOutput, watermarkvalue)
    VALUES 
    (@SourceName, @SourceObject,@SourceSchema, @SourceColumn, @TargetColumn, @TargetSchema, @TargetObject, @isKey,@ReplaceNull,  @ReplaceValues, @CustomCalculation,  @Nullable, @ValidationFormula,@ValidationOutput,@watermarkvalue)
END

