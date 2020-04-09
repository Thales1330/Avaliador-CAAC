#include "FormatValues.h"
#include "SearchInDrive.h"

SearchInDrive::SearchInDrive(wxWindow* parent, wxString* fileID, wxString* fileName) : SearchInDriveBase(parent)
{
    SetSize(GetBestSize());
    m_fileID = fileID;
    m_fileName = fileName;
    m_ifIcon.LoadFile("logo128.png", wxBITMAP_TYPE_PNG);
    InitList();
}

SearchInDrive::~SearchInDrive() {}

void SearchInDrive::OnCancelButtonClick(wxCommandEvent& event) { EndModal(wxID_CANCEL); }
void SearchInDrive::OnItemSelected(wxListEvent& event) {}
void SearchInDrive::OnOKButtonClick(wxCommandEvent& event)
{
    long item = -1;
    item = m_listCtrlProcess->GetNextItem(item, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

    if(item == -1) {
        wxMessageDialog dialog(this, wxT("Nenhum processo selecionado."), wxT("Erro"), wxICON_ERROR);
        dialog.ShowModal();
        return;
    }
    if((static_cast<long>(m_foundIDs.GetCount()) - 1) < item) {
        wxMessageDialog dialog(this, wxT("Não foi possível abrir o arquivo."), wxT("Erro"), wxICON_ERROR);
        dialog.ShowModal();
        return;
    }

    *m_fileID = m_foundIDs[item];
    *m_fileName = m_foundNames[item];
    EndModal(wxID_OK);
}
void SearchInDrive::OnSearchButtonClick(wxCommandEvent& event)
{
    DoSearch();
    event.Skip();
}

void SearchInDrive::InitList()
{
    m_listCtrlProcess->ClearAll();
    m_listCtrlProcess->AppendColumn(wxT("Protocolo"), wxLIST_FORMAT_LEFT, 150);
    m_listCtrlProcess->AppendColumn(wxT("Nome"), wxLIST_FORMAT_LEFT, 240);
}

wxBusyInfoFlags SearchInDrive::GetBusyInfoFlags(wxWindow* parent, wxString message)
{
    return wxBusyInfoFlags()
        .Parent(parent)
        .Icon(m_ifIcon)
        .Title(wxString::Format("<b>%s</b>", message))
        .Text(wxT("Aguarde um momento..."))
        .Foreground(*wxWHITE)
        .Background(*wxBLACK)
        .Transparency(4 * wxALPHA_OPAQUE / 5);
}

void SearchInDrive::DoSearch()
{
    
    wxString protocolNum = m_textCtrlProcessNumber->GetValue();
    wxString studentName = m_textCtrlStudentName->GetValue();

    FormatValues fValues(protocolNum, studentName);

    wxBusyInfo busy(GetBusyInfoFlags(this, wxT("Buscando arquivos no Drive...")));
    wxExecute(
        wxString::Format("%s FindInFolder2 \"%s\" \"%s\"", m_runDriveAPI, fValues.GetProtocol(), fValues.GetName()),
        wxEXEC_SYNC | m_consoleStatus);

    wxTextFile txtFileNames;
    wxTextFile txtFileIDs;
    m_foundNames.Clear();
    if(txtFileNames.Open("foundNames.txt")) {
        m_foundNames.Add(txtFileNames.GetFirstLine());
        while(!txtFileNames.Eof()) { m_foundNames.Add(txtFileNames.GetNextLine()); }
        txtFileNames.Clear();
        txtFileNames.Write();
    }
    m_foundIDs.Clear();
    if(txtFileIDs.Open("foundIDs.txt")) {
        m_foundIDs.Add(txtFileIDs.GetFirstLine());
        while(!txtFileIDs.Eof()) { m_foundIDs.Add(txtFileIDs.GetNextLine()); }
        txtFileIDs.Clear();
        txtFileIDs.Write();
    }

    InitList();
    for(unsigned int i = 0; i < m_foundNames.GetCount(); ++i) {
        wxString studentName;
        wxString protocolNumber;
        if(fValues.Deformat(m_foundNames[i], protocolNumber, studentName)) {
            m_listCtrlProcess->InsertItem(i, protocolNumber);
            m_listCtrlProcess->SetItem(i, 1, studentName);
        }
    }
}
