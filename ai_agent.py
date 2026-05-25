import os
import json
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

class ComenziGeogebra(BaseModel):
    comenzi: List[str] = Field(description="Lista de comenzi text pentru GeoGebra, in ordinea logica a constructiei.")

class LinieGeoGebra(BaseModel):
    comanda: str = Field(description="Comanda GeoGebra (fara comentariu)")
    schimbat: bool = Field(description="True daca aceasta linie a fost modificata fata de codul original")
    explicatie: Optional[str] = Field(description="Daca schimbat=True, explicatie scurta despre ce s-a reparat", default=None)

class ComenziReparate(BaseModel):
    comenzi: List[LinieGeoGebra] = Field(description="Lista de comenzi reparate, in ordine. Pentru fiecare linie indica daca a fost schimbata.")    
    
FEW_SHOT_EXAMPLES_DATE = """
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
    ).partial(format_instructions=parser.get_format_instructions(),few_shot=FEW_SHOT_EXAMPLES_DATE)

    chain = prompt | llm | parser

    try:
        rezultat_structurat = chain.invoke({"query": text_problema})
        return rezultat_structurat.model_dump()
    except Exception as e:
        print(f"Eroare la LLM: {e}")
        return None
    
FEW_SHOT_EXAMPLES_COD = """
Exemplul 1:
Date de intrare:
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

Raspuns corect:

["A=(0,0)",
"B=(10,0)",
"c_a=Circle(A, 8)",
"c_b=Circle(B, 6)",
"C = Intersect(c_a, c_b, 1)",
"abc = Polygon(A, B, C)",
"SetVisibleInView(c_a, 1, false)",
"SetVisibleInView(c_b, 1, false)",
"bc = Segment(B, C)",
"h_line = PerpendicularLine(A, bc)",
"D = Intersect(bc, h_line)",
"ad = Segment(A, D)",
"SetVisibleInView(h_line, 1, false)"]


Exemplul 2:
Date de intrare:
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
Mentiuni: Dacă un punct se află pe un segment și se cunoaște distanța, folosește formula vectoriala: Punct = Origine + (distanta/lungime_totala) * (Destinatie - Origine)
Raspuns corect:

["A=(0,0)",
"B=(24,0)",
"c_a=Circle(A, 32)",
"c_b=Circle(B, 36)",
"C = Intersect(c_a, c_b, 1)",
"abc = Polygon(A, B, C)",
"E = A + (9/24) * (B - A)",
"F = A + (12/32) * (C - A)",
"ef = Segment(E, F)",
"SetVisibleInView(c_a, 1, false)",
"SetVisibleInView(c_b, 1, false)"]



Exemplul 3:
Date de intrare:
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
Raspuns corect:

["A=(0,0)",
"B=(24,0)",
"c_a=Circle(A, 32)",
"c_b=Circle(B, 36)",
"C = Intersect(c_a, c_b, 1)",
"abc = Polygon(A, B, C)",
"SetVisibleInView(c_a, 1, false)",
"SetVisibleInView(c_b, 1, false)",
"bc=Segment(B,C)",
"M=Midpoint(bc)",
"am=Segment(A,M)"]

Exemplul 4:
Date de intrare:
{
  "tip_figura": "paralelogram",
  "puncte_principale": ["A", "B", "C", "D"],
  "laturi_date": {"AB": 6.0, "AD": 4.0},
  "unghiuri_date": {"DAB": 60.0},
  "relatii_suplimentare": []
}
Raspuns corect:

  [
    "A = (0, 0)",
    "B = (6, 0)",
    "D = (4; 60°)",
    "C = D + (B - A)",
    "p1 = Polygon(A, B, C, D)"
  ]


