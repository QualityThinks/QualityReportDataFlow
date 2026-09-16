Option Explicit

Private Const QUALITY_REPORT_SUBJECT_PREFIX As String = _
    "QUALITY REPORT"

Private Const QUALITY_REPORT_OUTPUT_FOLDER As String = _
    "C:\QR\"

Private Const ERROR_INVALID_DATE_RANGE As Long = _
    vbObjectError + 1001

Private Function GetQualityReportStartDate() As Date
    GetQualityReportStartDate = DateSerial(2026, 9, 1)
End Function


Private Function GetQualityReportEndDate() As Date
    GetQualityReportEndDate = Now()
End Function


Public Sub DownloadQualityReportAttachments()

    Const PROCEDURE_NAME As String = _
        "DownloadQualityReportAttachments"

    Dim outlookSession As Outlook.NameSpace
    Dim inboxFolder As Outlook.Folder

    Dim startDate As Date
    Dim endDate As Date

    Dim matchingEmailCount As Long
    Dim examinedAttachmentCount As Long
    Dim savedFileCount As Long
    Dim skippedFileCount As Long
    Dim failedFileCount As Long

    On Error GoTo ErrorHandler

    startDate = GetQualityReportStartDate()
    endDate = GetQualityReportEndDate()

    ValidateInclusiveDateRange _
        startDate:=startDate, _
        endDate:=endDate

    EnsureFolderExists QUALITY_REPORT_OUTPUT_FOLDER

    Set outlookSession = Application.Session
    Set inboxFolder = outlookSession.GetDefaultFolder(olFolderInbox)

    ProcessMailFolder _
        mailFolder:=inboxFolder, _
        startDate:=startDate, _
        endDate:=endDate, _
        matchingEmailCount:=matchingEmailCount, _
        examinedAttachmentCount:=examinedAttachmentCount, _
        savedFileCount:=savedFileCount, _
        skippedFileCount:=skippedFileCount, _
        failedFileCount:=failedFileCount

    MsgBox _
        Prompt:= _
            "Quality report attachment download completed." & _
            vbCrLf & vbCrLf & _
            "Date range: " & _
            Format$(startDate, "yyyy-mm-dd") & _
            " to " & _
            Format$(endDate, "yyyy-mm-dd") & vbCrLf & vbCrLf & _
            "Matching emails: " & _
            matchingEmailCount & vbCrLf & _
            "Attachments examined: " & _
            examinedAttachmentCount & vbCrLf & _
            "Files saved: " & _
            savedFileCount & vbCrLf & _
            "Files skipped: " & _
            skippedFileCount & vbCrLf & _
            "Files failed: " & _
            failedFileCount & vbCrLf & vbCrLf & _
            "Output folder:" & vbCrLf & _
            QUALITY_REPORT_OUTPUT_FOLDER, _
        Buttons:=vbInformation, _
        Title:="Quality Report Download"

CleanExit:
    Set inboxFolder = Nothing
    Set outlookSession = Nothing
    Exit Sub

ErrorHandler:
    MsgBox _
        Prompt:= _
            "The quality report attachment download " & _
            "could not be completed." & _
            vbCrLf & vbCrLf & _
            "Procedure: " & PROCEDURE_NAME & vbCrLf & _
            "Error number: " & Err.Number & vbCrLf & _
            "Description: " & Err.Description, _
        Buttons:=vbCritical, _
        Title:="Quality Report Download Error"
    Resume CleanExit
End Sub


Private Sub ProcessMailFolder( _
    ByVal mailFolder As Outlook.Folder, _
    ByVal startDate As Date, _
    ByVal endDate As Date, _
    ByRef matchingEmailCount As Long, _
    ByRef examinedAttachmentCount As Long, _
    ByRef savedFileCount As Long, _
    ByRef skippedFileCount As Long, _
    ByRef failedFileCount As Long)

    Dim folderItems As Outlook.Items
    Dim currentItem As Object
    Dim childFolder As Outlook.Folder
    Dim itemIndex As Long

    On Error GoTo ErrorHandler

    Set folderItems = mailFolder.Items

    For itemIndex = folderItems.Count To 1 Step -1

        Set currentItem = Nothing

        On Error Resume Next
        Set currentItem = folderItems.Item(itemIndex)
        Err.Clear
        On Error GoTo ErrorHandler

        If Not currentItem Is Nothing Then
            ProcessMailItem _
                outlookItem:=currentItem, _
                startDate:=startDate, _
                endDate:=endDate, _
                matchingEmailCount:=matchingEmailCount, _
                examinedAttachmentCount:= _
                    examinedAttachmentCount, _
                savedFileCount:=savedFileCount, _
                skippedFileCount:=skippedFileCount, _
                failedFileCount:=failedFileCount

        End If

        If itemIndex Mod 50 = 0 Then
            DoEvents
        End If

    Next itemIndex

    For Each childFolder In mailFolder.Folders

        ProcessMailFolder _
            mailFolder:=childFolder, _
            startDate:=startDate, _
            endDate:=endDate, _
            matchingEmailCount:=matchingEmailCount, _
            examinedAttachmentCount:= _
                examinedAttachmentCount, _
            savedFileCount:=savedFileCount, _
            skippedFileCount:=skippedFileCount, _
            failedFileCount:=failedFileCount

    Next childFolder

