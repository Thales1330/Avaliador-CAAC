#include <wx/aboutdlg.h>
#include <wx/msgdlg.h>
#include "MainFrame.h"
#include "PdfPage.h"

MainFrame::MainFrame(wxWindow* parent) : MainFrameBaseClass(parent) { InitFrame(); }

MainFrame::~MainFrame() {}

void MainFrame::InitFrame()
{
    m_locale.Init();

    EnableAll(false);
    BuildGrid();
    m_pgPropIFGEvent->SetAttribute(wxPG_BOOL_USE_CHECKBOX, true);
    m_pgPropInvalidate->SetAttribute(wxPG_BOOL_USE_CHECKBOX, true);
}

void MainFrame::OnExit(wxCommandEvent& event)
{
    wxUnusedVar(event);
    Close();
}

void MainFrame::OnNew(wxCommandEvent& event)
{
    NewProcess process(this, &m_protocolNumber, &m_studentName, &m_numDocs, &m_resolution);
    if(process.ShowModal() == wxID_OK) {
        ClearAll();
        EnableAll();
        m_staticTextProcessNumber->SetLabel(wxT("Processo: ") + m_protocolNumber);
        m_staticTextStudentName->SetLabel(wxT("Aluno: ") + m_studentName);
    }
    for(int i = 0; i < m_numDocs; ++i) DoAppendItem();
}

void MainFrame::OnOpen(wxCommandEvent& event)
{
    wxFileDialog openFileDialog(this, _("Abrir arquivo XML"), "", "", "Arquivos XML (*.xml)|*.xml",
                                wxFD_OPEN | wxFD_FILE_MUST_EXIST);
    if(openFileDialog.ShowModal() == wxID_CANCEL) return;  // the user changed idea...

    if(!OpenProcess(openFileDialog.GetPath())) {
        wxMessageDialog dialog(this, wxT("Não é possível abrir o arquivo."), wxT("Erro"), wxICON_ERROR);
        dialog.ShowModal();
        return;
    }
}

bool MainFrame::OpenProcess(wxString path)
{
    ClearAll();
    EnableAll(true);

    rapidxml::xml_document<> doc;
    rapidxml::file<> xmlFile(path.mb_str());

    doc.parse<0>(xmlFile.data());

    auto rootNode = doc.first_node("Processo");
    if(!rootNode) return false;
    auto numProtocolNode = rootNode->first_node("NumProtocolo");
    if(!numProtocolNode) return false;
    m_protocolNumber = wxString::FromUTF8(numProtocolNode->value());
    auto studentNameNode = rootNode->first_node("NomeEstudante");
    if(!studentNameNode) return false;
    m_studentName = wxString::FromUTF8(studentNameNode->value());
    m_resolution = static_cast<Resolution>(XMLParser::GetNodeValueInt(rootNode, "NumResolucao"));

    auto activitiesNode = rootNode->first_node("Atividades");
    if(!activitiesNode) return false;
    auto activityNode = activitiesNode->first_node("Atividade");
    while(activityNode) {
        // ID
        int id = XMLParser::GetAttributeValueInt(activityNode, "ID");
        // New activity
        Activity* activity = new Activity(id);
        // Item
        activity->SetItemCode(XMLParser::GetNodeValueInt(activityNode, "Item"));
        // Evento
        auto eventName = activityNode->first_node("Evento");
        if(!eventName) return false;
        activity->SetEventName(wxString::FromUTF8(eventName->value()));
        // Num shifts
        activity->SetShiftNumber(XMLParser::GetNodeValueDouble(activityNode, "NumTurnos"));
        // Evento IFG
        activity->SetIfgEvent(static_cast<bool>(XMLParser::GetNodeValueInt(activityNode, "EventoIFG")));
        // Instituicao
        auto institutionNode = activityNode->first_node("Instituicao");
        if(!institutionNode) return false;
        activity->SetInstitutionName(wxString::FromUTF8(institutionNode->value()));
        // Data
        auto dateNode = activityNode->first_node("Data");
        if(!dateNode) return false;
        activity->SetDate(wxString::FromUTF8(dateNode->value()));
        // Num shifts
        activity->SetChPresented(XMLParser::GetNodeValueDouble(activityNode, "CH"));
        // Atividade valida
        activity->SetInvalidateCH(static_cast<bool>(XMLParser::GetNodeValueInt(activityNode, "AtividadeValida")));
        // Obs
        auto obsNode = activityNode->first_node("Observacoes");
        if(!obsNode) return false;
        activity->SetObs(wxString::FromUTF8(obsNode->value()));

        m_activityList.push_back(activity);

        // Append new row
        BypassSelectionEvent();
        DoAppendItem(false, false);
        // Set new row ID
        m_grid->SetCellValue(m_grid->GetNumberRows() - 1, 0, wxString::Format("%d", id));

        activityNode = activityNode->next_sibling("Atividade");
    }

    FillAllRows();
    ValidateAllActivities();
    BypassSelectionEvent(false);
    UpdateCH();

    m_staticTextProcessNumber->SetLabel(wxT("Processo: ") + m_protocolNumber);
    m_staticTextStudentName->SetLabel(wxT("Aluno: ") + m_studentName);

    return true;
}

