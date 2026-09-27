
/*******************************************************************************/
/*               Scripting of source ingestion                                 */
/*               Source Name : <%=$sourcename%>                                */
/*               SourceTyope : <%=$sourcetype%>   NEw comment                  */
/*******************************************************************************/


DECLARE @SourceName VARCHAR(100) = '<%=$sourcename%>'
DECLARE @SourceType VARCHAR(100) = '<%=$sourcetype%>'
DECLARE @InstanceURL VARCHAR(225) = '<%=$instanceurl%>'
DECLARE @AuthentificationMode VARCHAR(100) = '<%=$authentificationmode%>'
DECLARE @UserName VARCHAR(150) = '<%=$username%>'
DECLARE @SecretName VARCHAR(150) = '<%=$secretname%>'
DECLARE @InstanceName VARCHAR(150) = '<%=$instancename%>'
DECLARE @ModificationUser VARCHAR(150) = CURRENT_USER

IF EXISTS (SELECT 1 FROM [dbo].[Source] WHERE SourceName = @SourceName)
BEGIN
    UPDATE [dbo].[Source]
    SET SourceType = @SourceType,
        InstanceURL = @InstanceURL,
        InstanceName= @InstanceName,
        AuthentificationMode = @AuthentificationMode,
        UserName = @UserName,
        SecretName=@SecretName,
        ModificationDate = CURRENT_TIMESTAMP,
        ModificationUser = @ModificationUser
    WHERE SourceName = @SourceName
END
ELSE
BEGIN
    INSERT INTO [dbo].[Source] (SourceName, SourceType, InstanceURL, InstanceName, AuthentificationMode, UserName,SecretName, ModificationDate, ModificationUser )
    VALUES (@SourceName, @SourceType, @InstanceURL,@InstanceName, @AuthentificationMode, @UserName,@SecretName, CURRENT_TIMESTAMP, @ModificationUser)
END