CleanExit:
    Set childFolder = Nothing
    Set currentItem = Nothing
    Set folderItems = Nothing
    Exit Sub

ErrorHandler:
    Err.Clear
    Resume CleanExit

End Sub


Private Sub ProcessMailItem( _
    ByVal outlookItem As Object, _
    ByVal startDate As Date, _
    ByVal endDate As Date, _
    ByRef matchingEmailCount As Long, _
    ByRef examinedAttachmentCount As Long, _
    ByRef savedFileCount As Long, _
    ByRef skippedFileCount As Long, _
    ByRef failedFileCount As Long)

    Dim mailItem As Outlook.mailItem

    On Error GoTo ErrorHandler

    If outlookItem.Class <> olMail Then
        Exit Sub
    End If

    Set mailItem = outlookItem

    If Not IsReceivedWithinDateRange( _
        receivedTime:=mailItem.receivedTime, _
        startDate:=startDate, _
        endDate:=endDate) Then

        GoTo CleanExit

    End If

    If Not SubjectStartsWithQualityReportPrefix( _
        emailSubject:=mailItem.Subject) Then

        GoTo CleanExit

    End If

    matchingEmailCount = matchingEmailCount + 1

    SaveSupportedAttachments _
        mailItem:=mailItem, _
        examinedAttachmentCount:=examinedAttachmentCount, _
        savedFileCount:=savedFileCount, _
        skippedFileCount:=skippedFileCount, _
        failedFileCount:=failedFileCount

CleanExit:
    Set mailItem = Nothing
    Exit Sub

ErrorHandler:
    Err.Clear
    Resume CleanExit

End Sub


Private Sub SaveSupportedAttachments( _
    ByVal mailItem As Outlook.mailItem, _
    ByRef examinedAttachmentCount As Long, _
    ByRef savedFileCount As Long, _
    ByRef skippedFileCount As Long, _
    ByRef failedFileCount As Long)

    Dim currentAttachment As Outlook.attachment
    Dim attachmentIndex As Long

    Dim senderEmailAddress As String
    Dim destinationFilePath As String

    On Error GoTo ErrorHandler

    senderEmailAddress = _
        GetSenderSmtpAddress(mailItem)

    For attachmentIndex = 1 To mailItem.Attachments.Count

        Set currentAttachment = Nothing
        destinationFilePath = vbNullString

        On Error GoTo AttachmentError

        Set currentAttachment = _
            mailItem.Attachments.Item(attachmentIndex)

        examinedAttachmentCount = _
            examinedAttachmentCount + 1

        If IsSupportedSpreadsheetFile( _
            fileName:=currentAttachment.fileName) Then

            destinationFilePath = _
                CreateUniqueAttachmentPath( _
                    outputFolderPath:= _
                        QUALITY_REPORT_OUTPUT_FOLDER, _
                    receivedTime:=mailItem.receivedTime, _
                    senderEmailAddress:=senderEmailAddress, _
                    originalFileName:= _
                        currentAttachment.fileName)

            currentAttachment.SaveAsFile _
                destinationFilePath

            savedFileCount = savedFileCount + 1

        Else

            skippedFileCount = skippedFileCount + 1

        End If

ContinueNextAttachment:
        On Error GoTo ErrorHandler
        Set currentAttachment = Nothing

    Next attachmentIndex

CleanExit:
    Set currentAttachment = Nothing
    Exit Sub

AttachmentError:
    failedFileCount = failedFileCount + 1

    Err.Clear
    Resume ContinueNextAttachment

ErrorHandler:
    Err.Clear
    Resume CleanExit

End Sub


