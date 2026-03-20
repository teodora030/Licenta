import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from langchain_anthropic import ChatAnthropic
from anthropic import Anthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

class RelatieGeometrica(BaseModel):
    tip: str = Field(description="Tipul constructiei geometrice. ex: punct_pe_latura, inaltime, bisectoare, mijloc, mediana, mediatoare, drepte paralele, puncte coliniare, simetricul unui punct fata de alt punct, altele. Foloseste 'punct_pe_latura' cand un punct nou se afla pe o latura existenta a figurii (ex: E pe AB, F pe AC).")
    nume_punct_nou: Optional[str] = Field(description="Numele punctului rezultat, ex: D",default=None)
    elemente_vizate: List[str] = Field(description="Numele elementelor pe care le folosim pentru a construi un element dependent. ex: ['AB']",default=None)
    detalii: Optional[str] = Field(description="Orice informatie suplimentara despre constructie, ex: 'E este intre A si B', 'M este mijlocul lui BC'",default=None)

class ExtragereDateleProblemei(BaseModel):
    tip_figura: str = Field(description="Normalizat: drepte_paralele, triunghi_oarecare, triunghi_isoscel, triunghi_echilateral, triunghi_dreptunghic, patrulater_oarecare, paralelogram, patrat, dreptunghi, romb, trapez")
    puncte_principale: List[str] = Field(description="DOAR punctele care definesc varfurile figurii principale, ex: ['A','B','C'] pentru triunghi, , ['A','B','C','D'] pentru patrulater. NU include puncte auxiliare precum E, F, M, H etc.")
    puncte_mentionate: List[str] = Field(description="Lista tuturor punctelor care sunt mentionate in problema, ex: ['A','B','C','D','E','F','H','P']")
    laturi_mentionate: List[str] = Field(description="Lista laturilor care formeaza figura, ex: ['AB','BC','AC','EF']")
    laturi_date: Dict[str,float] = Field(description="Laturile date in problema cu valori numerice cunoscute, ex: {'AB': 6,'BC':10}")
    unghiuri_mentionate: List[str] = Field(description="Lista unghiurilor care formeaza figura, ex: ['AB','BC','AC']")
    unghiuri_date: Dict[str, float] = Field(description="Unghiurile cu valori in grade. Ex: {'B': 90, 'A': 45, 'AOB':30}")
    relatii_suplimentare: List[RelatieGeometrica] = Field(description="TOATE constructiile suplimentare din problema. IMPORTANT: daca un punct nou (E, F, D, M...) apare pe o latura, adauga o relatie cu tip='punct_pe_latura'.Ex: E pe AB -> tip='punct_pe_latura', nume_punct_nou='E', pe_elementul='AB'")
    cerinte: List[str] = Field(description="Lista cerintelor problemei text, ex: ['Calculeaza lungimea segmentului EF','Demonstreaza ca triunghiurile ABC si AEF sunt asemenea']")


FEW_SHOT_EXAMPLES = """
EXEMPLU 1:
Problema: "In triunghiul ABC, AB=10 cm, AC=8 cm si BC=6 cm. Inaltimea din A pe BC are piciorul in D. Calculati AD."
Raspuns corect:
{{
  "tip_figura": "triunghi_oarecare",
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "D"],
  "laturi_mentionate": ["AB", "AC", "BC", "AD"],
  "laturi_date": {{"AB": 10.0, "AC": 8.0, "BC": 6.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "relatii_suplimentare": [
    {{
      "tip": "inaltime",
      "nume_punct_nou": "D",
      "elemente_vizate": ["BC"],
      "detalii": "AD este inaltimea din A pe latura BC, D este piciorul inaltimii"
    }}
  ],
  "cerinte": ["Calculeaza AD"]
}}
 
EXEMPLU 2:
Problema: "In triunghiul ABC, AB=24 cm, AC=32 cm si BC=36 cm. E este pe AB cu BE=15 cm, F este pe AC cu AF=12 cm. Cat este EF?"
Raspuns corect:
{{
  "tip_figura": "triunghi_oarecare",
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "E", "F"],
  "laturi_mentionate": ["AB", "AC", "BC", "BE", "AF", "EF"],
  "laturi_date": {{"AB": 24.0, "AC": 32.0, "BC": 36.0, "BE": 15.0, "AF": 12.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "relatii_suplimentare": [
    {{
      "tip": "punct_pe_latura",
      "nume_punct_nou": "E",
      "elemente_vizate": ["AB"],
      "detalii": "E este pe latura AB, intre A si B"
    }},
    {{
      "tip": "punct_pe_latura",
      "nume_punct_nou": "F",
      "elemente_vizate": ["AC"],
      "detalii": "F este pe latura AC, intre A si C"
    }}
  ],
  "cerinte": ["Calculeaza lungimea segmentului EF"]
}}
 
EXEMPLU 3:
Problema: "In triunghiul isoscel ABC cu AB=AC=13 cm si BC=10 cm, M este mijlocul lui BC. Calculati AM."
Raspuns corect:
{{
  "tip_figura": "triunghi_isoscel",
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "M"],
  "laturi_mentionate": ["AB", "AC", "BC", "AM"],
  "laturi_date": {{"AB": 13.0, "AC": 13.0, "BC": 10.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "relatii_suplimentare": [
    {{
      "tip": "mijloc",
      "nume_punct_nou": "M",
      "elemente_vizate": ["BC"],
      "detalii": "M este mijlocul segmentului BC"
    }}
  ],
  "cerinte": ["Calculeaza AM"]
}}
""".strip()


def scoate_datele_problemei(text_problema):
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    parser=PydanticOutputParser(pydantic_object=ExtragereDateleProblemei)
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Ești un asistent expert în matematică și geometrie plană.
            Rolul tău este să analizezi o problemă de geometrie în limba română și să extragi datele esențiale într-un format structurat precis.
            
            Reguli:
            1. Identifică corect tipul figurii principale (ex: dacă problema zice 'triunghi cu un unghi de 90 grade', tipul este 'triunghi_dreptunghic').
            2. Extrage doar valorile numerice pentru laturi și unghiuri. Nu inventa valori care nu apar în text.
            3. Analizează cu atenție relațiile suplimentare (înălțimi, bisectoare, mijloace).
            
            Răspunde STRICT în formatul de mai jos, fără niciun alt text explicativ:
            \n{format_instructions}
            EXEMPLE REZOLVATE (urmeaza exact acelasi pattern):{few_shot}
            """,
        ),
        ("human", "Extrage datele din urmatoarea problema: {query}")
    ]
    ).partial(format_instructions=parser.get_format_instructions(),few_shot=FEW_SHOT_EXAMPLES)

    chain = prompt | llm | parser

    try:
        rezultat_structurat = chain.invoke({"query": text_problema})
        return rezultat_structurat.model_dump()
    except Exception as e:
        print(f"Eroare la LLM: {e}")
        return None