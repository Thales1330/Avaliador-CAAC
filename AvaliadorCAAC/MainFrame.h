#ifndef MAINFRAME_H
#define MAINFRAME_H
#include <vector>
#include <wx/wfstream.h>
#include <wx/datetime.h>
#include <wx/filedlg.h>
#include <wx/utils.h>
#include <wx/generic/aboutdlgg.h>
#include "wxcrafter.h"

#include "NewProcess.h"
#include "XMLParser.h"

#define MY_APP_VERSION_STRING "0.1-beta"

class PdfPage;

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
    void SetIfgEvent(bool ifgEvent) { this->m_ifgEvent = ifgEvent; }
    void SetInstitutionName(const wxString& institutionName) { this->m_institutionName = institutionName; }
    void SetItemCode(int itemCode) { this->m_itemCode = itemCode; }
    void SetShiftNumber(double shiftNumber) { this->m_shiftNumber = shiftNumber; }
    double GetChPresented() const { return m_chPresented; }
    double GetChValidated() const { return m_chValidated; }
    const wxString& GetDate() const { return m_date; }
    const wxString& GetEventName() const { return m_eventName; }
    bool IsIFGEvent() const { return m_ifgEvent; }
    const wxString& GetInstitutionName() const { return m_institutionName; }
    int GetItemCode() const { return m_itemCode; }
    double GetShiftNumber() const { return m_shiftNumber; }
    void SetInvalidateCH(bool invalidateCH) { this->m_invalidateCH = invalidateCH; }
    void SetObs(const wxString& obs) { this->m_obs = obs; }
    bool IsInvalidateCH() const { return m_invalidateCH; }
    const wxString& GetObs() const { return m_obs; }

    void SetLimitedCH(bool limitedCH) { this->m_limitedCH = limitedCH; }
    bool IsLimitedCH() const { return m_limitedCH; }

   protected:
    int m_id = 0;
    int m_itemCode = 0;
    wxString m_eventName = wxT("Nome do evento...");
    double m_shiftNumber = 1.0;
    bool m_ifgEvent = true;
    wxString m_institutionName = wxT("Nome da instituição...");
    double m_chPresented = 0.0;
    wxString m_date = wxT("-");
    double m_chValidated = 0.0;
    bool m_invalidateCH = false;
    wxString m_obs = "";

    bool m_limitedCH = false;
};

class MainFrame : public MainFrameBaseClass
{
   public:
    MainFrame(wxWindow* parent);
    virtual ~MainFrame();

   protected:
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

    virtual void BypassSelectionEvent(bool bypass = true) { m_bypassSelEvent = bypass; }
    virtual bool IsSelectionEventBypassed() { return m_bypassSelEvent; }

    static int CompareForward(int* a, int* b);
    static int CompareBackward(int* a, int* b);
    
    virtual void FillAllRows();
    
    virtual bool OpenProcess(wxString path);

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
};
#endif  // MAINFRAME_H
