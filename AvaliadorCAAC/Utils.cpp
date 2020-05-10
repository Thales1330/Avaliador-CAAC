#include "Utils.h"

Utils& Utils::Get() { return s_utilsInstance; }

wxBusyInfoFlags Utils::BusyInfo(wxWindow* parent, wxString msg, wxString wait)
{
    return wxBusyInfoFlags()
        .Parent(parent)
        .Icon(m_ifIcon)
        .Title(wxString::Format("<b>%s</b>", msg))
        .Text(wait)
        .Foreground(*wxWHITE)
        .Background(*wxBLACK)
        .Transparency(4 * wxALPHA_OPAQUE / 5);
}

void Utils::Load() { m_ifIcon.LoadFile("logo128.png", wxBITMAP_TYPE_PNG); }

void Utils::SaveAtDrive(wxWindow* parent, wxString path, wxString fileName, bool showDialog, wxString msg)
{
    wxArrayString foundIDs;
    if(HaveFileInDive(parent, fileName, foundIDs)) {
        if(showDialog) {
            wxMessageDialog msgDialog(parent, wxT("Esse arquivo existe no Drive.\nDeseja sobrescrever?"),
                                      wxT("Atenção!"), wxYES_NO | wxICON_EXCLAMATION);
            switch(msgDialog.ShowModal()) {
                case wxID_YES: {
                    wxBusyInfo busy(BusyInfo(parent, msg));
                    wxExecute(
                        wxString::Format("%s Replace \"%s\" \"%s\" \"%s\"", m_runDriveAPI, foundIDs[0], fileName, path),
                        wxEXEC_SYNC | m_consoleStatus);
                    return;
                } break;
                case wxID_NO: {
                    return;
                } break;
            }
        } else {
            wxBusyInfo busy(BusyInfo(parent, msg));
            wxExecute(wxString::Format("%s Replace \"%s\" \"%s\" \"%s\"", m_runDriveAPI, foundIDs[0], fileName, path),
                      wxEXEC_SYNC | m_consoleStatus);
            return;
        }
    } else {
        wxBusyInfo busy(BusyInfo(parent, msg));
        wxExecute(wxString::Format("%s Save \"%s\" \"%s\"", m_runDriveAPI, fileName, path),
                  wxEXEC_SYNC | m_consoleStatus);
    }
}

bool Utils::HaveFileInDive(wxWindow* parent, wxString fileName, wxArrayString& fileIDs)
{
    wxBusyInfo busy(BusyInfo(parent, wxT("Procurando arquivo no Drive...")));
    wxExecute(wxString::Format("%s FindInfolder \"%s\"", m_runDriveAPI, fileName), wxEXEC_SYNC | m_consoleStatus);

    wxTextFile txtFile;
    if(txtFile.Open("foundIDs.txt")) {
        fileIDs.Add(txtFile.GetFirstLine());
        while(!txtFile.Eof()) { fileIDs.Add(txtFile.GetNextLine()); }

        if(fileIDs[0] == "") {
            txtFile.Clear();
            txtFile.Write();
            return false;

        } else {
            txtFile.Clear();
            txtFile.Write();
            return true;
        }
    }

    return false;
}