void MainFrame::OnSave(wxCommandEvent& event)
{
    wxFileDialog saveFileDialog(this, wxT("Salvar arquivo XML"), "", "", "Arquivo XML (*.xml)|*.xml",
                                wxFD_SAVE | wxFD_OVERWRITE_PROMPT);
    if(saveFileDialog.ShowModal() == wxID_CANCEL) return;

    // Erase the file (if exists or not) and write the initial data
    std::ofstream writeProjectsFile(saveFileDialog.GetPath().mb_str());
    writeProjectsFile.close();

    rapidxml::xml_document<> doc;
    rapidxml::file<> xmlFile(saveFileDialog.GetPath());
    doc.parse<0>(xmlFile.data());

    rapidxml::xml_node<>* decl = doc.allocate_node(rapidxml::node_declaration);
    rapidxml::xml_attribute<>* ver = doc.allocate_attribute("version", "1.0");
    rapidxml::xml_attribute<>* encoding = doc.allocate_attribute("encoding", "utf-8");
    decl->append_attribute(ver);
    decl->append_attribute(encoding);
    doc.append_node(decl);

    rapidxml::xml_node<>* rootNode = doc.allocate_node(rapidxml::node_element, "Processo");
    doc.append_node(rootNode);

    rapidxml::xml_node<>* processNameNode = XMLParser::AppendNode(doc, rootNode, "Nome");
    XMLParser::SetNodeValue(doc, processNameNode, saveFileDialog.GetFilename());

    rapidxml::xml_node<>* processNumber = XMLParser::AppendNode(doc, rootNode, "NumProtocolo");
    XMLParser::SetNodeValue(doc, processNumber, m_protocolNumber);

    rapidxml::xml_node<>* studentName = XMLParser::AppendNode(doc, rootNode, "NomeEstudante");
    XMLParser::SetNodeValue(doc, studentName, m_studentName);

    rapidxml::xml_node<>* resNumber = XMLParser::AppendNode(doc, rootNode, "NumResolucao");
    XMLParser::SetNodeValue(doc, resNumber, static_cast<int>(m_resolution));

    rapidxml::xml_node<>* activitiesNode = XMLParser::AppendNode(doc, rootNode, "Atividades");

    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        // ID
        rapidxml::xml_node<>* activityNode = XMLParser::AppendNode(doc, activitiesNode, "Atividade");
        XMLParser::SetNodeAttribute(doc, activityNode, "ID", activity->GetId());
        // Item
        rapidxml::xml_node<>* itemCode = XMLParser::AppendNode(doc, activityNode, "Item");
        XMLParser::SetNodeValue(doc, itemCode, activity->GetItemCode());
        // Evento
        rapidxml::xml_node<>* eventName = XMLParser::AppendNode(doc, activityNode, "Evento");
        XMLParser::SetNodeValue(doc, eventName, activity->GetEventName());
        // Turnos/apresentação/participação
        rapidxml::xml_node<>* numShift = XMLParser::AppendNode(doc, activityNode, "NumTurnos");
        XMLParser::SetNodeValue(doc, numShift, activity->GetShiftNumber());
        // Evento IFG
        rapidxml::xml_node<>* ifgEvent = XMLParser::AppendNode(doc, activityNode, "EventoIFG");
        XMLParser::SetNodeValue(doc, ifgEvent, static_cast<int>(activity->IsIFGEvent()));
        // Instituicao
        rapidxml::xml_node<>* institutionNode = XMLParser::AppendNode(doc, activityNode, "Instituicao");
        XMLParser::SetNodeValue(doc, institutionNode, activity->GetInstitutionName());
        // Data
        rapidxml::xml_node<>* dateNode = XMLParser::AppendNode(doc, activityNode, "Data");
        XMLParser::SetNodeValue(doc, dateNode, activity->GetDate());
        // CH apresentada
        rapidxml::xml_node<>* ch = XMLParser::AppendNode(doc, activityNode, "CH");
        XMLParser::SetNodeValue(doc, ch, activity->GetChPresented());
        // Atividade valida
        rapidxml::xml_node<>* validAct = XMLParser::AppendNode(doc, activityNode, "AtividadeValida");
        XMLParser::SetNodeValue(doc, validAct, static_cast<int>(activity->IsInvalidateCH()));
        // Obs
        rapidxml::xml_node<>* obs = XMLParser::AppendNode(doc, activityNode, "Observacoes");
        XMLParser::SetNodeValue(doc, obs, activity->GetObs());
    }

    std::ofstream writeXML(saveFileDialog.GetPath().mb_str());
    writeXML << doc;
    writeXML.close();
}

