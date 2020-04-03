#ifndef NEWPROCESS_H
#define NEWPROCESS_H
#include "wxcrafter.h"

enum Resolution { N_16 = 0, N_20 };

class NewProcess : public NewProcessBase
{
   public:
    NewProcess(wxWindow* parent);
    NewProcess(wxWindow* parent, wxString* protocolNumber, wxString* studentName, long int* numDocs, Resolution* resolution, bool enableNumDocs = true);
    virtual ~NewProcess();
    
    void FillFields();

   protected:
    virtual void OnCancelClick(wxCommandEvent& event) { EndModal(wxID_CANCEL); };
    virtual void OnOKClick(wxCommandEvent& event);
    bool ValidateData();
    
    wxString* m_protocolNumber = NULL;
    wxString* m_studentName = NULL;
    long int* m_numDocs = NULL;
    Resolution* m_resolution = NULL;
};
#endif  // NEWPROCESS_H