Private Function IsReceivedWithinDateRange( _
    ByVal receivedTime As Date, _
    ByVal startDate As Date, _
    ByVal endDate As Date) As Boolean

    Dim receivedDate As Date

    receivedDate = DateValue(receivedTime)

    IsReceivedWithinDateRange = _
        receivedDate >= DateValue(startDate) And _
        receivedDate <= DateValue(endDate)

End Function


Private Function SubjectStartsWithQualityReportPrefix( _
    ByVal emailSubject As String) As Boolean

    Dim normalizedSubject As String

    normalizedSubject = Trim$(emailSubject)

    If Len(normalizedSubject) < _
       Len(QUALITY_REPORT_SUBJECT_PREFIX) Then

        Exit Function

    End If

    SubjectStartsWithQualityReportPrefix = _
        StrComp( _
            Left$( _
                normalizedSubject, _
                Len(QUALITY_REPORT_SUBJECT_PREFIX)), _
            QUALITY_REPORT_SUBJECT_PREFIX, _
            vbTextCompare) = 0

End Function


Private Function IsSupportedSpreadsheetFile( _
    ByVal fileName As String) As Boolean

    Dim extensionPosition As Long
    Dim fileExtension As String

    extensionPosition = InStrRev(fileName, ".")

    If extensionPosition = 0 Then
        Exit Function
    End If

    fileExtension = _
        LCase$(Mid$(fileName, extensionPosition))

    Select Case fileExtension

        Case ".xls", _
             ".xlsx", _
             ".xlsm", _
             ".xlsb", _
             ".xlt", _
             ".xltx", _
             ".xltm", _
             ".csv"

            IsSupportedSpreadsheetFile = True

    End Select

End Function


Private Function CreateUniqueAttachmentPath( _
    ByVal outputFolderPath As String, _
    ByVal receivedTime As Date, _
    ByVal senderEmailAddress As String, _
    ByVal originalFileName As String) As String

    Dim normalizedFolderPath As String
    Dim safeSenderAddress As String
    Dim safeOriginalFileName As String

    Dim baseFileName As String
    Dim fileExtension As String
    Dim candidateFilePath As String

    Dim extensionPosition As Long
    Dim duplicateSequence As Long

    normalizedFolderPath = _
        AddTrailingBackslash(outputFolderPath)

    safeSenderAddress = _
        SanitizeFileName(senderEmailAddress)

    safeOriginalFileName = _
        SanitizeFileName(originalFileName)

    extensionPosition = _
        InStrRev(safeOriginalFileName, ".")

    If extensionPosition > 0 Then

        baseFileName = _
            Left$( _
                safeOriginalFileName, _
                extensionPosition - 1)

        fileExtension = _
            Mid$( _
                safeOriginalFileName, _
                extensionPosition)

    Else

        baseFileName = safeOriginalFileName
        fileExtension = vbNullString

    End If

    baseFileName = _
        Format$(receivedTime, "yyyymmdd_hhnnss") & _
        "_" & _
        safeSenderAddress & _
        "_" & _
        baseFileName

    candidateFilePath = _
        normalizedFolderPath & _
        baseFileName & _
        fileExtension

    duplicateSequence = 1

    Do While FileExists(candidateFilePath)

        candidateFilePath = _
            normalizedFolderPath & _
            baseFileName & _
            "_" & _
            Format$(duplicateSequence, "000") & _
            fileExtension

        duplicateSequence = duplicateSequence + 1

    Loop

    CreateUniqueAttachmentPath = candidateFilePath

End Function


Private Function GetSenderSmtpAddress( _
    ByVal mailItem As Outlook.mailItem) As String

    Dim exchangeUser As Outlook.exchangeUser
    Dim senderAddress As String

    On Error GoTo UseFallbackAddress

    If StrComp( _
        mailItem.SenderEmailType, _
        "EX", _
        vbTextCompare) = 0 Then

        If Not mailItem.Sender Is Nothing Then

            Set exchangeUser = _
                mailItem.Sender.GetExchangeUser

            If Not exchangeUser Is Nothing Then

                senderAddress = _
                    exchangeUser.PrimarySmtpAddress

            End If

        End If

    Else

        senderAddress = _
            mailItem.senderEmailAddress

    End If

FinalizeAddress:

    If Len(Trim$(senderAddress)) = 0 Then

        On Error Resume Next

        senderAddress = _
            mailItem.senderEmailAddress

        On Error GoTo 0

    End If

    If Len(Trim$(senderAddress)) = 0 Then
        senderAddress = "unknown_sender"
    End If

    GetSenderSmtpAddress = senderAddress