void MainFrame::EnableAll(bool enable)
{
    m_pgMgr->Enable(enable);
    m_pgPropItem->Enable(enable);
    m_pgPropEvent->Enable(enable);
    m_pgPropShiftN->Enable(enable);
    m_pgPropIFGEvent->Enable(enable);
    m_pgPropInstitution->Enable(enable);
    m_pgPropDate->Enable(enable);
    m_pgPropCH->Enable(enable);
    m_pgPropInvalidate->Enable(enable);
    m_pgPropObs->Enable(enable);

    m_buttonAppendItem->Enable(enable);
    m_buttonRemoveItem->Enable(enable);
    m_bmpButtonUp->Enable(enable);
    m_bmpButtonDown->Enable(enable);
}

void MainFrame::BuildGrid()
{
    m_grid->SetSelectionMode(wxGrid::wxGridSelectRows);
    m_grid->SetDefaultCellAlignment(wxALIGN_CENTRE, wxALIGN_CENTRE);

    //->HideRowLabels();
    m_grid->SetRowLabelSize(wxGRID_AUTOSIZE);
    m_grid->SetLabelFont(m_grid->GetLabelFont().Bold());
    m_grid->AppendCols(9, false);
    m_grid->SetColMinimalAcceptableWidth(100);
    m_grid->SetColLabelValue(0, wxT("ID"));
    // m_grid->SetColSize(0, 10);
    m_grid->HideCol(0);
    m_grid->SetColLabelValue(1, wxT("Item"));
    m_grid->SetColSize(1, 100);
    m_grid->SetColLabelValue(2, wxT("Evento"));
    m_grid->SetColSize(2, 200);
    m_grid->SetColLabelValue(3, wxT("TAP"));
    m_grid->SetColSize(3, 100);
    m_grid->SetColLabelValue(4, wxT("Evento IFG"));
    m_grid->SetColSize(4, 100);
    m_grid->SetColLabelValue(5, wxT("Instituição"));
    m_grid->SetColSize(5, 200);
    m_grid->SetColLabelValue(6, wxT("CH Apresentada"));
    m_grid->SetColSize(6, 100);
    m_grid->SetColLabelValue(7, wxT("Data Evento"));
    m_grid->SetColSize(7, 200);
    m_grid->SetColLabelValue(8, wxT("CH Validada"));
    m_grid->SetColSize(8, 100);
    m_grid->AutoSizeColumns();
    // m_grid->ForceRefresh();
}

void MainFrame::GridCellSelected(wxGridEvent& event)
{
    if(!IsSelectionEventBypassed()) {
        long int id = -1;
        if(m_grid->GetCellValue(event.GetRow(), 0).ToLong(&id)) FillPG(id);
    }
    BypassSelectionEvent(false);

    event.Skip();
}

void MainFrame::AppendItem(wxCommandEvent& event)
{
    DoAppendItem();

    event.Skip();
}

void MainFrame::RemoveItem(wxCommandEvent& event)
{
    DoRemoveItem();

    event.Skip();
}

void MainFrame::OnPGChange(wxPropertyGridEvent& event) { UpdateChangedPG(); }

void MainFrame::ChangePropertyText(wxPGProperty* property, wxString newText)
{
    wxPGCell cell = property->GetCell(0);
    cell.SetText(newText);
    property->SetCell(0, cell);
}

void MainFrame::EnableAllPG(bool enable)
{
    m_pgPropShiftN->Enable(enable);
    m_pgPropIFGEvent->Enable(enable);
    m_pgPropCH->Enable(enable);
}

