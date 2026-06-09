import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from langchain_anthropic import ChatAnthropic
from anthropic import Anthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from sympy import sympify

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

class RelatieGeometrica(BaseModel):
    tip: str = Field(description="Tipul constructiei geometrice. ex: punct_pe_latura, inaltime, bisectoare, mijloc, mediana, mediatoare, drepte_paralele, puncte_coliniare, simetricul_unui_punct_fata_de_alt_punct, altele. Foloseste 'punct_pe_latura' cand un punct nou se afla pe o latura existenta a figurii (ex: E pe AB, F pe AC).")
    nume_punct_nou: Optional[str] = Field(description="Numele punctului rezultat, ex: D",default=None)
    elemente_vizate: List[str] = Field(description="Numele elementelor pe care le folosim pentru a construi un element dependent. ex: ['AB']",default=[])
    detalii: Optional[str] = Field(description="Orice informatie suplimentara despre constructie, ex: 'E este intre A si B', 'M este mijlocul lui BC'",default=None)

class ExtragereDateleProblemei(BaseModel):
    tip_figura: List[str] = Field(
        description=(
            "Lista de categorii care descriu figura. Cele mai multe probleme au o singura categorie, "
            "dar unele pot avea mai multe (ex: ['triunghi_dreptunghic', 'inscris_in_cerc']). "
            "Categorii valide (foloseste EXACT dintre ele, NU inventa altele): "
            "puncte_coliniare,drepte_paralele, triunghi_oarecare, triunghi_isoscel, triunghi_echilateral, "
            "triunghi_dreptunghic, patrulater_oarecare, paralelogram, patrat, dreptunghi, "
            "romb, trapez, unghi, cerc, inscris_in_cerc, circumscris_cercului, "
            "prisma, cub, piramida, graficul_functiei,"
            "drepte_perpendiculare, constructia_triunghiurilor,linii_importante_in_triunghi,congruenta_triunghiurilor,"
            "asemanarea_triunghiurilor,geometrie_in_spatiu,tetraedru,paralelipiped_dreptunghic, cilindru, con, paralelism_in_spatiu, perpendiculatitate_in_spatiu, proiectii_de_puncte, unghi_diedru, teorema_celor_trei_perpendiculare,altele"
        )
    )
    puncte_principale: List[str] = Field(
        description="DOAR punctele care definesc varfurile figurii principale, ex: ['A','B','C'] pentru triunghi, ['A','B','C','D'] pentru patrulater. NU include puncte auxiliare precum E, F, M, H etc."
    )
    puncte_mentionate: List[str] = Field(
        description="Lista TUTUROR punctelor mentionate in problema, inclusiv cele auxiliare. Ex: ['A','B','C','D','E','F','H','P']"
    )
    laturi_mentionate: List[str] = Field(
        description="Lista laturilor/segmentelor care apar in problema, ex: ['AB','BC','AC','EF']"
    )
    laturi_date: Dict[str, float] = Field(
        description=(
            "Laturile cu valori numerice DIRECT date in problema (nu derivate)."
            "Ex: 'AB = 6 cm, BC = 10 cm' -> {'AB': 6.0, 'BC': 10.0}. "
        )
    )
    unghiuri_mentionate: List[str] = Field(
        description="Lista unghiurilor mentionate, ex: ['BAC', 'ABC']"
    )
    unghiuri_date: Dict[str, float] = Field(
        description="Unghiurile cu valori in grade. Ex: 'unghi B = 90' -> {'B': 90}, 'unghi AOB = 30' -> {'AOB': 30}"
    )
    proprietati_varfuri: Dict[str, str] = Field(
        description=(
            "Proprietati speciale ale unor puncte. Cheia=numele punctului, valoarea=proprietatea. "
            "EXEMPLE: "
            "'triunghi dreptunghic in C' -> {'C': 'unghi_drept'}; "
            "'cerc cu centrul O' -> {'O': 'centru_cerc'}; "
            "'tangenta in A la cerc' -> {'A': 'punct_tangenta'}. "
            "Daca nu sunt proprietati speciale, returneaza {}."
        ),
        default={}
    )
    aria: Optional[float] = Field(
        description=(
            "Aria DATA explicit (ca valoare). null daca e doar ceruta sau absenta."
        ),
        default=None
    )
    perimetru: Optional[float] = Field(
        description=(
            "Perimetrul figurii daca este DAT explicit. Daca e doar cerut, returneaza null."
        ),
        default=None
    )
    relatii_intre_laturi: List[str] = Field(
        description=("Relatii algebrice intre laturi, format 'rezultat = expresie'. Ex: ['BD = 3*CD']."
        ),
        default=[]
    )

    relatii_intre_unghiuri: List[str] = Field(
        description=(
            "Relatii algebrice intre unghiuri, NU valori directe. Format STRICT: 'rezultat = expresie'. "
            "EXEMPLE: "
            "'unghi AOC + unghi COB = 180' -> ['AOC + COB = 180']; "
            "'unghi A = 2 * unghi B' -> ['A = 2*B']; "
            "'AOC si COB sunt complementare' -> ['AOC + COB = 90']. "
            "Foloseste denumiri de unghiuri (BAC, AOM, etc.), nu numere. "
            "Pentru valori directe (B = 90°), foloseste unghiuri_date, NU acest camp."
        ),
        default=[]
    )

    relatii_suplimentare: List[RelatieGeometrica] = Field(
        description="TOATE constructiile suplimentare. IMPORTANT: daca un punct nou (E, F, D, M...) apare pe o latura, adauga relatie cu tip='punct_pe_latura'. Ex: E pe AB -> tip='punct_pe_latura', nume_punct_nou='E', elemente_vizate=['AB']"
    )
    cerinte: List[str] = Field(
        description="Lista cerintelor problemei, ex: ['Calculeaza lungimea EF', 'Demonstreaza ca ABC ~ AEF']"
    )

    # ========== Campuri specifice pentru functii ==========
    # Folosite DOAR cand 'graficul_functiei' este in tip_figura
    
    formula_functie: Optional[str] = Field(
        description=(
            "Formula functiei in sintaxa GeoGebra (cu * explicit pentru inmultire, ^ pentru putere). "
            "Variabila trebuie sa fie 'x'. "
            "EXEMPLE: "
            "'f(x) = 2x + 4' -> '2*x + 4'; "
            "'f(x) = x^2 - 3x + 2' -> 'x^2 - 3*x + 2'; "
            "'f(x) = 1/x' -> '1/x'. "
            "Doar pentru probleme cu tip_figura='graficul_functiei', altfel null."
        ),
        default=None
    )
    tip_functie: Optional[str] = Field(
        description=(
            "Tipul functiei. Valori posibile: 'liniara', 'patratica', 'cubica', "
            "'exponentiala', 'logaritmica', 'trigonometrica', 'rationala', 'altele'. "
            "Doar pentru probleme cu functii, altfel null."
        ),
        default=None
    )
    domeniu_functie: Optional[str] = Field(
        description=(
            "Domeniul functiei ca apare in problema. "
            "EXEMPLE: 'R', '[0, 10]', '(-infinit, 5)', 'R \\ {0}'. "
            "Daca nu e specificat in problema, foloseste 'R' implicit. "
            "Doar pentru probleme cu functii, altfel null."
        ),
        default=None
    )
    codomeniu_functie: Optional[str] = Field(
        description=(
            "Codomeniul functiei ca apare in problema. "
            "Daca nu e specificat, 'R' implicit. "
            "Doar pentru probleme cu functii, altfel null."
        ),
        default=None
    )
  
