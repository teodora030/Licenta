from ai_agent import scoate_datele_problemei, genereaza_comenzi_geogebra, repara_comenzi_geogebra
from categorii import CATEGORII

from flask import Flask, render_template, request, url_for, redirect, make_response, g, jsonify
from flask_scss import Scss
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
import jwt
from datetime import datetime,timezone,timedelta
import os
import smtplib
import ssl
import secrets
import re
from itsdangerous import URLSafeTimedSerializer,SignatureExpired, BadSignature

load_dotenv()

app = Flask(__name__)

Scss(app)

MONGODB_URI = os.getenv('MONGODB_URI')
SECRET_KEY = os.getenv('SECRET_KEY')

app.config['SECRET_KEY'] = SECRET_KEY

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db=client['geom']
problems_collection = db['problems']
users_collection = db['utilizatori']

try:
    client.admin.command('ping')
    print("Conectat la MongoDB cu succes!")
    print(f"Colectii: {db.list_collection_names()}")
    users_collection.create_index('email',unique=True)
    users_collection.create_index('username',unique=True)
    print("Am creat indexuri pentru email si username")
except Exception as e:
    print(f"NU m-am putut conecta la MongoDB: {e}")
    print("Aplicatia va incerca sa se reconecteze la fiecare request.")

app.config["MAIL_SERVER"] = os.environ["MAIL_SERVER"]
app.config["MAIL_PORT"] = int(os.environ["MAIL_PORT"])
app.config["MAIL_USERNAME"] = os.environ["MAIL_USERNAME"]
app.config["MAIL_PASSWORD"] = os.environ["MAIL_PASSWORD"]
app.config["MAIL_USE_TLS"] = os.environ["MAIL_USE_TLS"] == "True"
app.config["MAIL_DEFAULT_SENDER"] = os.environ["MAIL_DEFAULT_SENDER"]
app.config["SECRET_KEY_2"]=os.environ["SECRET_KEY_2"]
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY_2"])

def email_valid(email):
    if not email or not isinstance(email,str):
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9._%+-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern,email) is not None