void MainFrame::ValidateCH(Activity* activity)
{
    if(activity->IsInvalidateCH()) {
        activity->SetChValidated(0.0);
        activity->SetLimitedCH(true);
        return;
    }

    double chLanguage = 0.0;
    double chCourses = 0.0;
    double chComWork = 0.0;
    double chTCC = 0.0;
    double chEventNonIFG = 0.0;

    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        activity->SetLimitedCH(false);
        switch(activity->GetItemCode()) {
            case 1:
            case 2:
            case 5: {
                activity->SetChValidated(activity->GetShiftNumber() * 4.0);
                activity->SetChPresented(activity->GetShiftNumber() * 4.0);
            } break;
            case 3:
            case 4: {
                double ch = activity->GetChPresented();
                if(!activity->IsIFGEvent()) {
                    ch *= 0.8;
                    double oldCHEventNonIFG = chEventNonIFG;
                    chEventNonIFG += ch;
                    if(chEventNonIFG > m_chCompActivity * 0.5) {
                        double partialCH = m_chCompActivity * 0.5 - oldCHEventNonIFG;
                        if(partialCH > 0) {
                            activity->SetChValidated(partialCH);
                            activity->SetLimitedCH(true);
                        } else {
                            activity->SetChValidated(0.0);
                            activity->SetLimitedCH(true);
                        }
                    } else {
                        activity->SetChValidated(ch);
                    }
                } else
                    activity->SetChValidated(ch);
            } break;
            case 6:
            case 11:
            case 16: {
                double ch = activity->GetChPresented();
                double oldCH = 0.0;
                double accCH = 0.0;
                if(activity->GetItemCode() == 6) {
                    oldCH = chLanguage;
                    chLanguage += ch;
                    accCH = chLanguage;
                } else if(activity->GetItemCode() == 11) {
                    oldCH = chCourses;
                    chCourses += ch;
                    accCH = chCourses;
                } else if(activity->GetItemCode() == 16) {
                    oldCH = chComWork;
                    chComWork += ch;
                    accCH = chComWork;
                }
                if(accCH > m_chCompActivity * 0.4) {
                    double partialCH = m_chCompActivity * 0.4 - oldCH;
                    if(partialCH > 0) {
                        activity->SetChValidated(partialCH);
                        activity->SetLimitedCH(true);
                    } else {
                        activity->SetChValidated(0.0);
                        activity->SetLimitedCH(true);
                    }
                } else
                    activity->SetChValidated(ch);
            } break;
            case 7:
            case 8:
            case 9:
            case 10:
            case 12: {
                activity->SetChValidated(60.0);
                activity->SetChPresented(60.0);
            } break;
            case 13:
            case 14:
            case 15: {
                activity->SetChValidated(30.0);
                activity->SetChPresented(30.0);
            } break;
            case 17: {
                double ch = activity->GetShiftNumber() * 2.0;
                activity->SetChPresented(ch);
                double oldCHTCC = chTCC;
                chTCC += ch;
                if(chTCC > m_chCompActivity * 0.2) {
                    double partialCH = m_chCompActivity * 0.2 - oldCHTCC;
                    if(partialCH > 0) {
                        activity->SetChValidated(partialCH);
                        activity->SetLimitedCH(true);
                    } else {
                        activity->SetChValidated(0.0);
                        activity->SetLimitedCH(true);
                    }
                } else {
                    activity->SetChValidated(ch);
                }

            } break;
            default:
                break;
        }
    }
}

void MainFrame::ValidateAllActivities()
{
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        if(activity->GetItemCode() != 0) {
            ValidateCH(activity);
            UpdateRowCH(activity);
        }
    }
}

void MainFrame::UpdateRowCH(Activity* activity)
{
    int rowNumber = -1;
    for(int i = 0; i < m_grid->GetNumberRows(); ++i) {
        long int id = -1;
        if(m_grid->GetCellValue(i, 0).ToLong(&id)) {
            if(id == activity->GetId()) { rowNumber = i; }
        }
    }
    if(rowNumber == -1) return;

    m_grid->SetCellValue(rowNumber, 8, wxString::Format("%f", activity->GetChValidated()));

    wxColour rowColour = *wxBLACK;
    if(activity->IsLimitedCH()) { rowColour = *wxRED; }
    for(int j = 0; j < 9; ++j) m_grid->SetCellTextColour(rowNumber, j, rowColour);
}

void MainFrame::FillPG(int id)
{
    // Find activity
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        if(activity->GetId() == id) {
            m_pgPropItem->SetValueFromInt(activity->GetItemCode());
            m_pgPropEvent->SetValueFromString(activity->GetEventName());
            m_pgPropShiftN->SetValueFromInt(activity->GetShiftNumber());
            m_pgPropIFGEvent->SetValueFromInt(activity->IsIFGEvent());
            m_pgPropInstitution->SetValueFromString(activity->GetInstitutionName());
            m_pgPropDate->SetValueFromString(activity->GetDate());
            m_pgPropCH->SetValueFromString(wxString::Format("%f", activity->GetChPresented()));
            m_pgPropInvalidate->SetValueFromInt(activity->IsInvalidateCH());
            m_pgPropObs->SetValueFromString(activity->GetObs());
        }
    }

    UpdateChangedPG();
}