CleanExit:
    Set exchangeUser = Nothing
    Exit Function

UseFallbackAddress:
    Err.Clear

    On Error Resume Next
    senderAddress = mailItem.senderEmailAddress
    On Error GoTo 0

    GoTo FinalizeAddress

End Function


Private Function SanitizeFileName( _
    ByVal value As String) As String

    Dim invalidCharacters As Variant
    Dim currentCharacter As Variant

    value = Trim$(value)

    invalidCharacters = Array( _
        "\", _
        "/", _
        ":", _
        "*", _
        "?", _
        """", _
        "<", _
        ">", _
        "|")

    For Each currentCharacter In invalidCharacters

        value = Replace$( _
            Expression:=value, _
            Find:=CStr(currentCharacter), _
            Replace:="_")

    Next currentCharacter

    Do While InStr( _
        1, _
        value, _
        "__", _
        vbBinaryCompare) > 0

        value = Replace$( _
            Expression:=value, _
            Find:="__", _
            Replace:="_")

    Loop

    Do While Len(value) > 0 And _
             (Right$(value, 1) = "." Or _
              Right$(value, 1) = " ")

        value = Left$(value, Len(value) - 1)

    Loop

    If Len(value) = 0 Then
        value = "unknown"
    End If

    SanitizeFileName = value

End Function


Private Sub EnsureFolderExists( _
    ByVal folderPath As String)

    Const PROCEDURE_NAME As String = _
        "EnsureFolderExists"

    Dim fileSystem As Object
    Dim normalizedFolderPath As String

    On Error GoTo ErrorHandler

    normalizedFolderPath = _
        RemoveTrailingBackslash(folderPath)

    Set fileSystem = _
        CreateObject("Scripting.FileSystemObject")

    If Not fileSystem.FolderExists( _
        normalizedFolderPath) Then

        CreateFolderHierarchy _
            fileSystem:=fileSystem, _
            folderPath:=normalizedFolderPath

    End If

CleanExit:
    Set fileSystem = Nothing
    Exit Sub

ErrorHandler:
    Err.Raise _
        Number:=Err.Number, _
        Source:=PROCEDURE_NAME, _
        Description:= _
            "Could not create or access folder """ & _
            normalizedFolderPath & _
            """. " & _
            Err.Description

End Sub


Private Sub CreateFolderHierarchy( _
    ByVal fileSystem As Object, _
    ByVal folderPath As String)

    Dim parentFolderPath As String

    If fileSystem.FolderExists(folderPath) Then
        Exit Sub
    End If

    parentFolderPath = _
        fileSystem.GetParentFolderName(folderPath)

    If Len(parentFolderPath) > 0 Then

        If Not fileSystem.FolderExists( _
            parentFolderPath) Then

            CreateFolderHierarchy _
                fileSystem:=fileSystem, _
                folderPath:=parentFolderPath

        End If

    End If

    fileSystem.CreateFolder folderPath

End Sub


Private Function FileExists( _
    ByVal filePath As String) As Boolean

    FileExists = _
        Len(Dir$( _
            PathName:=filePath, _
            Attributes:= _
                vbNormal Or _
                vbHidden Or _
                vbSystem Or _
                vbReadOnly)) > 0

End Function


Private Function AddTrailingBackslash( _
    ByVal folderPath As String) As String

    folderPath = _
        Replace$(folderPath, "/", "\")

    If Right$(folderPath, 1) <> "\" Then
        folderPath = folderPath & "\"
    End If

    AddTrailingBackslash = folderPath

End Function


Private Function RemoveTrailingBackslash( _
    ByVal folderPath As String) As String

    folderPath = _
        Replace$(folderPath, "/", "\")

    Do While Len(folderPath) > 3 And _
             Right$(folderPath, 1) = "\"

        folderPath = _
            Left$(folderPath, Len(folderPath) - 1)

    Loop

    RemoveTrailingBackslash = folderPath

End Function


Private Sub ValidateInclusiveDateRange( _
    ByVal startDate As Date, _
    ByVal endDate As Date)

    If DateValue(startDate) > DateValue(endDate) Then

        Err.Raise _
            Number:=ERROR_INVALID_DATE_RANGE, _
            Source:="ValidateInclusiveDateRange", _
            Description:= _
                "The start date must be earlier than " & _
                "or equal to the end date."

    End If

End Sub