from ai_agent import scoate_datele_problemei, genereaza_comenzi_geogebra

from flask import Flask, render_template, request, url_for, redirect, make_response, g, jsonify
from flask_scss import Scss
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
import bcrypt
import jwt
import datetime
import os
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
    problems_collection = None
    users_collection = None

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

    toate_problemele = list(problems_collection.find({"user_id": ObjectId(g.user_id)}))

    return render_template("index.html",probleme=toate_problemele)

@app.route("/adauga_problema", methods=['GET','POST'])
@token_required
def adauga_problema():

    if request.method =='POST':
        text_problema = request.form.get("text_problema")

        document_problema = {
            "versiuni_text": [text_problema],
            "user_id": ObjectId(g.user_id),
            "date_ai":[None],
            "cod_geogebra":[""]
        }

        rezultat = problems_collection.insert_one(document_problema)
        id_nou=rezultat.inserted_id

        return redirect(url_for('vizualizeaza_problema',id_problema=str(id_nou) , mesaj="Problema noua creata"))
    
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

    # problems_collection.update_one(
    #     {"_id": ObjectId(id_problema)},
    #     {"$push":{"versiuni_text":text_nou}}
    # )

    return redirect(url_for('vizualizeaza_problema',id_problema=id_problema, mesaj="Versiune noua salvata."))

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
    
    lista_comenzi =  genereaza_comenzi_geogebra(date_curente)

    if lista_comenzi:
        problems_collection.update_one(
            {"_id":ObjectId(id_problema)},
            {"$set":{f"cod_geogebra.{index_versiune}": "\n".join(lista_comenzi)}}
        )
        return jsonify({"status": "succes", "comenzi": lista_comenzi})
    else:
        return jsonify({"status": "eroare", "mesaj": "Ai-ul nu a putut genera codul Geogebra"}),500

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

@app.route("/signup", methods=['GET','POST'])
def signup():
    if request.method=='POST':
        username = request.form.get("username")
        email = request.form.get("email")
        parola_clara = request.form.get("password")
    
        parola_criptata = bcrypt.hashpw(parola_clara.encode('utf-8'), bcrypt.gensalt())

        utilizator_nou = {
            "username": username,
            "email": email,
            "parola": parola_criptata
        }
        try:
            users_collection.insert_one(utilizator_nou)
            return redirect(url_for('login', mesaj="Cont creat cu succes! Acum te poți loga."))
        except Exception as e:

            return render_template("signup.html", eroare="Email-ul sau username-ul există deja!")
    
    return render_template("signup.html")

@app.route("/login", methods=['GET','POST'])
def login():

    if request.method=='POST':
        email_introdus = request.form.get("email")
        parola_introdusa = request.form.get("password")

        utilizator_gasit = users_collection.find_one({"email": email_introdus})

        if utilizator_gasit:
            parola_din_db = utilizator_gasit['parola']

            if bcrypt.checkpw(parola_introdusa.encode('utf-8'), parola_din_db):
                token = jwt.encode({
                    'user_id': str(utilizator_gasit['_id']),
                    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
                }, app.config['SECRET_KEY'], algorithm='HS256')

                raspuns = make_response(redirect(url_for('index')))
                raspuns.set_cookie('jwt_token', token, httponly=True)
                return raspuns
            else:
                return render_template("login.html", eroare="Parola este incorectă!")
        else:
            return render_template("login.html", eroare="Nu există niciun cont cu acest email!")

    mesaj_succes = request.args.get("mesaj")
    return render_template("login.html", mesaj=mesaj_succes)    


@app.route("/logout")
def logout():
    raspuns = make_response(redirect(url_for('login',mesaj="Te-ai deconectat")))
    raspuns.delete_cookie('jwt_token')

    return raspuns



if __name__ in "__main__":
    app.run(debug=True)