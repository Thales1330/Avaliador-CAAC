#ifndef SEARCHINDRIVE_H
#define SEARCHINDRIVE_H
#include <wx/busyinfo.h>
#include <wx/msgdlg.h>
#include <wx/process.h>
#include <wx/string.h>
#include <wx/textfile.h>
#include "wxcrafter.h"

class FormatValues;

class SearchInDrive : public SearchInDriveBase
{
   public:
    SearchInDrive(wxWindow* parent, wxString* fileID, wxString* fileName);
    virtual ~SearchInDrive();

    virtual void DoSearch();

    virtual void FillProtocolNum(wxString protocolNum) { m_textCtrlProcessNumber->SetValue(protocolNum); }
    virtual void FillStudentName(wxString studentName) { m_textCtrlStudentName->SetValue(studentName); }

   protected:
    virtual void OnCancelButtonClick(wxCommandEvent& event);
    virtual void OnItemSelected(wxListEvent& event);
    virtual void OnOKButtonClick(wxCommandEvent& event);
    virtual void OnSearchButtonClick(wxCommandEvent& event);
    virtual void InitList();

    wxBusyInfoFlags GetBusyInfoFlags(wxWindow* parent, wxString message);

    wxArrayString m_foundIDs;
    wxArrayString m_foundNames;
    wxString* m_fileID = NULL;
    wxString* m_fileName = NULL;

    const wxString m_runDriveAPI = "cmd.exe /c py googleDiveAPI.py";
    const int m_consoleStatus = wxEXEC_HIDE_CONSOLE;
    wxIcon m_ifIcon;
};
#endif  // SEARCHINDRIVE_H
