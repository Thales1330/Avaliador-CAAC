#ifndef UTILS_H
#define UTILS_H

#include <wx/utils.h>
#include <wx/busyinfo.h>
#include <wx/msgdlg.h> 
#include <wx/textfile.h>

class Utils
{
public:
    Utils(const Utils&) = delete;
    static Utils& Get();
    
    wxBusyInfoFlags BusyInfo(wxWindow* parent, wxString msg, wxString wait = wxT("Aguarde um momento..."));
    void SaveAtDrive(wxWindow* parent, wxString path, wxString fileName, bool showDialog = true, wxString msg = "");
    bool HaveFileInDive(wxWindow* parent, wxString fileName, wxArrayString& fileIDs);
    void Load();
private:
    Utils() {}
    
    static Utils s_utilsInstance;
    
    wxIcon m_ifIcon;
    const wxString m_runDriveAPI = "cmd.exe /c py googleDiveAPI.py";
    const int m_consoleStatus = wxEXEC_HIDE_CONSOLE;
};

#endif // UTILS_H
