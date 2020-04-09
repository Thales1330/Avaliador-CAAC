#include "FormatValues.h"

FormatValues::FormatValues(wxString protocol, wxString name)
{
    m_fProtocol = protocol;
    m_fProtocol.Replace(".", "-");
    m_fProtocol.Replace("/", "-");
    m_fProtocol.Replace(" ", "-");
    m_fName = name;
    m_fName.Replace(".", "-");
    m_fName.Replace("/", "-");
    m_fName.Replace(" ", "-");
}

bool FormatValues::Deformat(wxString formatedFile, wxString& protocol, wxString& name)
{
    if(formatedFile == "") return false;

    wxString nameUnformated = "";
    wxString protocolUnformated = "";

    protocolUnformated = formatedFile.BeforeFirst('[', &nameUnformated);
    if(!nameUnformated) return false;
    nameUnformated = nameUnformated.BeforeFirst(']');

    int pos = protocolUnformated.find('-');
    if(pos != wxNOT_FOUND) protocolUnformated[pos] = '.';
    pos = protocolUnformated.find('-');
    protocolUnformated[pos] = '/';

    pos = nameUnformated.find('-');
    while(pos != wxNOT_FOUND) {
        nameUnformated[pos] = ' ';
        pos = nameUnformated.find('-');
    }

    protocol = protocolUnformated;
    name = nameUnformated;
    return true;
}