void MainFrame::UpdateChangedPG()
{
    EnableAllPG(false);
    bool shiftN = false;
    bool ifgEvent = false;
    bool ch = false;

    switch(m_pgPropItem->GetValue().GetInteger()) {
        case 0: {
            return;
        } break;
        case 1:
        case 2: {
            ChangePropertyText(m_pgPropShiftN, wxT("Num. Turnos"));
            m_pgPropShiftN->Enable(true);
            shiftN = true;
        } break;
        case 3:
        case 4: {
            ChangePropertyText(m_pgPropShiftN, wxT("Num. Participações"));
            m_pgPropShiftN->Enable(true);
            m_pgPropIFGEvent->Enable(true);
            m_pgPropCH->Enable(true);
            shiftN = true;
            ifgEvent = true;
            ch = true;
        } break;
        case 5: {
            ChangePropertyText(m_pgPropShiftN, wxT("Num. Apresentações"));
            m_pgPropShiftN->Enable(true);
            shiftN = true;
        } break;
        case 6:
        case 11:
        case 16: {
            m_pgPropCH->Enable(true);
            ch = true;
        } break;
        case 7:
        case 8:
        case 9:
        case 10:
        case 12: {
            // nothing really matters...
        } break;
        case 13:
        case 14:
        case 15: {
            // to me...
        } break;
        case 17: {
            ChangePropertyText(m_pgPropShiftN, wxT("Num. Participações"));
            m_pgPropShiftN->Enable(true);
            shiftN = true;
        } break;
        default:
            break;
    }

    m_pgMgr->Refresh();

    if(!m_grid->GetSelectedRows().IsEmpty() && m_pgPropItem->GetValue().GetInteger() != 0) {
        // Get current activity from list
        int rowNumber = m_grid->GetSelectedRows()[0];
        Activity* currentActivity = NULL;
        for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
            Activity* activity = *it;
            long int id = -1;
            if(!m_grid->GetCellValue(rowNumber, 0).ToLong(&id)) break;
            if(activity->GetId() == id) { currentActivity = activity; }
        }

        // Fill the current activity with new informations
        currentActivity->SetItemCode(m_pgPropItem->GetValue().GetInteger());
        currentActivity->SetEventName(m_pgPropEvent->GetValue().GetString());
        currentActivity->SetShiftNumber(m_pgPropShiftN->GetValue().GetDouble());
        currentActivity->SetIfgEvent(m_pgPropIFGEvent->GetValue().GetBool());
        currentActivity->SetInstitutionName(m_pgPropInstitution->GetValue().GetString());
        currentActivity->SetChPresented(m_pgPropCH->GetValue().GetDouble());
        currentActivity->SetDate(m_pgPropDate->GetValue().GetString());
        currentActivity->SetInvalidateCH(m_pgPropInvalidate->GetValue().GetBool());
        currentActivity->SetObs(m_pgPropObs->GetValue().GetString());

        ValidateCH(currentActivity);

        if(currentActivity) {
            m_grid->SetCellValue(rowNumber, 1, m_pgPropItem->GetDisplayedString());

            m_grid->SetCellValue(rowNumber, 2, currentActivity->GetEventName());

            wxString shiftNStr = "-";
            if(shiftN) shiftNStr = wxString::Format("%d", static_cast<int>(currentActivity->GetShiftNumber()));
            m_grid->SetCellValue(rowNumber, 3, shiftNStr);

            wxString ifgEventStr = "-";
            if(ifgEvent) ifgEventStr = currentActivity->IsIFGEvent() ? wxT("Sim") : wxT("Não");
            m_grid->SetCellValue(rowNumber, 4, ifgEventStr);

            m_grid->SetCellValue(rowNumber, 5, currentActivity->GetInstitutionName());

            wxString chPresentedStr = "-";
            if(ch) chPresentedStr = wxString::Format("%f", currentActivity->GetChPresented());
            m_grid->SetCellValue(rowNumber, 6, chPresentedStr);

            m_grid->SetCellValue(rowNumber, 7, currentActivity->GetDate());

            m_grid->SetCellValue(rowNumber, 8, wxString::Format("%f", currentActivity->GetChValidated()));

            wxColour rowColour = *wxBLACK;
            if(currentActivity->IsLimitedCH()) { rowColour = *wxRED; }
            for(int i = 0; i < 9; ++i) m_grid->SetCellTextColour(rowNumber, i, rowColour);
        }
    }

    UpdateCH();
}
void MainFrame::GoUp(wxCommandEvent& event)
{
    if(!m_grid->GetSelectedRows().IsEmpty()) {
        wxArrayInt rowArr = m_grid->GetSelectedRows();
        rowArr.Sort(CompareBackward);
        for(int i = rowArr.Count() - 1; i >= 0; --i) {
            int rowNumber = rowArr[i];
            if(rowNumber != 0) {
                for(int j = 0; j < m_grid->GetNumberCols(); ++j) {
                    auto tmpValue = m_grid->GetCellValue(rowNumber, j);
                    m_grid->SetCellValue(rowNumber, j, m_grid->GetCellValue(rowNumber - 1, j));
                    m_grid->SetCellValue(rowNumber - 1, j, tmpValue);
                }
                // Swap activity at the list
                auto tmpActvity = m_activityList[rowNumber];
                m_activityList[rowNumber] = m_activityList[rowNumber - 1];
                m_activityList[rowNumber - 1] = tmpActvity;

                BypassSelectionEvent();
                m_grid->SelectRow(rowNumber - 1, true);
                m_grid->DeselectRow(rowNumber);
            }
        }
    }
}
void MainFrame::GoDown(wxCommandEvent& event)
{
    if(!m_grid->GetSelectedRows().IsEmpty()) {
        wxArrayInt rowArr = m_grid->GetSelectedRows();
        rowArr.Sort(CompareForward);
        for(int i = rowArr.Count() - 1; i >= 0; --i) {
            int rowNumber = rowArr[i];
            if(rowNumber != m_grid->GetNumberRows() - 1) {
                for(int j = 0; j < m_grid->GetNumberCols(); ++j) {
                    auto tmpValue = m_grid->GetCellValue(rowNumber, j);
                    m_grid->SetCellValue(rowNumber, j, m_grid->GetCellValue(rowNumber + 1, j));
                    m_grid->SetCellValue(rowNumber + 1, j, tmpValue);
                }
                // Swap activity at the list
                auto tmpActvity = m_activityList[rowNumber];
                m_activityList[rowNumber] = m_activityList[rowNumber + 1];
                m_activityList[rowNumber + 1] = tmpActvity;

                BypassSelectionEvent();
                m_grid->SelectRow(rowNumber + 1, true);
                m_grid->DeselectRow(rowNumber);
            }
        }
    }
}

