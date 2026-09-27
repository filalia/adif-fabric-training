
/*******************************************************************************/
/*               Scripting of source objects                                   */
/*               Source Name : <%=$sourcename%>                                */
/*               Object Name : <%=$sourceobject%>                               */
/*******************************************************************************/
/*******************************************************************************/


-- Variables for SourceName and BatchGroupName
DECLARE @SourceName VARCHAR(100) = '<%=$sourcename%>'
DECLARE @BatchGroupName VARCHAR(150) = '<%=$batchgroupname%>'
DECLARE @BatchOrderID VARCHAR(150) = <%=$batchorderid%>
Declare @LoadMode varchar(50) ='<%=$loadmode%>' 
DECLARE @SourceObject varchar(50) = '<%=$sourceobject%>'
DECLARE @SourceSchema varchar(50) = '<%=$sourceschema%>'
DECLARE @InstanceName varchar(50) = '<%=$instancename%>'
DECLARE @RelativeURL varchar(100) = '<%=$relativeurl%>'
Declare @WatermarkColumn varchar(50) ='<%=$watermarkcolumn%>'
Declare @WaterMarkValue varchar(50) ='<%=$watermarkvalue%>' 

IF NOT EXISTS (SELECT 1 FROM [dbo].[SourceObject] 
               WHERE SourceName = @SourceName 
                 AND SourceObject = @SourceObject 
                 AND SourceSchema = @SourceSchema)
BEGIN
    INSERT INTO [dbo].[SourceObject] (SourceName, SourceObject, SourceSchema, RelativeURL, LoadMode, WatermarkColumn, WatermarkValue, BatchGroupName, BatchOrderID, ModificationDate, ModificationUser)
    VALUES (@SourceName, @SourceObject, @SourceSchema, @RelativeURL, @LoadMode, @WatermarkColumn, @WaterMarkValue, @BatchGroupName, @BatchOrderID, CURRENT_TIMESTAMP, CURRENT_USER)
END
ELSE
BEGIN
    UPDATE [dbo].[SourceObject]
    SET RelativeURL = @RelativeURL,
        BatchOrderID = @BatchOrderID,
        BatchGroupName = @BatchGroupName,
        LoadMode = @LoadMode,
        WatermarkColumn = @WatermarkColumn,
        ModificationDate = CURRENT_TIMESTAMP,
        ModificationUser = CURRENT_USER
    WHERE SourceName = @SourceName 
      AND SourceObject = @SourceObject 
      AND SourceSchema = @SourceSchema
      AND (ISNULL(RelativeURL, '-1') <> ISNULL(@RelativeURL, '-1') OR
           ISNULL(BatchOrderID, '-1') <> ISNULL(@BatchOrderID, '-1') OR
           ISNULL(BatchGroupName, '-1') <> ISNULL(@BatchGroupName, '-1') OR
           LoadMode <> @LoadMode OR
           ISNULL(WatermarkColumn, '-1') <> ISNULL(@WatermarkColumn, '-1'))
END

