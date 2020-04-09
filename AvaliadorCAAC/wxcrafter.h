//////////////////////////////////////////////////////////////////////
// This file was auto-generated by codelite's wxCrafter Plugin
// wxCrafter project file: wxcrafter.wxcp
// Do not modify this file by hand!
//////////////////////////////////////////////////////////////////////

#ifndef _AVALIADOR_CAAC_AVALIADORCAAC_WXCRAFTER_BASE_CLASSES_H
#define _AVALIADOR_CAAC_AVALIADORCAAC_WXCRAFTER_BASE_CLASSES_H

// clang-format off
#include <wx/settings.h>
#include <wx/xrc/xmlres.h>
#include <wx/xrc/xh_bmp.h>
#include <wx/frame.h>
#include <wx/iconbndl.h>
#include <wx/artprov.h>
#include <wx/sizer.h>
#include <wx/menu.h>
#include <wx/panel.h>
#include <wx/stattext.h>
#include <wx/statbmp.h>
#include <wx/propgrid/manager.h>
#include <wx/propgrid/property.h>
#include <wx/propgrid/advprops.h>
#include <wx/button.h>
#include <wx/bmpbuttn.h>
#include <wx/grid.h>
#include <wx/dialog.h>
#include <wx/textctrl.h>
#include <wx/choice.h>
#include <wx/arrstr.h>
#include <wx/listctrl.h>
#if wxVERSION_NUMBER >= 2900
#include <wx/persist.h>
#include <wx/persist/toplevel.h>
#include <wx/persist/bookctrl.h>
#include <wx/persist/treebook.h>
#endif

#ifdef WXC_FROM_DIP
#undef WXC_FROM_DIP
#endif
#if wxVERSION_NUMBER >= 3100
#define WXC_FROM_DIP(x) wxWindow::FromDIP(x, NULL)
#else
#define WXC_FROM_DIP(x) x
#endif

// clang-format on

class MainFrameBaseClass : public wxFrame
{
   protected:
    wxMenuBar* m_menuBar;
    wxMenu* m_menuFile;
    wxMenuItem* m_menuItemNew;
    wxMenuItem* m_menuItemSave;
    wxMenuItem* m_menuItemOpen;
    wxMenuItem* m_menuItemOpenDrive;
    wxMenuItem* m_menuItemExit;
    wxMenu* m_menuReport;
    wxMenuItem* m_menuItemEditProcess;
    wxMenuItem* m_menuItemGenerateReport;
    wxMenu* m_menuHelp;
    wxMenuItem* m_menuItemAbout;
    wxPanel* m_mainPanel;
    wxStaticText* m_staticTextProcessNumber;
    wxStaticText* m_staticTextStudentName;
    wxStaticBitmap* m_staticBitmap137;
    wxPropertyGridManager* m_pgMgr;
    wxPGProperty* m_pgPropItem;
    wxPGProperty* m_pgPropEvent;
    wxPGProperty* m_pgPropShiftN;
    wxPGProperty* m_pgPropIFGEvent;
    wxPGProperty* m_pgPropInstitution;
    wxPGProperty* m_pgPropDate;
    wxPGProperty* m_pgPropCH;
    wxPGProperty* m_pgPropInvalidate;
    wxPGProperty* m_pgPropShowInReport;
    wxPGProperty* m_pgPropIgnoreRestrictions;
    wxPGProperty* m_pgPropObs;
    wxButton* m_buttonAppendItem;
    wxButton* m_buttonRemoveItem;
    wxBitmapButton* m_bmpButtonUp;
    wxBitmapButton* m_bmpButtonDown;
    wxGrid* m_grid;
    wxStaticText* m_staticTextTotalRequested;
    wxStaticText* m_staticTextTotalValidated;
    wxStaticText* m_staticTextSubLimited;
    wxStaticText* m_staticTextSubIgnored;
    wxStaticText* m_staticTextSubInvalidated;
    wxStaticText* m_staticTextSubNoReport;

   protected:
    virtual void OnCloseEvent(wxCloseEvent& event) { event.Skip(); }
    virtual void OnNew(wxCommandEvent& event) { event.Skip(); }
    virtual void OnSave(wxCommandEvent& event) { event.Skip(); }
    virtual void OnOpen(wxCommandEvent& event) { event.Skip(); }
    virtual void OnOpenDrive(wxCommandEvent& event) { event.Skip(); }
    virtual void OnExit(wxCommandEvent& event) { event.Skip(); }
    virtual void EditProcess(wxCommandEvent& event) { event.Skip(); }
    virtual void GenerateReport(wxCommandEvent& event) { event.Skip(); }
    virtual void OnAboutClick(wxCommandEvent& event) { event.Skip(); }
    virtual void OnPanelKeyDown(wxKeyEvent& event) { event.Skip(); }
    virtual void OnPGChange(wxPropertyGridEvent& event) { event.Skip(); }
    virtual void AppendItem(wxCommandEvent& event) { event.Skip(); }
    virtual void RemoveItem(wxCommandEvent& event) { event.Skip(); }
    virtual void GoUp(wxCommandEvent& event) { event.Skip(); }
    virtual void GoDown(wxCommandEvent& event) { event.Skip(); }
    virtual void GridCellSelected(wxGridEvent& event) { event.Skip(); }