class ComenziGeogebra(BaseModel):
    rationament: str = Field(description=(
        "Gandeste pas cu pas INAINTE de comenzi: unde plasez fiecare punct, "
        "ce coordonate rezulta, care intersectie (index) cade in semiplanul "
        "y>0, cum verific ca lungimile/unghiurile ies corecte."
    ))
    comenzi: List[str] = Field(description="Lista de comenzi text pentru GeoGebra, in ordinea logica a constructiei.")

class LinieGeoGebra(BaseModel):
    comanda: str = Field(description="Comanda GeoGebra (fara comentariu)")
    schimbat: bool = Field(description="True daca aceasta linie a fost modificata fata de codul original")
    explicatie: Optional[str] = Field(description="Daca schimbat=True, explicatie scurta despre ce s-a reparat", default=None)

class ComenziReparate(BaseModel):
    comenzi: List[LinieGeoGebra] = Field(description="Lista de comenzi reparate, in ordine. Pentru fiecare linie indica daca a fost schimbata.")    
    
FEW_SHOT_EXAMPLES_DATE = """
EXEMPLU 1 (triunghi cu inaltime):
Problema: "In triunghiul ABC, AB=10 cm, AC=8 cm si BC=6 cm. Inaltimea din A pe BC are piciorul in D. Calculati AD."
Raspuns corect:
{{
  "tip_figura": ["triunghi_oarecare"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "D"],
  "laturi_mentionate": ["AB", "AC", "BC", "AD"],
  "laturi_date": {{"AB": 10.0, "AC": 8.0, "BC": 6.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "proprietati_varfuri": {{}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
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

EXEMPLU 2 (puncte pe laturi):
Problema: "In triunghiul ABC, AB=24 cm, AC=32 cm si BC=36 cm. E este pe AB cu BE=15 cm, F este pe AC cu AF=12 cm. Cat este EF?"
Raspuns corect:
{{
  "tip_figura": ["triunghi_oarecare"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "E", "F"],
  "laturi_mentionate": ["AB", "AC", "BC", "BE", "AF", "EF"],
  "laturi_date": {{"AB": 24.0, "AC": 32.0, "BC": 36.0, "BE": 15.0, "AF": 12.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "proprietati_varfuri": {{}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
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

EXEMPLU 3 (triunghi isoscel cu mijloc):
Problema: "In triunghiul isoscel ABC cu AB=AC=13 cm si BC=10 cm, M este mijlocul lui BC. Calculati AM."
Raspuns corect:
{{
  "tip_figura": ["triunghi_isoscel"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "M"],
  "laturi_mentionate": ["AB", "AC", "BC", "AM"],
  "laturi_date": {{"AB": 13.0, "AC": 13.0, "BC": 10.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "proprietati_varfuri": {{}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
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

EXEMPLU 4 (triunghi inscris in cerc - multi-categorie):
Problema: "Triunghiul ABC este inscris in cercul de centru O. Coarda BC are lungimea 10 cm, iar unghiul BAC = 60°. Calculati raza cercului."
Raspuns corect:
{{
  "tip_figura": ["triunghi_oarecare", "inscris_in_cerc"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "O"],
  "laturi_mentionate": ["AB", "AC", "BC"],
  "laturi_date": {{"BC": 10.0}},
  "unghiuri_mentionate": ["BAC"],
  "unghiuri_date": {{"BAC": 60.0}},
  "proprietati_varfuri": {{"O": "centru_cerc"}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
  "relatii_suplimentare": [],
  "cerinte": ["Calculeaza raza cercului"]
}}

EXEMPLU 5 (cub - figura 3D):
Problema: "In cubul ABCDA'B'C'D' cu AB = 8 cm, M este mijlocul muchiei CC'. Calculati lungimea segmentului AM."
Raspuns corect:
{{
  "tip_figura": ["cub"],
  "puncte_principale": ["A", "B", "C", "D", "A'", "B'", "C'", "D'"],
  "puncte_mentionate": ["A", "B", "C", "D", "A'", "B'", "C'", "D'", "M"],
  "laturi_mentionate": ["AB", "CC'", "AM"],
  "laturi_date": {{"AB": 8.0}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "proprietati_varfuri": {{}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
  "relatii_suplimentare": [
    {{
      "tip": "mijloc",
      "nume_punct_nou": "M",
      "elemente_vizate": ["CC'"],
      "detalii": "M este mijlocul muchiei CC'"
    }}
  ],
  "cerinte": ["Calculeaza lungimea segmentului AM"]
}}

EXEMPLU 6 (unghiuri adiacente suplementare):
Problema: "Unghiurile AOC si COB sunt adiacente suplementare. Stiind ca unghiul AOC = 110° si OM este bisectoarea unghiului COB, calculati unghiul AOM."
Raspuns corect:
{{
  "tip_figura": ["unghi"],
  "puncte_principale": ["O"],
  "puncte_mentionate": ["A", "O", "B", "C", "M"],
  "laturi_mentionate": ["OA", "OB", "OC", "OM"],
  "laturi_date": {{}},
  "unghiuri_mentionate": ["AOC", "COB", "AOM"],
  "unghiuri_date": {{"AOC": 110.0}},
  "proprietati_varfuri": {{"O": "varf_unghi"}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
  "relatii_intre_unghiuri": ["AOC + COB = 180", "COM = MOB", "COM = COB/2"],
  "relatii_suplimentare": [
    {{
      "tip": "unghiuri_adiacente_suplementare",
      "nume_punct_nou": null,
      "elemente_vizate": ["AOC", "COB"],
      "detalii": "Unghiurile AOC si COB sunt adiacente suplementare, deci AOC + COB = 180°"
    }},
    {{
      "tip": "bisectoare",
      "nume_punct_nou": "M",
      "elemente_vizate": ["COB"],
      "detalii": "OM este bisectoarea unghiului COB"
    }}
  ],
  "cerinte": ["Calculeaza unghiul AOM"]
}}

EXEMPLU 7 (graficul unei functii):
Problema: "Se considera functia f: R -> R, f(x) = 2x + 4. Reprezentati graficul functiei si calculati aria triunghiului format de grafic cu axele de coordonate."
Raspuns corect:
{{
  "tip_figura": ["graficul_functiei"],
  "puncte_principale": [],
  "puncte_mentionate": [],
  "laturi_mentionate": [],
  "laturi_date": {{}},
  "unghiuri_mentionate": [],
  "unghiuri_date": {{}},
  "proprietati_varfuri": {{}},
  "aria": null,
  "perimetru": null,
  "relatii_intre_laturi": [],
  "formula_functie": "2*x + 4",
  "tip_functie": "liniara",
  "domeniu_functie": "R",
  "codomeniu_functie": "R",
  "relatii_suplimentare": [
    {{
      "tip": "intersectie_axe",
      "nume_punct_nou": null,
      "elemente_vizate": [],
      "detalii": "Se cere triunghiul format de grafic cu axele Ox si Oy"
    }}
  ],
  "cerinte": ["Reprezinta graficul functiei", "Calculeaza aria triunghiului format de grafic cu axele de coordonate"]
}}
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
              Esti un asistent in matematica, geometrie plana si in spatiu.
              Rolul tau este sa analizezi o problema de geometrie in limba romana si sa extragi datele esentiale intr-un format structurat precis.
              
              REGULI IMPORTANTE:
              
              1. TIP FIGURA: Foloseste DOAR categoriile valide din schema. Daca problema descrie:
                - "triunghi dreptunghic in C" -> ['triunghi_dreptunghic'] + proprietati_varfuri={{'C': 'unghi_drept'}}
                - "triunghi inscris in cerc" -> ['triunghi_oarecare', 'inscris_in_cerc']
                - "cub ABCDA'B'C'D'" -> ['cub']
                - "prisma triunghiulara" -> ['prisma']
                - "punctele coliniare A, B, C, D" -> ['puncte_coliniare']
                - "graficul functiei f(x)=..." -> ['graficul_functiei']
              
              2. PROPRIETATI VARFURI: Mentionarea unui varf cu unghi drept, sau a centrului unui cerc, etc. ->
                pune in proprietati_varfuri. NU lasa aceste informatii sa se piarda doar in tip_figura.
              
              3. LATURI - VALORI vs RELATII:
                - Valoare directa "AB = 10 cm" -> laturi_date={{'AB': 10.0}}
                - Relatie "BD = 3*CD" -> relatii_intre_laturi=['BD = 3*CD']
                - Nu duplica: o latura cu valoare DIRECTA nu mai apare in relatii.
                - Relatii_intre_laturi sunt ALGEBRICE, nu inventa valori numerice.
              
              4. ARIE / PERIMETRU:
                - Doar daca sunt DATE EXPLICIT in problema (nu doar cerute).
                - "aria paralelogramului este 96" -> aria=96.0
                - "calculati aria" (fara valoare data) -> aria=null
              
              5. EXTRAGE doar valori care apar TEXTUAL in problema. NU inventa, NU presupune.

              6. FUNCTII: Daca problema implica o functie f(x) = ..., completeaza:
                  - formula_functie cu sintaxa GeoGebra (foloseste * explicit, ^ pentru puteri)
                  - tip_functie cu tipul (liniara, patratica, etc.)
                  - domeniu_functie si codomeniu_functie (default 'R' daca nu sunt specificate)
                  - tip_figura include 'graficul_functiei'
                  Pentru probleme de geometrie pura, lasa aceste campuri null.
              
              7. RELATII DERIVATE DIN CONSTRUCTII:
                  Cand identifici o relatie_suplimentara, adauga AUTOMAT in relatii_intre_laturi
                  sau relatii_intre_unghiuri urmatoarele relatii algebrice implicite:
                  
                  - 'mijloc' (M mijlocul lui BC): adauga in relatii_intre_laturi
                    ['BM = MC', 'BM = BC/2']
                  
                  - 'bisectoare' (OM bisectoarea COB): adauga in relatii_intre_unghiuri
                    ['COM = MOB', 'COM = COB/2']
                  
                  - 'inaltime' (AD inaltimea din A pe BC, D piciorul): adauga in relatii_intre_unghiuri
                    ['ADB = 90', 'ADC = 90'] si in relatii_intre_laturi ['BD + DC = BC']
                  
                  - 'punct_pe_latura' (E pe AB intre A si B): adauga in relatii_intre_laturi
                    ['AE + EB = AB']
                  
                  - 'mediana' (AM mediana din A pe BC): la fel ca mijlocul - in relatii_intre_laturi
                    ['BM = MC', 'BM = BC/2']
                  
                  IMPORTANT: NU dubla informatia! Daca problema da valoarea directa (ex: AM = 7),
                  pune-o in laturi_date, NU si in relatii_intre_laturi.
              
              Raspunde STRICT in formatul de mai jos, fara text explicativ:
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
Exemplul 1 (triunghi cu inaltime):
Date de intrare:
{{
  "tip_figura": ["triunghi_oarecare"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "D"],
  "laturi_mentionate": ["AB", "AC", "BC", "AD"],
  "laturi_date": {{"AB": 10.0, "AC": 8.0, "BC": 6.0}},
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": [
    {{"tip": "inaltime", "nume_punct_nou": "D", "elemente_vizate": ["BC"], "detalii": "AD este inaltimea din A pe latura BC"}}
  ],
  "cerinte": ["Calculeaza AD"]
}}

Raspuns corect:
["A = (0, 0)",
 "B = (10, 0)",
 "c_a = Circle(A, 8)",
 "c_b = Circle(B, 6)",
 "C = Intersect(c_a, c_b, 1)",
 "abc = Polygon(A, B, C)",
 "bc = Segment(B, C)",
 "h_line = PerpendicularLine(A, bc)",
 "D = Intersect(bc, h_line)",
 "ad = Segment(A, D)"]


Exemplul 2 (puncte pe laturi):
Date de intrare:
{{
  "tip_figura": ["triunghi_oarecare"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "E", "F"],
  "laturi_mentionate": ["AB", "AC", "BC", "BE", "AF", "EF"],
  "laturi_date": {{"AB": 24.0, "AC": 32.0, "BC": 36.0, "BE": 15.0, "AF": 12.0}},
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": [
    {{"tip": "punct_pe_latura", "nume_punct_nou": "E", "elemente_vizate": ["AB"], "detalii": "E pe AB"}},
    {{"tip": "punct_pe_latura", "nume_punct_nou": "F", "elemente_vizate": ["AC"], "detalii": "F pe AC"}}
  ],
  "cerinte": ["Calculeaza EF"]
}}

Mentiuni: Punct pe segment cu distanta cunoscuta -> Punct = Origine + (distanta/lungime_totala) * (Destinatie - Origine)

Raspuns corect:
["A = (0, 0)",
 "B = (24, 0)",
 "c_a = Circle(A, 32)",
 "c_b = Circle(B, 36)",
 "C = Intersect(c_a, c_b, 1)",
 "abc = Polygon(A, B, C)",
 "E = A + (9/24) * (B - A)",
 "F = A + (12/32) * (C - A)",
 "ef = Segment(E, F)"]


Exemplul 3 (triunghi isoscel cu mijloc):
Date de intrare:
{{
  "tip_figura": ["triunghi_isoscel"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C", "M"],
  "laturi_mentionate": ["AB", "AC", "BC", "AM"],
  "laturi_date": {{"AB": 13.0, "AC": 13.0, "BC": 10.0}},
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": [
    {{"tip": "mijloc", "nume_punct_nou": "M", "elemente_vizate": ["BC"], "detalii": "M mijlocul lui BC"}}
  ],
  "cerinte": ["Calculeaza AM"]
}}

Raspuns corect:
["A = (0, 0)",
 "B = (10, 0)",
 "c_a = Circle(A, 13)",
 "c_b = Circle(B, 13)",
 "C = Intersect(c_a, c_b, 1)",
 "abc = Polygon(A, B, C)",
 "bc = Segment(B, C)",
 "M = Midpoint(bc)",
 "am = Segment(A, M)"]


Exemplul 4 (paralelogram cu unghi dat):
Date de intrare:
{{
  "tip_figura": ["paralelogram"],
  "puncte_principale": ["A", "B", "C", "D"],
  "laturi_date": {{"AB": 6.0, "AD": 4.0}},
  "unghiuri_date": {{"DAB": 60.0}},
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": []
}}

Raspuns corect:
["A = (0, 0)",
 "B = (6, 0)",
 "D = (4; 60°)",
 "C = D + (B - A)",
 "p1 = Polygon(A, B, C, D)"]


Exemplul 5 (triunghi dreptunghic cu varf specificat):
Date de intrare:
{{
  "tip_figura": ["triunghi_dreptunghic"],
  "puncte_principale": ["A", "B", "C"],
  "puncte_mentionate": ["A", "B", "C"],
  "laturi_mentionate": ["AB", "BC", "AC"],
  "laturi_date": {{"AB": 12.0, "BC": 6.0}},
  "proprietati_varfuri": {{"C": "unghi_drept"}},
  "relatii_suplimentare": [],
  "cerinte": ["Calculati AC"]
}}

Mentiuni: Daca un varf are unghi drept, plaseaza-l in origine si pune catetele pe axe.
AB este ipotenuza (cea mai lunga, opusa unghiului drept). 
Daca BC e cateta cunoscuta, atunci AC = sqrt(AB^2 - BC^2) = sqrt(144 - 36) = sqrt(108).
Foloseste constructia cu cercuri si Intersect pentru a obtine pozitii corecte.

Raspuns corect:
["C = (0, 0)",
 "B = (6, 0)",
 "c_c = Circle(C, sqrt(108))",
 "perp = PerpendicularLine(C, xAxis)",
 "A = Intersect(c_c, perp, 1)",
 "abc = Polygon(A, B, C)"]


Exemplul 6 (paralelogram cu arie data):
Date de intrare:
{{
  "tip_figura": ["paralelogram"],
  "puncte_principale": ["A", "B", "C", "D"],
  "puncte_mentionate": ["A", "B", "C", "D"],
  "laturi_mentionate": ["AB"],
  "laturi_date": {{"AB": 12.0}},
  "aria": 96.0,
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": [],
  "cerinte": ["Calculati distanta de la D la AB"]
}}

Mentiuni: Pentru paralelogram, aria = baza * inaltime, deci inaltime = aria / AB = 96/12 = 8.
Construim cu un unghi non-90° (ex: 70°) ca sa nu para dreptunghi. AD se calculeaza din inaltime/sin(unghi).

Raspuns corect:
["A = (0, 0)",
 "B = (12, 0)",
 "inaltime = 8",
 "unghi = 70",
 "ad_lungime = inaltime / sin(unghi°)",
 "D = (ad_lungime; unghi°)",
 "C = D + (B - A)",
 "p1 = Polygon(A, B, C, D)"]


Exemplul 7 (cub 3D):
Date de intrare:
{{
  "tip_figura": ["cub"],
  "puncte_principale": ["A", "B", "C", "D", "A'", "B'", "C'", "D'"],
  "puncte_mentionate": ["A", "B", "C", "D", "A'", "B'", "C'", "D'", "M"],
  "laturi_mentionate": ["AB", "CC'", "AM"],
  "laturi_date": {{"AB": 8.0}},
  "proprietati_varfuri": {{}},
  "relatii_suplimentare": [
    {{"tip": "mijloc", "nume_punct_nou": "M", "elemente_vizate": ["CC'"], "detalii": "M mijlocul muchiei CC'"}}
  ],
  "cerinte": ["Calculati AM"]
}}

Mentiuni: Pentru figuri 3D foloseste comanda Cube(A, B, directie) sau construieste cu coordonate 3D.
Punctele cu apostrof (A') sunt scrise in GeoGebra ca A_1 sau cu indicii (verifica documentatia).
C nu trebuie precizat deoarece este creat din comanda Cube(D,A,B)

Raspuns corect:
["A = (0, 0, 0)",
 "B = (8, 0, 0)",
 "D = (0, 8, 0)",
 "cub1 = Cube(D,A,B)",
 "A_1=F",
 "B_1=G",
 "C_1=H",
 "D_1=E",
 "M = Midpoint(C, C_1)",
 "am = Segment(A, M)",
 "SetConditionToShowObject(F, false)",
 "SetConditionToShowObject(G, false)",
 "SetConditionToShowObject(H, false)",
 "SetConditionToShowObject(E, false)"]


Exemplul 8 (graficul unei functii liniare):
Date de intrare:
{{
  "tip_figura": ["graficul_functiei"],
  "puncte_principale": [],
  "puncte_mentionate": [],
  "laturi_mentionate": [],
  "laturi_date": {{}},
  "proprietati_varfuri": {{}},
  "formula_functie": "2*x + 4",
  "tip_functie": "liniara",
  "domeniu_functie": "R",
  "codomeniu_functie": "R",
  "relatii_suplimentare": [
    {{"tip": "intersectie_axe", "nume_punct_nou": null, "elemente_vizate": [], "detalii": "Triunghiul format de grafic cu axele"}}
  ],
  "cerinte": ["Reprezinta graficul", "Aria triunghiului cu axele"]
}}

Mentiuni: Pentru functii pe R, foloseste f(x) = ... direct. Pentru intersectie cu axele:
A = Intersect(f, xAxis), B = Intersect(f, yAxis). Triunghi cu axele: Polygon(O, A, B) unde O=(0,0).

Raspuns corect:
["f(x) = 2*x + 4",
 "O = (0, 0)",
 "A = Intersect(f, xAxis)",
 "B = Intersect(f, yAxis)",
 "triunghi = Polygon(O, A, B)"]
""".strip()
    
