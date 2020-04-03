#include <wx/msgdlg.h>
#include "NewProcess.h"

NewProcess::NewProcess(wxWindow* parent) : NewProcessBase(parent) {}

NewProcess::~NewProcess() {}

void NewProcess::OnOKClick(wxCommandEvent& event)
{
    if(ValidateData()) {
        EndModal(wxID_OK);
    } else {
        wxMessageDialog dialog(this, wxT("Dados incorretos!"), wxT("Erro"), wxICON_ERROR);
        dialog.ShowModal();
    }
}

NewProcess::NewProcess(wxWindow* parent,
                       wxString* protocolNumber,
                       wxString* studentName,
                       long int* numDocs,
                       Resolution* resolution,
                       bool enableNumDocs)
    : NewProcessBase(parent)
{
    m_protocolNumber = protocolNumber;
    m_studentName = studentName;
    m_numDocs = numDocs;
    m_resolution = resolution;
    m_textCtrlNumDoc->Enable(enableNumDocs);
    m_staticTextNumDoc->Enable(enableNumDocs);
}

bool NewProcess::ValidateData()
{
    wxString protocolNumber = m_textCtrlProcessNumber->GetValue();
    wxString studentName = m_textCtrlStudentName->GetValue();
    if(!m_textCtrlNumDoc->GetValue().ToLong(m_numDocs)) return false;
    *m_resolution = static_cast<Resolution>(m_choiceResolution->GetSelection());
    
    *m_protocolNumber = protocolNumber;
    *m_studentName = studentName;
    return true;
}

void NewProcess::FillFields()
{
    m_textCtrlProcessNumber->SetValue(*m_protocolNumber);
    m_textCtrlStudentName->SetValue(*m_studentName);
    m_textCtrlNumDoc->SetValue(wxString::Format("%d", *m_numDocs));
    m_choiceResolution->Select(static_cast<int>(*m_resolution));
}