def trimite_email(destinatar, subiect, continut_text, continut_html=None):
    """
    Trimite un email folosind smtplib direct.
    Returneaza (True, None) la succes sau (False, mesaj_eroare) la esec.
    """
    expeditor = os.environ["MAIL_USERNAME"]
    parola = os.environ["MAIL_PASSWORD"].replace(" ", "")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subiect
    msg["From"] = expeditor
    msg["To"] = destinatar
    
    # versiune text (fallback)
    msg.attach(MIMEText(continut_text, "plain"))
    
    # versiune HTML (preferată, dacă există)
    if continut_html:
        msg.attach(MIMEText(continut_html, "html"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(expeditor, parola)
            server.sendmail(expeditor, destinatar, msg.as_string())
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = request.cookies.get('jwt_token')

        if not token:
            return redirect(url_for('login', eroare="Trebuie să te loghezi pentru a accesa pagina!"))
        
        try:
            date_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            g.user_id=date_token['user_id']
            
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login', eroare="Sesiunea a expirat. Te rugăm să te loghezi din nou."))
        except jwt.InvalidTokenError:
            return redirect(url_for('login', eroare="Token invalid!"))

        return f(*args, **kwargs)
    return decorated

@app.before_request
def verifica_db():
    try:
        client.admin.command('ping')
    except Exception:
        return render_template("eroare_db.html"),503

@app.route("/")
@token_required
def index():

    toate_problemele = list(problems_collection.find({"user_id": ObjectId(g.user_id)}).sort("_id", -1))

    return render_template("index.html",probleme=toate_problemele)

@app.route("/api/categorii")
def get_categorii():
    return jsonify(CATEGORII)

@app.route("/adauga_problema", methods=['GET','POST'])
@token_required
def adauga_problema():

    if request.method =='POST':
        text_problema = request.form.get("text_problema")
        clasa = request.form.get("clasa")
        subcapitol = request.form.get("subcapitol")
        tip_figura = request.form.get("tip_aplicatie")

        document_problema = {
            "versiuni_text": [text_problema],
            "user_id": ObjectId(g.user_id),
            "date_ai":[None],
            "cod_geogebra":[""],
            "raport_erori_ggb": [[]],
            "clasa":clasa,
            "subcapitol":subcapitol,
            "tip_figura":tip_figura
        }

        rezultat = problems_collection.insert_one(document_problema)
        id_nou=rezultat.inserted_id

        return redirect(url_for('vizualizeaza_problema',id_problema=str(id_nou) , mesaj="Problema noua creata",auto_genereaza=1))
    
    return render_template("adauga_problema.html")
    

@app.route("/vizualizeaza_problema/<id_problema>")
@token_required
def vizualizeaza_problema(id_problema):
    problema_gasita = problems_collection.find_one({"_id": ObjectId(id_problema), "user_id": ObjectId(g.user_id)})

    mesaj_din_url =  request.args.get('mesaj')
    
    return render_template("vizualizeaza_problema.html",problema=problema_gasita,mesaj=mesaj_din_url)

@app.route("/editeaza_problema/<id_problema>",methods=['POST'])
@token_required
def editeaza_problema(id_problema):
    text_nou = request.form.get("text_problema","")
    text_nou_curatat = text_nou.strip()

    problema_curenta = problems_collection.find_one({"_id": ObjectId(id_problema),"user_id": ObjectId(g.user_id)})

    exista_deja =  any(versiune.strip() == text_nou_curatat for versiune in problema_curenta.get("versiuni_text",[]))

    if exista_deja:
        return redirect(url_for('vizualizeaza_problema', id_problema=id_problema, mesaj="Aceasta versiune a problemei exista deja."))
    else:
        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$push": {"versiuni_text": text_nou_curatat}}
        )
        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$push": {"date_ai":None}}
        )
        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$push": {"cod_geogebra": ""}}
        )
        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$push": {"raport_erori_ggb": []}}
        )

    return redirect(url_for('vizualizeaza_problema',id_problema=id_problema, mesaj="Versiune noua salvata.",auto_genereaza=1))

@app.route("/sterge_versiune/<id_problema>", methods=['POST'])
@token_required
def sterge_versiune(id_problema):
    data = request.get_json()
    index_de_sters = int(data.get('index'))

    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema),
        "user_id": ObjectId(g.user_id)
    })

    if not problema:
        return jsonify({"status": "eroare", "mesaj": "Problema nu a fost gasita"}), 404
    
    versiuni = problema.get("versiuni_text",[])

    #daca e singura versiune
    if len(versiuni) <= 1:
        problems_collection.delete_one({"_id": ObjectId(id_problema)})
        return jsonify({"status": "succes", "redirect": url_for('index')})
    
    #daca sunt mai multe versiuni
    versiuni.pop(index_de_sters)

    update_data = {"versiuni_text": versiuni}

        #stergem si datele problemei extrase si codul geogebra generat
    if "date_ai" in problema:
        date_ai = problema["date_ai"]
        if index_de_sters < len(date_ai):
            date_ai.pop(index_de_sters)
        update_data["date_ai"]=date_ai

    if "cod_geogebra" in problema:
        cod_ggb = problema["cod_geogebra"]

        if isinstance(cod_ggb,list) and index_de_sters<len(cod_ggb):
            cod_ggb.pop(index_de_sters)
            update_data["cod_geogebra"]=cod_ggb

    if "raport_erori_ggb" in problema:
        raport_erori = problema["raport_erori_ggb"]

        if isinstance(raport_erori, list) and index_de_sters < len(raport_erori):
            raport_erori.pop(index_de_sters)
            update_data["raport_erori_ggb"] = raport_erori

    #facem update la problema
    problems_collection.update_one(
        {"_id": ObjectId(id_problema)},
        {"$set": update_data}
    )

    return jsonify({"status":"succes","redirect":url_for('vizualizeaza_problema',id_problema=id_problema)})