def genereaza_comenzi_geogebra(date_problema, text_problema):
        # Copie a datelor ca sa nu modificam originalul
    date_problema = dict(date_problema)
    
    # PREPROCESARE 1: Rezolvam relatiile algebrice intre laturi
    laturi_complete = dict(date_problema.get("laturi_date", {}))
    if date_problema.get("relatii_intre_laturi"):
        laturi_complete = rezolva_relatii_laturi(
            laturi_complete,
            date_problema["relatii_intre_laturi"]
        )
        date_problema["laturi_date"] = laturi_complete
    
    # PREPROCESARE 2: Rezolvam relatiile algebrice intre unghiuri
    unghiuri_complete = dict(date_problema.get("unghiuri_date", {}))
    if date_problema.get("relatii_intre_unghiuri"):
        unghiuri_complete = rezolva_relatii_unghiuri(
            unghiuri_complete,
            date_problema["relatii_intre_unghiuri"]
        )
        date_problema["unghiuri_date"] = unghiuri_complete
    
    llm = ChatAnthropic(model="claude-opus-4-8")
    parser = PydanticOutputParser(pydantic_object=ComenziGeogebra)

    prompt = ChatPromptTemplate.from_messages([
          ("system",""" 
              Primesti un JSON cu datele unei probleme de matematica.
              Rolul tau este sa generezi EXACT comenzile GeoGebra necesare pentru a desena figura/graficul.
              
              REGULI GENERALE:
              1. Primul punct se pune in origine: P1 = (0, 0).
              2. Construieste baza inteligent (ex: daca ai latura AB de 5, pune A=(0,0), B=(5,0)).
              3. Foloseste comenzi declarative cand laturile sunt date (ex: cercuri + Intersect),
                NU hardcoda coordonate pentru toate punctele.
              4. NUMIRE STRICTA:
                - Puncte: MAJUSCULE (A, C, P, M)
                - Segmente, drepte, cercuri, raze: litere mici (ab, oc, h_line)
                - Ex CORECT: ac = Segment(A, C). GRESIT: AC = Segment(A, C).
              
              REGULI PENTRU CAMPURI SPECIFICE:
              
              5. proprietati_varfuri: Indica varfuri cu proprietati speciale.
                - {{'C': 'unghi_drept'}} -> construieste triunghi dreptunghic cu unghi drept in C.
                  Pune C in origine, una din catete pe Ox (ex: C=(0,0), B pe Ox, A pe Oy).
                - {{'O': 'centru_cerc'}} -> O este centrul cercului.
                - {{'O': 'varf_unghi'}} -> O este varful unui unghi.
              
              6. aria / perimetru: Daca sunt date, foloseste-le pentru a determina dimensiuni necunoscute.
                Ex: paralelogram cu AB=12 si aria=96 -> inaltimea = 96/12 = 8.
              
              7. tip_figura este o LISTA (poate avea mai multe categorii):
                - ['triunghi_oarecare', 'inscris_in_cerc'] -> deseneaza triunghiul si cercul circumscris.
                - ['cub'] -> foloseste comanda Cube(A, B, C) sau construieste cu 8 puncte.
                - ['graficul_functiei'] -> foloseste formula_functie cu comanda f(x) = ...
              
              8. FUNCTII: Daca tip_figura contine 'graficul_functiei':
                - Foloseste DIRECT formula_functie ca o comanda GeoGebra: f(x) = <formula_functie>
                - Daca domeniu_functie e specific (ex: '[0, 5]'), foloseste Function(formula, a, b).
                - Pentru cerinte gen "intersectia cu axele", foloseste comenzi precum:
                  A = Intersect(f, xAxis), B = Intersect(f, yAxis).
              
              9. relatii_intre_laturi: Daca apar in input, IGNORA-LE - sunt deja rezolvate
                  in laturi_date (vei vedea valorile finale acolo).
              
              Returneaza STRICT in formatul JSON cerut:
              \n{format_instructions}
              EXEMPLE REZOLVATE (urmeaza acelasi pattern):{few_shot_cod}
              """
          ),
          ("human","Enuntul original:\n{text_problema}\n\nDatele problemei:\n{date_json}")
      ]).partial(format_instructions=parser.get_format_instructions(), few_shot_cod=FEW_SHOT_EXAMPLES_COD)

    chain = prompt | llm | parser

    try:
        rezultat_structurat = chain.invoke({"date_json": json.dumps(date_problema), "text_problema":text_problema})
        return {
            "comenzi": rezultat_structurat.comenzi,
            "laturi_date_complete": laturi_complete,
            "unghiuri_date_complete": unghiuri_complete,
            
        }
    except Exception as e:
        print(f"Eroare la ai: {e}")
        return None
    

