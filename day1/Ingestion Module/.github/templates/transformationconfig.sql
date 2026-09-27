-- Declare and set the variables in the same statement using placeholder format

DECLARE @TargetDomain VARCHAR(50) = TRIM('<%=$targetdomain%>')  -- Target Domain
DECLARE @TargetSchema VARCHAR(50) = '<%=$targetschema%>'  -- Target Subdomain
DECLARE @TargetObject VARCHAR(50) = '<%=$targetobject%>'  -- Target Object
DECLARE @NotebookPath VARCHAR(50) = '<%=$notebookpath%>'  -- TransformationNotebook to be executed
DECLARE @BatchGroupName VARCHAR(150) = '<%=$batchgroupname%>'
DECLARE @BatchOrderID INT = <%=$batchorderid%>  -- Placeholder for Key Columns


-- Check if a row exists in the Standardization table with the given SourceObjectID and SourceColumn
IF EXISTS (SELECT 1 FROM [dbo].[TransformationConfig] 
           WHERE TargetDomain = @TargetDomain
             AND   TargetSchema = @TargetSchema 
             AND TargetObject= @TargetObject
             
             )
BEGIN
    -- Update the existing row
    UPDATE [dbo].[TransformationConfig]
    SET 
        NotebookPath = @NotebookPath
        , BatchOrderID= @BatchOrderID
        , BatchGroupName= @BatchGroupName
    WHERE    TargetDomain = @TargetDomain
             AND   TargetSchema = @TargetSchema 
             AND TargetObject= @TargetObject
    -- Update only if any value has changed, handling NULLs with ISNULL
         AND ( ISNULL(NotebookPath, '-1') <> ISNULL(@NotebookPath, '-1'))
END
ELSE
BEGIN
    -- Insert a new row
    INSERT INTO [dbo].[TransformationConfig] 
    (    TargetDomain , TargetSchema , TargetObject , NotebookPath , BatchGroupName , BatchOrderID)
    VALUES 
    (  @TargetDomain , @TargetSchema , @TargetObject ,  @NotebookPath ,  @BatchGroupName , @BatchOrderID )
END