int MainFrame::CompareForward(int* a, int* b)
{
    if(*a > *b)
        return 1;
    else if(*a < *b)
        return -1;
    else
        return 0;
}

int MainFrame::CompareBackward(int* a, int* b)
{
    if(*a > *b)
        return -1;
    else if(*a < *b)
        return 1;
    else
        return 0;
}

void MainFrame::EditProcess(wxCommandEvent& event)
{
    m_numDocs = m_grid->GetNumberRows();
    NewProcess process(this, &m_protocolNumber, &m_studentName, &m_numDocs, &m_resolution, false);
    process.FillFields();
    if(process.ShowModal() == wxID_OK) {
        EnableAll();
        m_staticTextProcessNumber->SetLabel(wxT("Processo: ") + m_protocolNumber);
        m_staticTextStudentName->SetLabel(wxT("Aluno: ") + m_studentName);
    }
}

void MainFrame::ClearAll()
{
    EnableAll(false);
    m_grid->DeleteRows(0, m_grid->GetNumberRows());
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        if(*it) delete *it;
    }
    m_activityList.clear();
    m_index = 0;
}

void MainFrame::DoAppendItem(bool createActivity, bool selectRow)
{
    m_grid->AppendRows(1, true);
    m_grid->SetCellValue(m_grid->GetNumberRows() - 1, 0, wxString::Format("%d", m_index));
    m_grid->SetCellAlignment(m_grid->GetNumberRows() - 1, 1, wxALIGN_LEFT, wxALIGN_LEFT);  // Item
    m_grid->SetCellAlignment(m_grid->GetNumberRows() - 1, 2, wxALIGN_LEFT, wxALIGN_LEFT);  // Evento
    m_grid->SetCellAlignment(m_grid->GetNumberRows() - 1, 5, wxALIGN_LEFT, wxALIGN_LEFT);  // Instituição

    if(createActivity) {
        Activity* newActivity = new Activity(m_index);
        m_activityList.emplace_back(newActivity);
    }
    if(selectRow)
        m_grid->SelectRow(m_grid->GetNumberRows() - 1);
    else
        BypassSelectionEvent();
    m_index++;
    m_grid->SetRowLabelSize(wxGRID_AUTOSIZE);
}

void MainFrame::DoRemoveItem()
{
    if(!m_grid->GetSelectedRows().IsEmpty()) {
        wxArrayInt selArr = m_grid->GetSelectedRows();
        selArr.Sort(CompareForward);
        for(int i = selArr.Count() - 1; i >= 0; --i) {
            long int id = -1;
            m_grid->GetCellValue(selArr[i], 0).ToLong(&id);
            // Remove activity from list
            for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
                Activity* activity = *it;
                if(activity->GetId() == id) {
                    m_activityList.erase(it);
                    break;
                }
            }
            BypassSelectionEvent();
            m_grid->DeleteRows(selArr[i], 1);
        }
    }
    ValidateAllActivities();
}

void MainFrame::UpdateCH()
{
    double chRequested = 0.0;
    double chValidated = 0.0;
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        chRequested += activity->GetChPresented();
        chValidated += activity->GetChValidated();
    }

    m_totalReqCH = chRequested;
    m_totalValCH = chValidated;

    m_staticTextTotalRequested->SetLabel(wxString::Format(wxT("Total solicitado = %.2f h"), chRequested));
    m_staticTextTotalValidated->SetLabel(wxString::Format(wxT("Total validado = %.2f h"), chValidated));
}