@app.route("/api/extrage_date/<id_problema>", methods=['POST'])
@token_required
def api_extrage_date(id_problema):

    date_primite=request.get_json()
    index_versiune=date_primite.get('index')

    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema), 
        "user_id": ObjectId(g.user_id)
    })

    if not problema or not problema.get("versiuni_text"):
        return jsonify({"eroare": "Problema nu a fost găsită"}), 404
    
    text_curent = problema["versiuni_text"][index_versiune]

    date_extrase = scoate_datele_problemei(text_curent)

    if date_extrase:

        lista_date_ai = problema.get("date_ai", [None]*len(problema["versiuni_text"]))

        while len(lista_date_ai) < len(problema["versiuni_text"]):
            lista_date_ai.append(None)

        lista_date_ai[index_versiune] = date_extrase

        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$set": {"date_ai": lista_date_ai}}
        )

        return jsonify({"status": "succes", "date": date_extrase})
    else:
        return jsonify({"status": "eroare", "mesaj": "AI-ul nu a putut procesa problema."}), 500

@app.route("/api/genereaza_figura/<id_problema>",methods=["POST"])
@token_required
def api_genereaza_figura(id_problema):
    date_primite = request.get_json()
    index_versiune = date_primite.get('index')

    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema),
        "user_id": ObjectId(g.user_id)
    })

    if not problema or "date_ai" not in problema:
        return jsonify({"eroare": "Nu exista date extrase. Apasa Extrage Date mai intai"}),400
    
    date_curente = problema["date_ai"][index_versiune]

    if not date_curente:
        return jsonify({"eroare": "Nu exista date extrase pentru aceasta versiune"}),400
    
    rezultat = genereaza_comenzi_geogebra(date_curente, problema["versiuni_text"][index_versiune])

    if rezultat:
        lista_comenzi = rezultat["comenzi"]
        laturi_complete = rezultat["laturi_date_complete"]
        unghiuri_complete = rezultat["unghiuri_date_complete"]
        
        problems_collection.update_one(
            {"_id": ObjectId(id_problema)},
            {"$set": {
                f"cod_geogebra.{index_versiune}": "\n".join(lista_comenzi),
                f"date_ai.{index_versiune}.laturi_date_complete": laturi_complete,
                f"date_ai.{index_versiune}.unghiuri_date_complete": unghiuri_complete
            }}
        )
        return jsonify({
            "status": "succes", 
            "comenzi": lista_comenzi,
            "laturi_date_complete": laturi_complete,
            "unghiuri_date_complete": unghiuri_complete
        })
    else:
        return jsonify({"status": "eroare", "mesaj": "Ai-ul nu a putut genera codul Geogebra"}), 500

@app.route("/api/salveaza_cod_ggb/<id_problema>",methods=['POST'])
@token_required
def api_salveaza_cod_ggb(id_problema):
    date=request.get_json()
    index_versiune=date.get('index')
    cod_nou=date.get('cod')

    problems_collection.update_one(
        {"_id":ObjectId(id_problema)},
        {"$set":{f"cod_geogebra.{index_versiune}": cod_nou}}
    )
    return jsonify({"status":"succes"})

@app.route("/api/salveaza_raport_erori/<id_problema>", methods=['POST'])
@token_required
def api_salveaza_raport_erori(id_problema):
    date = request.get_json()
    index_versiune = date.get('index')
    raport = date.get('raport')

    # Asiguram ca documentul are campul raport_erori_ggb si ca e suficient de lung
    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema),
        "user_id": ObjectId(g.user_id)
    })

    if not problema:
        return jsonify({"status": "eroare", "mesaj": "Problema nu a fost gasita"}), 404

    # Daca campul nu exista sau e prea scurt, il extindem
    raport_erori = problema.get("raport_erori_ggb", [])
    while len(raport_erori) <= index_versiune:
        raport_erori.append([])
    
    # Adaugam raportul nou in istoric la pozitia versiunii
    raport_erori[index_versiune].append(raport)

    # Salvam in MongoDB
    problems_collection.update_one(
        {"_id": ObjectId(id_problema)},
        {"$set": {"raport_erori_ggb": raport_erori}}
    )

    return jsonify({"status": "succes"})