""".strip()
    
def genereaza_comenzi_geogebra(date_problema):
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    parser = PydanticOutputParser(pydantic_object=ComenziGeogebra)

    prompt = ChatPromptTemplate.from_messages([
        ("system",""" 
            Primești un JSON cu datele unei probleme de geometrie.
            Rolul tău este să generezi EXACT comenzile GeoGebra necesare pentru a desena acea figură.
            
            Reguli vitale:
            1. Primul punct pune-l mereu în origine: P1=(0,0).
            2. Construiește baza inteligent (ex: dacă ai o latură P1P2 de 5, pune P2=(5,0)).
            3. Folosește comenzi native GeoGebra (ex: Polygon(A,B,C), Midpoint(B,C), Line(A,B), Intersect(f,g)).
            4. Foloseste comenzi declarative cand construiesti figuri ale caror laturi sunt date explicit, pentru a asigura ca lungimile raman valabile (ex: "A = (0, 0)","B = (5, 0)","c_a = Circle(A, 4)","c_b = Circle(B, 3)","C = Intersect(c_a, c_b, 1)").
            5. Ascunde etichetele obiectelor ajutătoare dacă e cazul (ex: "SetVisibleInView(c_a, 1, false)","SetVisibleInView(c_b, 1, false)").
            6. Regula stricta de numire: In geogebra, punctele trebuie sa aiba nume cu majuscule (A,C,P), segmentele, dreptele, cercurile trebuie sa aiba nume cu litere mici, (ex: corect este `ac = Segment(A,C)`, greșit este `AC = Segment(A,C)`)
            
            Nu explica logica, returnează STRICT în formatul JSON cerut mai jos:
            \n{format_instructions}
            EXEMPLE REZOLVATE (urmeaza acelasi pattern):{few_shot_cod}
                  """
        ),
        ("human","datele problemei sunt: \n{date_json}")
        ]).partial(format_instructions=parser.get_format_instructions(),few_shot_cod=FEW_SHOT_EXAMPLES_COD)

    chain = prompt | llm | parser

    try:
        rezultat_structurat = chain.invoke({"date_json": json.dumps(date_problema)})
        return rezultat_structurat.comenzi
    except Exception as e:
        print(f"Eroare la ai: {e}")
        return None
    

def repara_comenzi_geogebra(date_problema, cod_anterior, raport):
    """
    Primește codul GeoGebra anterior și raportul de execuție cu erori.
    Returnează codul reparat cu marcarea liniilor schimbate.
    """
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    parser = PydanticOutputParser(pydantic_object=ComenziReparate)
    
    # Formatam raportul ca text linie-cu-linie
    raport_text = ""
    for i, item in enumerate(raport["comenzi"], start=1):
        if item["succes"]:
            raport_text += f"Linia {i}: {item['comanda']} → OK\n"
        else:
            eroare = item.get("eroare") or "necunoscuta"
            raport_text += f"Linia {i}: {item['comanda']} → EROARE: {eroare}\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Rolul tau este sa repari comenzi GeoGebra care au esuat la executie.
            
            Ai primit:
            1. Datele unei probleme de geometrie
            2. Codul GeoGebra generat anterior pentru aceasta problema
            3. Raportul de executie care arata ce comenzi au reusit (OK) si care au esuat (EROARE)
            
            Sarcina ta:
            - Analizeaza fiecare comanda care a esuat si identifica cauza
            - Returneaza INTREG codul reparat, in ordine logica
            - Pastreaza comenzile care au reusit, doar daca raman valide in contextul reparat
            - Pentru fiecare linie indica daca a fost schimbata (schimbat=true/false)
            - Pentru liniile schimbate adauga o explicatie scurta in romana
            
            Reguli GeoGebra importante:
            - Punctele au nume cu MAJUSCULE (A, B, C, M, N)
            - Segmentele, dreptele, cercurile, razele au nume cu litere mici (ab, oc, h_line)
            - Rotate(Punct, unghi, centru) → returneaza un Punct
            - Rotate(Dreapta/Raza/Segment, unghi, centru) → returneaza acelasi tip
            - Ray(P1, P2) cere DOUA PUNCTE, nu accepta raze sau drepte
            - Intersect(d, c) cu cerc poate returna o lista; foloseste Intersect(d, c, 1) pentru primul punct
            
            Raspunde STRICT in formatul JSON cerut:
            \n{format_instructions}
            """
        ),
        ("human", """
            Datele problemei:
            {date_problema}
            
            Codul anterior generat:
            {cod_anterior}
            
            Raportul de executie:
            {raport_text}
            
            Repara codul.
            """
        )
    ]).partial(format_instructions=parser.get_format_instructions())
    
    chain = prompt | llm | parser
    
    try:
        rezultat = chain.invoke({
            "date_problema": json.dumps(date_problema, ensure_ascii=False),
            "cod_anterior": cod_anterior,
            "raport_text": raport_text
        })
        return rezultat.model_dump()
    except Exception as e:
        print(f"Eroare la reparare: {e}")
        return None