void MainFrame::GenerateReport(wxCommandEvent& event)
{
    PdfPage pdf;
    pdf.AliasNbPages();
    pdf.AddPage();

    // Logo
    pdf.Image(wxS("logoIFG.png"), 10, 13, 55);
    pdf.SetFont(wxS("Arial"), wxS("B"), 9);
    // Move to the right
    pdf.Cell(65);
    // Title
    pdf.Cell(0, 10, wxS("MINISTÉRIO DA EDUCAÇÃO"), wxPDF_BORDER_NONE, 0, wxPDF_ALIGN_LEFT);
    // Line break
    pdf.Ln(4);
    pdf.Cell(65);
    pdf.Cell(0, 10, wxS("SECRETARIA DE EDUCAÇÃO PROFISSIONAL E TECNOLÓGICA"), wxPDF_BORDER_NONE, 0, wxPDF_ALIGN_LEFT);
    pdf.Ln(4);
    pdf.Cell(65);
    pdf.Cell(0, 10, wxS("INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DE GOIÁS"), wxPDF_BORDER_NONE, 0,
             wxPDF_ALIGN_LEFT);
    pdf.Ln(4);
    pdf.Cell(65);
    pdf.Cell(0, 10, wxS("Campus Itumbiara"), wxPDF_BORDER_NONE, 0, wxPDF_ALIGN_LEFT);
    pdf.Ln(10);

    pdf.Ln(6);
    pdf.SetFont(wxS("Arial"), wxS("B"), 12);
    pdf.Cell(0, 10, wxString::Format(wxS("PROCESSO: N° %s"), m_protocolNumber), 0, 1);
    pdf.SetFont(wxS("Arial"), wxS("B"), 11);
    pdf.Cell(0, 10, wxString::Format(wxS("ASSUNTO: AVALIAÇÃO DE ATIVIDADES COMPLEMENTARES"), m_protocolNumber), 0, 1);
    pdf.Ln(1);
    pdf.Cell(0, 6.6);
    pdf.Ln(6);

    pdf.SetFont(wxS("Times"), wxS(""), 11);

    wxFileInputStream f(wxS("head.txt"));
    int len = f.GetLength();
    char* ctxt = new char[len + 1];
    f.Read(ctxt, len);
    ctxt[len] = '\0';
    wxString txt(ctxt, *wxConvCurrent);
    txt.Replace("\\resNumDate", m_resolution == N_16 ? wxT("16 de 26/12/2011") : wxT("20 de 26/12/2011"));
    txt.Replace("\\hours", wxString::FromDouble(m_totalValCH));
    txt.Replace("\\studentName", m_studentName);
    // Output justified text
    // pdf.Ln(8);
    pdf.WriteXml(txt);
    pdf.Ln(1);
    pdf.SetFont(wxS("Times"), wxS(""), 12);
    pdf.Cell(0, 0, wxS("A seguir a relação dos certificados recebidos e avaliados:"), wxPDF_BORDER_NONE, 0,
             wxPDF_ALIGN_CENTER);
    pdf.Ln(6);

    wxFileInputStream fTH(wxS("tableHead.txt"));
    len = fTH.GetLength();
    ctxt = new char[len + 1];
    fTH.Read(ctxt, len);
    ctxt[len] = '\0';
    wxString fTHtxt(ctxt, *wxConvCurrent);

    wxFileInputStream fTB(wxS("tableBody.txt"));
    len = fTB.GetLength();
    ctxt = new char[len + 1];
    fTB.Read(ctxt, len);
    ctxt[len] = '\0';
    wxString fTBtxt(ctxt, *wxConvCurrent);

    wxFileInputStream fTF(wxS("tableFoot.txt"));
    len = fTF.GetLength();
    ctxt = new char[len + 1];
    fTF.Read(ctxt, len);
    ctxt[len] = '\0';
    wxString fTFtxt(ctxt, *wxConvCurrent);

    wxString table = fTHtxt;
    int numObs = 3;
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        wxString activityStr = fTBtxt;
        activityStr.Replace("\\event", activity->GetEventName());
        activityStr.Replace("\\institution", activity->GetInstitutionName());
        activityStr.Replace("\\date", activity->GetDate());
        activityStr.Replace("\\requiredCH", wxString::FromDouble(activity->GetChPresented()));
        wxString validatedCHStr = wxString::FromDouble(activity->GetChValidated());
        if(activity->GetObs() != "") {
            validatedCHStr += wxString::Format(wxS("<sup>%d</sup>"), numObs);
            numObs++;
        }
        activityStr.Replace("\\validatedCH", validatedCHStr);
        table += activityStr;
    }

    fTFtxt.Replace("\\totalReqCH", wxString::FromDouble(m_totalReqCH));
    fTFtxt.Replace("\\totalValCH", wxString::FromDouble(m_totalValCH));

    table += fTFtxt;

    pdf.SetFont(wxS("Times"), wxS(""), 10);
    pdf.WriteXml(table);

    pdf.Ln(6);
    pdf.SetFont(wxS("Times"), wxS(""), 12);
    pdf.Cell(0, 0, wxT("Observações:"));

    pdf.Ln();
    wxString olStr = "<ol type=\"1\">";
    olStr += wxT("<li>Os certificados analisados estão apresentados na tabela acima de acordo com a ordem de "
                 "apresentação no processo.</li>");
    olStr += wxString::Format(wxT("<li>A carga horária validada está de acordo com a Resolução n° %s do Regulamento "
                                  "das Atividades Complementares.</li>"),
                              m_resolution == N_16 ? wxT("16") : wxT("20"));
    for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
        Activity* activity = *it;
        if(activity->GetObs() != "") { olStr += "<li>" + activity->GetObs() + "</li>"; }
    }
    olStr += "</ol>";
    pdf.WriteXml(olStr);

    pdf.Ln(15);
    wxDateTime dateNow = wxDateTime::Now();
    pdf.Cell(0, 0,
             wxString::Format("Itumbiara/GO, %d de %s de %d.", dateNow.GetDay(),
                              wxDateTime::GetMonthName(dateNow.GetMonth()), dateNow.GetYear()),
             wxPDF_BORDER_NONE, 0, wxPDF_ALIGN_RIGHT);
    pdf.Ln(10);

    wxFileInputStream fSgn(wxS("signatures.txt"));
    len = fSgn.GetLength();
    ctxt = new char[len + 1];
    fSgn.Read(ctxt, len);
    ctxt[len] = '\0';
    wxString fSgnTxt(ctxt, *wxConvCurrent);
    pdf.WriteXml(fSgnTxt);

    wxFileDialog saveFileDialog(this, _("Salvar PDF"), "", "", "Arquivos PDF (*.pdf)|*.pdf",
                                wxFD_SAVE | wxFD_OVERWRITE_PROMPT);
    if(saveFileDialog.ShowModal() == wxID_CANCEL) return;

    // save the current contents in the file;
    if(!pdf.SaveAsFile(saveFileDialog.GetPath())) {
        wxMessageDialog dialog(
            this, wxString::Format(wxT("Não é possível salvar o arquivo em '%s'."), saveFileDialog.GetPath()),
            wxT("Erro"), wxICON_ERROR);
        dialog.ShowModal();
        return;
    } else {
        wxLaunchDefaultApplication(saveFileDialog.GetPath());
    }
}

