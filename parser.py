import PyPDF2
import docx
import re

class ResumeParser:

    def extract_text(self, file):

        if file.endswith(".pdf"):
            with open(file,"rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join(p.extract_text() for p in reader.pages)

        if file.endswith(".docx"):
            doc = docx.Document(file)
            return "\n".join(p.text for p in doc.paragraphs)

        if file.endswith(".txt"):
            return open(file,"r",encoding="utf8").read()

    def parse(self, file):

        text = self.extract_text(file)

        email = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        phone = re.findall(r'\d{10}', text)

        return {
            "raw_text": text,
            "email": email[0] if email else "",
            "phone": phone[0] if phone else ""
        }
