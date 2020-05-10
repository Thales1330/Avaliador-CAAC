#include "EventList.h"
#include "Utils.h"

EventList::EventList() {}

bool EventList::Load(wxWindow* parent)
{
    wxBusyInfo busy(Utils::Get().BusyInfo(parent, wxT("Avaliador CAAC"), wxT("Atualizando lista de eventos...")));
    // Get ID from Drive
    wxExecute(wxString::Format("%s FindInfolder \"%s\"", m_runDriveAPI, "EventList.xml"),
              wxEXEC_SYNC | m_consoleStatus);
    // Get ID in file
    wxTextFile txtFileIDs;
    wxString fileID = "";
    if(txtFileIDs.Open("foundIDs.txt")) {
        fileID = txtFileIDs.GetFirstLine();
        txtFileIDs.Clear();
        txtFileIDs.Write();
    } else
        return false;

    if(fileID == "") return false;

    wxExecute(wxString::Format("%s Download \"%s\" \"%s\"", m_runDriveAPI, fileID, "EventList.xml"),
              wxEXEC_SYNC | m_consoleStatus);

    if(!LoadEventList()) return false;

    return true;
}

bool EventList::LoadEventList()
{
    rapidxml::xml_document<> doc;
    rapidxml::file<> xmlFile("EventList.xml");

    m_eventList.Clear();

    doc.parse<0>(xmlFile.data());

    auto rootNode = doc.first_node("Lista");
    if(!rootNode) return false;
    auto eventNode = rootNode->first_node("Evento");
    while(eventNode) {
        m_eventList.Add(wxString::FromUTF8(eventNode->value()));
        eventNode = eventNode->next_sibling("Evento");
    }

    return true;
}

void EventList::Save(wxWindow* parent, wxArrayString eventList)
{
    for(auto it = eventList.begin(), itEnd = eventList.end(); it != itEnd; ++it) {
        wxString newEvent = *it;
        bool isNewEvent = true;
        for(auto itB = m_eventList.begin(), itEndB = m_eventList.end(); itB != itEndB; ++itB) {
            wxString oldEvent = *itB;
            if(newEvent == oldEvent) {
                isNewEvent = false;
                break;
            }
        }
        if(isNewEvent) m_eventList.Add(newEvent);
    }
    
    // Save event file
    
    // Erase the file (if exists or not) and write the initial data
    std::ofstream writeEventList("EventList.xml");
    writeEventList.close();

    rapidxml::xml_document<> doc;
    rapidxml::file<> xmlFile("EventList.xml");
    doc.parse<0>(xmlFile.data());

    rapidxml::xml_node<>* decl = doc.allocate_node(rapidxml::node_declaration);
    rapidxml::xml_attribute<>* ver = doc.allocate_attribute("version", "1.0");
    rapidxml::xml_attribute<>* encoding = doc.allocate_attribute("encoding", "utf-8");
    decl->append_attribute(ver);
    decl->append_attribute(encoding);
    doc.append_node(decl);
    
    rapidxml::xml_node<>* rootNode = doc.allocate_node(rapidxml::node_element, "Lista");
    doc.append_node(rootNode);

    for(auto it = m_eventList.begin(), itEnd = m_eventList.end(); it != itEnd; ++it) {
        rapidxml::xml_node<>* eventName = XMLParser::AppendNode(doc, rootNode, "Evento");
        XMLParser::SetNodeValue(doc, eventName, *it);
    }
    
    std::ofstream writeXML("EventList.xml");
    writeXML << doc;
    writeXML.close();
    
    //SaveAtDrive("EventList.xml", "EventList.xml");
    Utils::Get().SaveAtDrive(parent, "EventList.xml", "EventList.xml", false, wxT("Atualizando lista de eventos..."));
}