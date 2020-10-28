#ifndef MAINFRAME_H
#define MAINFRAME_H
#include <wx/arrstr.h>
#include <wx/busyinfo.h>
#include <wx/datetime.h>
#include <wx/filedlg.h>
#include <wx/generic/aboutdlgg.h>
#include <wx/process.h>
#include <wx/textfile.h>
#include <wx/utils.h>
#include <wx/wfstream.h>
#include <vector>
#include "wxcrafter.h"

#include "NewProcess.h"
#include "XMLParser.h"
#include "EventList.h"

#define MY_APP_VERSION_STRING "0.3.2-beta"

class Utils;
class PdfPage;
class SearchInDrive;
class FormatValues;

class Activity
{
   public:
    Activity() {}
    Activity(int id) { m_id = id; }
    virtual ~Activity() {}

    void SetId(int id) { this->m_id = id; }
    int GetId() const { return m_id; }
    void SetChPresented(double chPresented) { this->m_chPresented = chPresented; }
    void SetChValidated(double chValidated) { this->m_chValidated = chValidated; }
    void SetDate(const wxString& date) { this->m_date = date; }
    void SetEventName(const wxString& eventName) { this->m_eventName = eventName; }
    void SetEventDescription(const wxString& eventDesc) { this->m_eventDesc = eventDesc; }
    void SetIfgEvent(bool ifgEvent) { this->m_ifgEvent = ifgEvent; }
    void SetInstitutionName(const wxString& institutionName) { this->m_institutionName = institutionName; }
    void SetItemCode(int itemCode) { this->m_itemCode = itemCode; }
    void SetShiftNumber(double shiftNumber) { this->m_shiftNumber = shiftNumber; }
    double GetChPresented() const { return m_chPresented; }
    double GetChValidated() const { return m_chValidated; }
    const wxString& GetDate() const { return m_date; }
    const wxString& GetEventName() const { return m_eventName; }
    const wxString& GetEventDescription() const { return m_eventDesc; }
    bool IsIFGEvent() const { return m_ifgEvent; }
    const wxString& GetInstitutionName() const { return m_institutionName; }
    int GetItemCode() const { return m_itemCode; }
    double GetShiftNumber() const { return m_shiftNumber; }
    void SetInvalidateCH(bool invalidateCH) { this->m_invalidateCH = invalidateCH; }
    void SetObs(const wxString& obs) { this->m_obs = obs; }
    bool IsInvalidateCH() const { return m_invalidateCH; }
    const wxString& GetObs() const { return m_obs; }
    void SetIgnoreRestrictions(bool ignoreRestrictions) { this->m_ignoreRestrictions = ignoreRestrictions; }
    void SetShowInReport(bool show) { this->m_show = show; }
    bool IsRestrictionsIgnored() const { return m_ignoreRestrictions; }
    bool IsShownInReport() const { return m_show; }

    void SetLimitedCH(bool limitedCH) { this->m_limitedCH = limitedCH; }
    bool IsLimitedCH() const { return m_limitedCH; }
    

   protected:
    int m_id = 0;
    int m_itemCode = 0;
    wxString m_eventName = wxT("Nome do evento...");
    wxString m_eventDesc = "";
    double m_shiftNumber = 1.0;
    bool m_ifgEvent = true;
    wxString m_institutionName = wxT("Nome da instituição...");
    double m_chPresented = 0.0;
    wxString m_date = wxT("-");
    double m_chValidated = 0.0;
    bool m_invalidateCH = false;
    bool m_show = true;
    bool m_ignoreRestrictions = false;
    wxString m_obs = "";

    bool m_limitedCH = false;
};

class MainFrame : public MainFrameBaseClass
{
   public:
    MainFrame(wxWindow* parent);
    virtual ~MainFrame();

   protected:
    virtual void OnOpenDrive(wxCommandEvent& event);
    virtual void OnPanelKeyDown(wxKeyEvent& event);
    virtual void OnCloseEvent(wxCloseEvent& event);
    virtual void OnAboutClick(wxCommandEvent& event);
    virtual void GenerateReport(wxCommandEvent& event);
    virtual void EditProcess(wxCommandEvent& event);
    virtual void GoDown(wxCommandEvent& event);
    virtual void GoUp(wxCommandEvent& event);
    virtual void OnPGChange(wxPropertyGridEvent& event);
    virtual void AppendItem(wxCommandEvent& event);
    virtual void GridCellSelected(wxGridEvent& event);
    virtual void RemoveItem(wxCommandEvent& event);
    virtual void OnNew(wxCommandEvent& event);
    virtual void OnOpen(wxCommandEvent& event);
    virtual void OnSave(wxCommandEvent& event);
    virtual void OnExit(wxCommandEvent& event);

    virtual void InitFrame();
    virtual void EnableAll(bool enable = true);
    virtual void EnableAllPG(bool enable = true);
    virtual void BuildGrid();
    virtual void ChangePropertyText(wxPGProperty* property, wxString newText);
    virtual void ValidateCH(Activity* activity);
    virtual void ClearAll();

    virtual void DoAppendItem(bool createActivity = true, bool selectRow = true);
    virtual void DoRemoveItem();

    virtual void ValidateAllActivities();
    virtual void UpdateRowCH(Activity* activity);
    virtual void FillPG(int id);
    virtual void UpdateChangedPG();
    virtual void UpdateCH();
    virtual void UpdateRowColour(Activity* activity, int rowNumber);

    virtual void BypassSelectionEvent(bool bypass = true) { m_bypassSelEvent = bypass; }
    virtual bool IsSelectionEventBypassed() { return m_bypassSelEvent; }

    static int CompareForward(int* a, int* b);
    static int CompareBackward(int* a, int* b);

    virtual void FillAllRows();

    virtual bool SaveProcess(wxString path, wxString fileName);
    virtual bool OpenProcess(wxString path);

    virtual bool ShowSaveDialog();
    virtual bool IsSaveNeeded() { return m_saveNeeded; }
    virtual void SaveNeeded(bool saveNeeded = true) { m_saveNeeded = saveNeeded; }
    
    long ConvertPropToItemCode(const long& id, const Resolution& resolution);
    long ConvertItemCodeToProp(const long& id, const Resolution& resolution);

    // Drive mathods
    wxBusyInfoFlags GetBusyInfoFlags(wxWindow* parent, wxString message);
    virtual void SaveAtDrive(wxString path, wxString fileName);
    virtual bool HaveFileInDive(wxString fileName, wxArrayString& fileIDs);

    wxLocale m_locale;

    int m_index = 0;
    double m_chCompActivity = 120.0;
    bool m_bypassSelEvent = false;

    std::vector<Activity*> m_activityList;

    wxString m_protocolNumber = "";
    wxString m_studentName = "";
    long int m_numDocs = 0;
    Resolution m_resolution = N_16;
    double m_totalReqCH = 0.0;
    double m_totalValCH = 0.0;

    bool m_saveNeeded = false;
    
    EventList m_eventList;

    const wxString m_runDriveAPI = "cmd.exe /c py googleDiveAPI.py";
    const int m_consoleStatus = wxEXEC_HIDE_CONSOLE;
    wxIcon m_ifIcon;
    
    wxArrayString m_itensResN16;
    wxArrayString m_itensResN20;
};
#endif  // MAINFRAME_H