@app.route("/api/repara_cod_ggb/<id_problema>", methods=['POST'])
@token_required
def api_repara_cod_ggb(id_problema):
    date = request.get_json()
    index_versiune = date.get('index')
    tip_raport = date.get('tip_raport', 'executie')  # default executie

    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema),
        "user_id": ObjectId(g.user_id)
    })

    if not problema:
        return jsonify({"status": "eroare", "mesaj": "Problema nu a fost gasita"}), 404

    cod_geogebra_list = problema.get("cod_geogebra", [])
    if index_versiune >= len(cod_geogebra_list) or not cod_geogebra_list[index_versiune]:
        return jsonify({"status": "eroare", "mesaj": "Nu exista cod GeoGebra pentru aceasta versiune"}), 400
    cod_anterior = cod_geogebra_list[index_versiune]

    date_problema = problema.get("date_ai", [])[index_versiune] if index_versiune < len(problema.get("date_ai", [])) else {}

    # Alegem raportul potrivit
    raport_executie = None
    raport_imprecizii = None
    
    if tip_raport == 'executie':
        rapoarte = problema.get("raport_erori_ggb", [])
        if index_versiune >= len(rapoarte) or not rapoarte[index_versiune]:
            return jsonify({"status": "eroare", "mesaj": "Nu exista raport de erori"}), 400
        raport_executie = rapoarte[index_versiune][-1]
    elif tip_raport == 'imprecizii':
        rapoarte = problema.get("raport_imprecizii_ggb", [])
        if index_versiune >= len(rapoarte) or not rapoarte[index_versiune]:
            return jsonify({"status": "eroare", "mesaj": "Nu exista raport de imprecizii"}), 400
        raport_imprecizii = rapoarte[index_versiune][-1]
    else:
        return jsonify({"status": "eroare", "mesaj": f"Tip raport necunoscut: {tip_raport}"}), 400

    rezultat = repara_comenzi_geogebra(
        date_problema, 
        cod_anterior, 
        raport_executie=raport_executie,
        raport_imprecizii=raport_imprecizii
    )
    
    if rezultat is None:
        return jsonify({"status": "eroare", "mesaj": "Eroare la apelul AI"}), 500

    return jsonify({
        "status": "succes",
        "comenzi": rezultat["comenzi"]
    })

@app.route("/api/salveaza_raport_imprecizii/<id_problema>", methods=['POST'])
@token_required
def api_salveaza_raport_imprecizii(id_problema):
    date = request.get_json()
    index_versiune = date.get('index')
    raport = date.get('raport')

    problema = problems_collection.find_one({
        "_id": ObjectId(id_problema),
        "user_id": ObjectId(g.user_id)
    })

    if not problema:
        return jsonify({"status": "eroare", "mesaj": "Problema nu a fost gasita"}), 404

    # Asiguram ca documentul are campul raport_imprecizii_ggb si ca e suficient de lung
    raport_imprecizii = problema.get("raport_imprecizii_ggb", [])
    while len(raport_imprecizii) <= index_versiune:
        raport_imprecizii.append([])
    
    raport_imprecizii[index_versiune].append(raport)

    problems_collection.update_one(
        {"_id": ObjectId(id_problema)},
        {"$set": {"raport_imprecizii_ggb": raport_imprecizii}}
    )

    return jsonify({"status": "succes"})


@app.route("/api/actualizeaza_categorii/<id_problema>",methods=["POST"])
@token_required
def actualizeaza_categorii(id_problema):
    data = request.get_json()
    clasa = data.get("clasa")
    subcapitol = data.get("subcapitol")
    
    # validare
    if clasa not in CATEGORII:
        return jsonify({"status": "eroare", "mesaj": "Clasă invalidă"}), 400
    if subcapitol not in CATEGORII[clasa]:
        return jsonify({"status": "eroare", "mesaj": "Subcapitol invalid"}), 400
    
    db.problems.update_one(
        {"_id": ObjectId(id_problema)},
        {"$set": {"clasa": clasa, "subcapitol": subcapitol}}
    )
    
    return jsonify({"status": "succes", "clasa": clasa, "subcapitol": subcapitol})

