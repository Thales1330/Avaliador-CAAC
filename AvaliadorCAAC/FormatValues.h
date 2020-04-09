#ifndef FORMATVALUES_H
#define FORMATVALUES_H

#include <wx/string.h>

class FormatValues
{
   public:
    FormatValues() {}
    FormatValues(wxString protocol, wxString name);
    ~FormatValues() {}

    wxString GetProtocol() { return m_fProtocol; }
    wxString GetName() { return m_fName; }
    bool Deformat(wxString formatedFile, wxString& protocol, wxString& name);

   private:
    wxString m_fProtocol;
    wxString m_fName;
};

#endif  // FORMATVALUES_H
