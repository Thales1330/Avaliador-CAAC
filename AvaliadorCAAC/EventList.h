#ifndef EVENTLIST_H
#define EVENTLIST_H

#include <wx/process.h>
#include <wx/textfile.h>
#include <wx/utils.h>
#include <wx/wfstream.h>
#include <wx/msgdlg.h> 

#include "XMLParser.h"

class Utils;

class EventList
{
   public:
    EventList();
    ~EventList() {}
    
    const wxArrayString& GetEventList() const { return m_eventList; }
    bool Load(wxWindow* parent);
    void Save(wxWindow* parent, wxArrayString eventList);

   private:
    bool LoadEventList();

    wxArrayString m_eventList;

    const wxString m_runDriveAPI = "cmd.exe /c py googleDiveAPI.py";
    const int m_consoleStatus = wxEXEC_HIDE_CONSOLE;
};

#endif  // EVENTLIST_H