@app.route("/signup", methods=['GET','POST'])
def signup():
    if request.method=='POST':
        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip().lower()
        parola_clara = request.form.get("password","")
        parola_confirmare = request.form.get("password_confirm","")

        prenume = request.form.get("prenume")
        nume_familie=request.form.get("nume_familie")
        clasa = request.form.get("clasa","")

        if not username or not email or not parola_clara:
            return render_template("signup.html", eroare="Toate câmpurile obligatorii sunt necesare")
        
        if len(parola_clara) < 8:
            return render_template("signup.html", eroare="Parola trebuie să aibă minim 8 caractere")
        if parola_clara != parola_confirmare:
            return render_template("signup.html", eroare="Parolele nu se potrivesc")
        
        if not email_valid(email):
            return render_template("signup.html", eroare="Format email invalid")
        
        if users_collection.find_one({"email":email}):
            return render_template("signup.html", eroare="Email deja inregistrat")
        
        if users_collection.find_one({"username":username}):
            return render_template("signup.html", eroare="Username deja folosit")

        parola_criptata = bcrypt.hashpw(parola_clara.encode('utf-8'), bcrypt.gensalt())



        utilizator_nou = {
            "username": username,
            "email": email,
            "parola": parola_criptata,
            "activ": True,
            "clasa":clasa,
            "data_creare":datetime.now(timezone.utc),
            "email_confirmat":False,
            "full_name": {
                "prenume":prenume,
                "nume_familie":nume_familie
            },
            "rol":"elev",
            "ultima_logare":None,
            "data_modificare":None
        }
        try:
            users_collection.insert_one(utilizator_nou)
            token = serializer.dumps(email, salt="confirmare-email")
            link = f"{os.environ['APP_URL']}/confirma_email/{token}"
            
            trimite_email(
                destinatar=email,
                subiect="Confirmă-ți contul GeoTutor",
                continut_text=f"Salut! Confirmă contul aici: {link}",
                continut_html=f'<p>Salut! Confirmă contul <a href="{link}">apăsând aici</a>.</p>'
            )
            
            return redirect(url_for('login', mesaj="Cont creat! Verifică email-ul pentru confirmare."))
        except DuplicateKeyError:
            return render_template("signup.html", eroare="Email sau username deja folosit")
        except Exception as e:
            print(f"Eroare neașteptată: {type(e).__name__}: {e}")
            return render_template("signup.html", eroare="A aparut o eroare. Te rog reincearca!")
    
    return render_template("signup.html")