   public:
    wxMenuBar* GetMenuBar() { return m_menuBar; }
    wxStaticText* GetStaticTextProcessNumber() { return m_staticTextProcessNumber; }
    wxStaticText* GetStaticTextStudentName() { return m_staticTextStudentName; }
    wxStaticBitmap* GetStaticBitmap137() { return m_staticBitmap137; }
    wxPropertyGridManager* GetPgMgr() { return m_pgMgr; }
    wxButton* GetButtonAppendItem() { return m_buttonAppendItem; }
    wxButton* GetButtonRemoveItem() { return m_buttonRemoveItem; }
    wxBitmapButton* GetBmpButtonUp() { return m_bmpButtonUp; }
    wxBitmapButton* GetBmpButtonDown() { return m_bmpButtonDown; }
    wxGrid* GetGrid() { return m_grid; }
    wxStaticText* GetStaticTextTotalRequested() { return m_staticTextTotalRequested; }
    wxStaticText* GetStaticTextTotalValidated() { return m_staticTextTotalValidated; }
    wxStaticText* GetStaticTextSubLimited() { return m_staticTextSubLimited; }
    wxStaticText* GetStaticTextSubIgnored() { return m_staticTextSubIgnored; }
    wxStaticText* GetStaticTextSubInvalidated() { return m_staticTextSubInvalidated; }
    wxStaticText* GetStaticTextSubNoReport() { return m_staticTextSubNoReport; }
    wxPanel* GetMainPanel() { return m_mainPanel; }
    MainFrameBaseClass(wxWindow* parent,
                       wxWindowID id = wxID_ANY,
                       const wxString& title = wxT("Avaliador CAAC"),
                       const wxPoint& pos = wxDefaultPosition,
                       const wxSize& size = wxSize(500, 300),
                       long style = wxCAPTION | wxRESIZE_BORDER | wxMAXIMIZE_BOX | wxMINIMIZE_BOX | wxSYSTEM_MENU |
                                    wxCLOSE_BOX);
    virtual ~MainFrameBaseClass();
};

class NewProcessBase : public wxDialog
{
   protected:
    wxStaticText* m_staticTextProcess;
    wxTextCtrl* m_textCtrlProcessNumber;
    wxStaticText* m_staticTextStudentName;
    wxTextCtrl* m_textCtrlStudentName;
    wxStaticText* m_staticTextNumDoc;
    wxTextCtrl* m_textCtrlNumDoc;
    wxStaticText* m_staticTexRes;
    wxChoice* m_choiceResolution;
    wxButton* m_buttonOK;
    wxButton* m_buttonCancel;

   protected:
    virtual void OnOKClick(wxCommandEvent& event) { event.Skip(); }
    virtual void OnCancelClick(wxCommandEvent& event) { event.Skip(); }

   public:
    wxStaticText* GetStaticTextProcess() { return m_staticTextProcess; }
    wxTextCtrl* GetTextCtrlProcessNumber() { return m_textCtrlProcessNumber; }
    wxStaticText* GetStaticTextStudentName() { return m_staticTextStudentName; }
    wxTextCtrl* GetTextCtrlStudentName() { return m_textCtrlStudentName; }
    wxStaticText* GetStaticTextNumDoc() { return m_staticTextNumDoc; }
    wxTextCtrl* GetTextCtrlNumDoc() { return m_textCtrlNumDoc; }
    wxStaticText* GetStaticTexRes() { return m_staticTexRes; }
    wxChoice* GetChoiceResolution() { return m_choiceResolution; }
    wxButton* GetButtonOK() { return m_buttonOK; }
    wxButton* GetButtonCancel() { return m_buttonCancel; }
    NewProcessBase(wxWindow* parent,
                   wxWindowID id = wxID_ANY,
                   const wxString& title = wxT("Novo Processo"),
                   const wxPoint& pos = wxDefaultPosition,
                   const wxSize& size = wxSize(500, 300),
                   long style = wxDEFAULT_DIALOG_STYLE);
    virtual ~NewProcessBase();
};

class SearchInDriveBase : public wxDialog
{
   protected:
    wxStaticText* m_staticTextProcess;
    wxTextCtrl* m_textCtrlProcessNumber;
    wxStaticText* m_staticTextStudentName;
    wxTextCtrl* m_textCtrlStudentName;
    wxStaticText* m_staticTextObs;
    wxButton* m_buttonRunSearch;
    wxListCtrl* m_listCtrlProcess;
    wxButton* m_buttonOK;
    wxButton* m_buttonCancel;

   protected:
    virtual void OnSearchButtonClick(wxCommandEvent& event) { event.Skip(); }
    virtual void OnItemSelected(wxListEvent& event) { event.Skip(); }
    virtual void OnOKButtonClick(wxCommandEvent& event) { event.Skip(); }
    virtual void OnCancelButtonClick(wxCommandEvent& event) { event.Skip(); }

   public:
    wxStaticText* GetStaticTextProcess() { return m_staticTextProcess; }
    wxTextCtrl* GetTextCtrlProcessNumber() { return m_textCtrlProcessNumber; }
    wxStaticText* GetStaticTextStudentName() { return m_staticTextStudentName; }
    wxTextCtrl* GetTextCtrlStudentName() { return m_textCtrlStudentName; }
    wxStaticText* GetStaticTextObs() { return m_staticTextObs; }
    wxButton* GetButtonRunSearch() { return m_buttonRunSearch; }
    wxListCtrl* GetListCtrlProcess() { return m_listCtrlProcess; }
    wxButton* GetButtonOK() { return m_buttonOK; }
    wxButton* GetButtonCancel() { return m_buttonCancel; }
    SearchInDriveBase(wxWindow* parent,
                      wxWindowID id = wxID_ANY,
                      const wxString& title = wxT("Buscar no Drive"),
                      const wxPoint& pos = wxDefaultPosition,
                      const wxSize& size = wxSize(500, 300),
                      long style = wxDEFAULT_DIALOG_STYLE);
    virtual ~SearchInDriveBase();
};

#endif