void MainFrame::FillAllRows()
{
    for(int i = 0; i < m_grid->GetNumberRows(); ++i) {
        // Get activity
        long int id = -1;
        m_grid->GetCellValue(i, 0).ToLong(&id);
        Activity* activity = NULL;
        for(auto it = m_activityList.begin(), itEnd = m_activityList.end(); it != itEnd; ++it) {
            if((*it)->GetId() == id) {
                activity = *it;
                break;
            }
        }

        if(activity) {
            bool shiftN = false;
            bool ifgEvent = false;
            bool ch = false;

            switch(activity->GetItemCode()) {
                case 1:
                case 2: {
                    shiftN = true;
                } break;
                case 3:
                case 4: {
                    shiftN = true;
                    ifgEvent = true;
                    ch = true;
                } break;
                case 5: {
                    shiftN = true;
                } break;
                case 6:
                case 11:
                case 16: {
                    ch = true;
                } break;
                case 7:
                case 8:
                case 9:
                case 10:
                case 12: {
                    // nothing really matters...
                } break;
                case 13:
                case 14:
                case 15: {
                    // to me...
                } break;
                case 17: {
                    shiftN = true;
                } break;
                default:
                    break;
            }

            m_pgPropItem->SetValueFromInt(activity->GetItemCode());
            m_grid->SetCellValue(i, 1, m_pgPropItem->GetValueAsString());

            m_grid->SetCellValue(i, 2, activity->GetEventName());

            wxString shiftNStr = "-";
            if(shiftN) shiftNStr = wxString::Format("%d", static_cast<int>(activity->GetShiftNumber()));
            m_grid->SetCellValue(i, 3, shiftNStr);

            wxString ifgEventStr = "-";
            if(ifgEvent) ifgEventStr = activity->IsIFGEvent() ? wxT("Sim") : wxT("Não");
            m_grid->SetCellValue(i, 4, ifgEventStr);

            m_grid->SetCellValue(i, 5, activity->GetInstitutionName());

            wxString chPresentedStr = "-";
            if(ch) chPresentedStr = wxString::Format("%f", activity->GetChPresented());
            m_grid->SetCellValue(i, 6, chPresentedStr);

            m_grid->SetCellValue(i, 7, activity->GetDate());

            m_grid->SetCellValue(i, 8, wxString::Format("%f", activity->GetChValidated()));

            wxColour rowColour = *wxBLACK;
            if(activity->IsLimitedCH()) { rowColour = *wxRED; }
            for(int j = 0; j < 9; ++j) m_grid->SetCellTextColour(i, j, rowColour);
        }
    }
}
void MainFrame::OnAboutClick(wxCommandEvent& event)
{
    wxAboutDialogInfo aboutInfo;
    aboutInfo.SetName(wxT("Avaliador CAAC"));
    aboutInfo.SetVersion(MY_APP_VERSION_STRING);
    aboutInfo.SetDescription(
        wxT("Software auxiliar para cálculo e geração de relatórios de avaliação de horas complementares pela CAAC\n\n"
            "Comissão para Avaliação de Atividades Complementares - Setor da Indústria\nIFG - Câmpus Itumbiara"));
    aboutInfo.SetCopyright("(C) 2020");
    aboutInfo.AddDeveloper("Thales Lima Oliveira (thales.oliveira@ifg.edu.br)");
    wxGenericAboutDialog dlgAbout(aboutInfo, this);
    dlgAbout.ShowModal();
}