@app.route("/login", methods=['GET','POST'])
def login():

    if request.method=='POST':
        email_introdus = request.form.get("email","").strip().lower()
        parola_introdusa = request.form.get("password","")

        if not email_introdus or not parola_introdusa:
            return render_template("login.html", eroare="Completează toate câmpurile")

        utilizator_gasit = users_collection.find_one({"email": email_introdus})

        mesaj_credentiale = "Email sau parolă incorecte"

        if not utilizator_gasit:
            return render_template("login.html", eroare=mesaj_credentiale)
        
        if not bcrypt.checkpw(parola_introdusa.encode('utf-8'), utilizator_gasit['parola']):
            return render_template("login.html", eroare=mesaj_credentiale)
        
        if not utilizator_gasit.get('activ', True):
            return render_template("login.html", eroare="Contul tău este dezactivat. Contactează administratorul.")

        if not utilizator_gasit.get('email_confirmat', False):
            return render_template("login.html", eroare="Trebuie să-ți confirmi email-ul înainte de a te loga.",afiseaza_retrimite=True,email=email_introdus)
        
       
        token = jwt.encode({'user_id': str(utilizator_gasit['_id']),'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm='HS256')

        users_collection.update_one(
            {"_id": utilizator_gasit['_id']},
            {"$set": {"ultima_logare": datetime.now(timezone.utc)}}
        )

        raspuns = make_response(redirect(url_for('index')))
        raspuns.set_cookie(
            'jwt_token', 
            token, 
            httponly=True,
            samesite='Lax',
            max_age=86400  # 24h în secunde
        )
        return raspuns

    mesaj_succes = request.args.get("mesaj")
    return render_template("login.html", mesaj=mesaj_succes)    


@app.route("/logout")
def logout():
    raspuns = make_response(redirect(url_for('login',mesaj="Te-ai deconectat")))
    raspuns.delete_cookie('jwt_token')

    return raspuns

@app.route("/confirma_email/<token>")
def confirma_email(token):
    try:
        email = serializer.loads(token, salt="confirmare-email", max_age=86400)
    except SignatureExpired:
        return "Linkul a expirat. Te rog cere unul nou."
    except BadSignature:
        return "Link invalid."
    
    users_collection.update_one(
        {"email": email},
        {"$set": {"email_confirmat": True}}
    )
    
    return redirect(url_for("login", mesaj="Email confirmat! Te poți loga acum."))

@app.route("/retrimite_confirmare", methods=["POST"])
def retrimite_confirmare():
    email = request.form.get("email", "").strip().lower()
    user = users_collection.find_one({"email": email})
    
    # mesaj generic indiferent dacă userul există sau nu (securitate)
    mesaj_generic = "Dacă există un cont cu această adresă, vei primi un email."
    
    if not user or user.get("email_confirmat"):
        return render_template("verifica_email.html", mesaj=mesaj_generic)
    
    token = serializer.dumps(email, salt="confirmare-email")
    link = f"{os.environ['APP_URL']}/confirma_email/{token}"
    
    trimite_email(
        destinatar=email,
        subiect="Confirmă-ți contul GeoTutor",
        continut_text=f"Linkul tău de confirmare: {link}",
        continut_html=f'<a href="{link}">Confirmă email-ul</a>'
    )
    
    return render_template("verifica_email.html", mesaj=mesaj_generic)

@app.route("/am_uitat_parola", methods=["GET", "POST"])
def am_uitat_parola():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        mesaj_generic = "Dacă există un cont cu această adresă, vei primi un email."
        
        utilizator = users_collection.find_one({"email": email})
        
        # trimitem email DOAR dacă userul există și e activ + confirmat
        if utilizator and utilizator.get("activ", True) and utilizator.get("email_confirmat"):
            token = serializer.dumps(email, salt="resetare-parola")
            link = f"{os.environ['APP_URL']}/reseteaza_parola/{token}"
            
            trimite_email(
                destinatar=email,
                subiect="Resetare parolă GeoTutor",
                continut_text=f"Resetează parola aici: {link}\n\nLinkul expiră în 1 oră.",
                continut_html=f'<p><a href="{link}">Resetează parola</a></p><p>Linkul expiră în 1 oră.</p>'
            )
        
        # mesaj generic indiferent de rezultat (securitate)
        return render_template("am_uitat_parola.html", mesaj=mesaj_generic)
    
    return render_template("am_uitat_parola.html")

@app.route("/reseteaza_parola/<token>", methods=["GET", "POST"])
def reseteaza_parola(token):
    try:
        email = serializer.loads(token, salt="resetare-parola", max_age=3600)
    except SignatureExpired:
        return "Linkul a expirat. Cere unul nou."
    except BadSignature:
        return "Link invalid."
    
    if request.method == "POST":
        parola_noua = request.form.get("parola_noua", "")
        parola_confirmare = request.form.get("parola_confirmare", "")
        
        if len(parola_noua) < 8:
            return render_template("reseteaza_parola.html", token=token,
                                   eroare="Parola trebuie să aibă minim 8 caractere")
        
        if parola_noua != parola_confirmare:
            return render_template("reseteaza_parola.html", token=token,
                                   eroare="Parolele nu se potrivesc")
        
        parola_hash = bcrypt.hashpw(parola_noua.encode("utf-8"), bcrypt.gensalt())
        
        users_collection.update_one(
            {"email": email},
            {"$set": {
                "parola": parola_hash,
                "data_modificare": datetime.now(timezone.utc)
            }}
        )
        
        return redirect(url_for("login", mesaj="Parola a fost resetată! Te poți loga acum."))
    
    return render_template("reseteaza_parola.html", token=token)




if __name__ in "__main__":
    app.run(debug=True)