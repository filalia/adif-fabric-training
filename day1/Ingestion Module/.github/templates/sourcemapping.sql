DECLARE @SourceName VARCHAR(100) = '<%=$sourcename%>'
DECLARE @ConnectionID UNIQUEIDENTIFIER = '<%=$connectionid%>'
DECLARE @SourceShortName VARCHAR(50) = '<%=$sourceshortname%>'
DECLARE @ModificationUser VARCHAR(150) = CURRENT_USER

IF EXISTS (SELECT 1 FROM [dbo].[SourceMapping] WHERE SourceName = @SourceName)
BEGIN
    UPDATE [dbo].[SourceMapping]
    SET ConnectionID = @ConnectionID,
        SourceShortName = @SourceShortName
        
    WHERE SourceName = @SourceName
END
ELSE
BEGIN
    INSERT INTO [dbo].[SourceMapping] (SourceName, SourceShortName, ConnectionID)
    VALUES (@SourceName, @SourceShortName, @ConnectionID)
END
