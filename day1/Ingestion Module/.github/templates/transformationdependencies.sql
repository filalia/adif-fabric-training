-- Declare and set the variables in the same statement using placeholder format

DECLARE @SourceDomain VARCHAR(50) = '<%=$sourcedomain%>'  -- Target Domain
DECLARE @SourceObject VARCHAR(50) = '<%=$sourceobject%>'  -- Target Subdomain
DECLARE @SourceSchema VARCHAR(50) = '<%=$sourceschema%>'  -- Target Object
DECLARE @TargetDomain VARCHAR(50) = '<%=$targetdomain%>'  -- Target Domain
DECLARE @TargetObject VARCHAR(50) = '<%=$targetobject%>'  -- Target Subdomain
DECLARE @TargetSchema VARCHAR(50) = '<%=$targetschema%>'  -- Target Object
DECLARE @Stage VARCHAR(50) = '<%=$stage%>'  -- TransformationNotebook to be executed



-- Check if a row exists in the Standardization table with the given SourceObjectID and SourceColumn
IF NOT EXISTS (SELECT 1 FROM [dbo].[TransformationDependencies] 
           WHERE    SourceDomain = @SourceDomain 
             AND SourceObject= @SourceObject
             AND SourceSchema= @SourceSchema
             and TargetDomain= @TargetDomain
             and TargetSchema = @TargetSchema
             and TargetObject = @TargetObject

             )

BEGIN
    -- Insert a new row
    INSERT INTO [dbo].[TransformationDependencies] 
    (  TargetDomain ,TargetSchema , TargetObject , SourceDomain ,SourceSchema , SourceObject , Stage  )
    VALUES 
    ( @TargetDomain ,@TargetSchema , @TargetObject ,   @SourceDomain , @SourceSchema ,  @SourceObject , @Stage 
    )
END