def repara_comenzi_geogebra(date_problema, cod_anterior, raport_executie=None, raport_imprecizii=None):
    """
    Repara comenzi GeoGebra. Poate primi:
    - raport_executie: pentru erori de executie (comenzi care au esuat)
    - raport_imprecizii: pentru imprecizii matematice (lungimi/unghiuri gresite)
    Exact UNUL trebuie sa fie furnizat.
    """
    llm = ChatAnthropic(model="claude-opus-4-8")
    parser = PydanticOutputParser(pydantic_object=ComenziReparate)
    
    # Construim sectiunea de raport in functie de tipul de eroare
    if raport_executie:
        raport_text = "TIP RAPORT: Erori de executie GeoGebra\n\n"
        for i, item in enumerate(raport_executie["comenzi"], start=1):
            if item["succes"]:
                raport_text += f"Linia {i}: {item['comanda']} → OK\n"
            else:
                eroare = item.get("eroare") or "necunoscuta"
                raport_text += f"Linia {i}: {item['comanda']} → EROARE: {eroare}\n"
        instructiuni_specifice = (
            "- Analizeaza fiecare comanda care a esuat si identifica cauza\n"
            "- Pastreaza comenzile care au reusit, doar daca raman valide in contextul reparat"
        )
    elif raport_imprecizii:
        raport_text = "TIP RAPORT: Imprecizii matematice\n\n"
        raport_text += "Comenzile au rulat fara erori, DAR figura desenata nu respecta datele problemei.\n\n"
        raport_text += "LUNGIMI INCORECTE:\n"
        for masuratoare in raport_imprecizii["masuratori"]["laturi"]:
            if not masuratoare["valid"]:
                raport_text += (
                    f"- {masuratoare['latura']}: ar trebui sa fie {masuratoare['asteptat']}, "
                    f"dar e {masuratoare['real']:.4f} (diferenta: {masuratoare['diferenta']:.4f})\n"
                )
        if raport_imprecizii["masuratori"]["unghiuri"]:
            raport_text += "\nUNGHIURI INCORECTE:\n"
            for masuratoare in raport_imprecizii["masuratori"]["unghiuri"]:
                if not masuratoare["valid"]:
                    raport_text += (
                        f"- {masuratoare['unghi']}: ar trebui sa fie {masuratoare['asteptat']}°, "
                        f"dar e {masuratoare['real']:.4f}° (diferenta: {masuratoare['diferenta']:.4f})\n"
                    )
        instructiuni_specifice = (
            "- Identifica DE CE figura nu respecta lungimile/unghiurile cerute\n"
            "- Cauze frecvente: sintaxa amestecata (cartezian (x,y) vs polar (r;u°)), "
            "calcul gresit al coordonatelor, confuzii intre grade si radiani\n"
            "- Reconstruieste figura folosind METODA cea mai sigura: cercuri cu raze date + Intersect, "
            "sau coordonate polare cu notatia (raza; unghi°)"
        )
    else:
        return None  # nu avem ce repara
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Rolul tau este sa repari comenzi GeoGebra.
            
            Ai primit:
            1. Datele unei probleme de geometrie/matematica
            2. Codul GeoGebra generat anterior
            3. Un raport care arata de ce codul nu e corect
            
            Sarcina ta:
            {instructiuni_specifice}
            - Returneaza INTREG codul reparat, in ordine logica
            - Pentru fiecare linie indica daca a fost schimbata (schimbat=true/false)
            - Pentru liniile schimbate adauga o explicatie scurta in romana
            
            Reguli GeoGebra importante:
            - Punctele au nume cu MAJUSCULE (A, B, C, M, N)
            - Segmentele, dreptele, cercurile au nume cu litere mici
            - (x, y) = coordonate carteziene
            - (r; u°) = coordonate polare (raza; unghi in GRADE cu simbolul °)
            - sin/cos/arcsin folosesc RADIANI implicit; pentru grade adauga °
            - Pentru triunghi cu laturi cunoscute, foloseste cercuri si Intersect (cel mai sigur)
            
            Raspunde STRICT in formatul JSON cerut:
            \n{format_instructions}
            """
        ),
        ("human", """
            Datele problemei:
            {date_problema}
            
            Codul anterior generat:
            {cod_anterior}
            
            Raportul:
            {raport_text}
            
            Repara codul.
            """
        )
    ]).partial(
        format_instructions=parser.get_format_instructions(),
        instructiuni_specifice=instructiuni_specifice
    )
    
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
    
def rezolva_relatii_laturi(laturi_date: dict, relatii: List[str]) -> dict:
    """
    Calculeaza valorile derivate din relatii algebrice.
    Ex: laturi_date={'CD': 3}, relatii=['BD = 3*CD', 'AD = 3*BD']
    Returneaza: {'CD': 3, 'BD': 9, 'AD': 27}
    """
    cunoscute = dict(laturi_date)
    for relatie in relatii:
        try:
            rezultat, expresie = relatie.split("=")
            rezultat = rezultat.strip()
            expresie = expresie.strip()
            valoare = float(sympify(expresie).subs(cunoscute))
            cunoscute[rezultat] = valoare
        except Exception as e:
            print(f"Eroare la rezolvarea relatiei '{relatie}': {e}")
    return cunoscute


def rezolva_relatii_unghiuri(unghiuri_date: dict, relatii: List[str]) -> dict:
    """
    Calculeaza valorile derivate din relatii intre unghiuri.
    Format relatii poate fi:
    - 'rezultat = expresie' (ex: 'A = 2*B')
    - 'unghi1 + unghi2 = constanta' (ex: 'AOC + COB = 180' - suplementare/complementare)
    """
    from sympy import sympify, Symbol, solve
    
    cunoscute = dict(unghiuri_date)
    
    for relatie in relatii:
        try:
            if "=" not in relatie:
                print(f"Relatie invalida (lipseste '='): {relatie}")
                continue
            
            stanga, dreapta = relatie.split("=", 1)
            stanga = stanga.strip()
            dreapta = dreapta.strip()
            
            # Cazul 1: stanga e un singur unghi (gen "A = 2*B")
            # Verificam daca stanga e doar un identificator simplu
            if stanga.replace("'", "").isalnum() and stanga not in cunoscute:
                # Putem incerca sa substituim cunoscutele in dreapta si sa obtinem valoarea
                expresie = sympify(dreapta)
                try:
                    valoare = float(expresie.subs(cunoscute))
                    cunoscute[stanga] = valoare
                    continue
                except (TypeError, ValueError):
                    pass  # cad in cazul 2
            
            # Cazul 2: ecuatie cu o singura necunoscuta (gen "AOC + COB = 180")
            # Construim ecuatia: stanga - dreapta = 0
            ecuatie = sympify(stanga) - sympify(dreapta)
            
            # Substituim ce stim
            ecuatie_substituita = ecuatie.subs(cunoscute)
            
            # Gasim ce simbol a ramas necunoscut
            necunoscute = ecuatie_substituita.free_symbols
            
            if len(necunoscute) == 1:
                necunoscuta = list(necunoscute)[0]
                solutii = solve(ecuatie_substituita, necunoscuta)
                if solutii:
                    cunoscute[str(necunoscuta)] = float(solutii[0])
            elif len(necunoscute) == 0:
                # Toate cunoscute - relatie de verificare, ignoram
                pass
            else:
                print(f"Relatia '{relatie}' are {len(necunoscute)} necunoscute, nu pot rezolva")
                
        except Exception as e:
            print(f"Eroare la rezolvarea relatiei '{relatie}': {e}")
    
    return cunoscute
