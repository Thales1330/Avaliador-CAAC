#ifndef PDFPAGE_H
#define PDFPAGE_H

#include "wx/pdfdoc.h"

class PdfPage : public wxPdfDocument
{
public:
    PdfPage() {}
    ~PdfPage() {}
    
    void Header();
    //void Footer();

};

#endif // PDFPAGE_H
