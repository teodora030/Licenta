window.addEventListener('load', function () {
    const MOD_DEBUG = false;
    let updateUI = null;

    const wrapper = document.getElementById('ggb-wrapper');

    if (wrapper){
    
        const containerWidth = wrapper.offsetWidth;
        const tipFigura = wrapper.dataset.tip;
        const appName = tipFigura === "3d" ? "3d" : "classic"

    const ggbApp = new GGBApplet({
        appName: appName,
        width: containerWidth,
        height: 1000,
        showToolBar: true,
        showAlgebraInput: true,
        showMenuBar: true,
        appletOnLoad: function(){
            console.log("Geogebra e gata");
            if (updateUI) updateUI();
        }
    }, true);

    ggbApp.inject('ggb-element');

    window.addEventListener('resize',function(){
        let newWidth = wrapper.offsetWidth;
        ggbApplet.setWidth(newWidth);
    });

    // toate versiunile problemei transmise la finalul paginii vizualizeaza problema
    const cutieDate =  this.document.getElementById("date_versiuni");

    if(cutieDate){

        // vizualizare versiunile problemei
        const versiuni = JSON.parse(cutieDate.dataset.versiuni);

        const cutieDateAI = this.document.getElementById("date_ai_salvate");
        let dateAiSalvate=[];
        if (cutieDateAI && cutieDateAI.dataset.ai){
            dateAiSalvate = JSON.parse(cutieDateAI.dataset.ai);
        }
        let indexCurent = versiuni.length -1;
        const textarea = this.document.getElementById('textarea_problema');
        const spanCurent = this.document.getElementById('versiune_curenta');
        const spanTotal= this.document.getElementById('total_versiuni');
        const btnPrev = document.getElementById('btn_prev');
        const btnNext = document.getElementById('btn_next');
        const btnSterge = this.document.getElementById('btn_sterge_versiune');

        
        const btnExtrage = document.getElementById('btn_extrage_date');
        const btnGenereaza = document.getElementById('btn_genereaza_geogebra'); 
        const afisareAI = document.getElementById('afisare_datele_problemei'); 
        const afisareAItot = this.document.getElementById('afisare_toate_datele_problemei');

        // editare comenzi geogebra
        const zonaCodGgb = this.document.getElementById('zona_cod_geogebra');
        const textareaComenzi = this.document.getElementById('textarea_cod_geogebra');
        const btnDeseneaza=this.document.getElementById('btn_deseneaza');
        const btnReparaAI = this.document.getElementById('btn_repara_ai');
        const cutieCoduri = this.document.getElementById("date_cod_ggb"); //div-ul invizibil
        let coduriSalvate = [];
        if (cutieCoduri && cutieCoduri.dataset.coduri){
            coduriSalvate = JSON.parse(cutieCoduri.dataset.coduri);
        }




        updateUI= function(){
            textarea.value=versiuni[indexCurent];
            spanCurent.textContent=indexCurent+1;
            spanTotal.textContent=versiuni.length;

            btnPrev.disabled = (indexCurent===0);
            btnNext.disabled = (indexCurent===versiuni.length -1);
            
            const dateCurenteAI=dateAiSalvate[indexCurent];
            if (dateCurenteAI && dateCurenteAI !== null) {

                afisareAI.innerHTML = dateCurenteAI;


                // Construim un design HTML frumos
                let designFrumos = `
                    <h3 style="margin-top: 0; color: #2196F3;">Tip figură: <b>${dateCurenteAI.tip_figura.replace('_', ' ').toUpperCase()}</b></h3>
                    <p><b>Puncte principale:</b> ${dateCurenteAI.puncte_principale.join(', ')}</p>
                    <p><b>Puncte mentionate:</b> ${dateCurenteAI.puncte_mentionate.join(', ')}</p>
                    <p><b>Laturi mentionate:</b> ${dateCurenteAI.laturi_mentionate.join(', ')}</p>
                    <p><b>Laturi date:</b> ${JSON.stringify(dateCurenteAI.laturi_date)}</p>
                    <p><b>Unghiuri mentionate:</b> ${dateCurenteAI.unghiuri_mentionate.join(', ')}</p>
                    <p><b>Unghiuri date:</b> ${JSON.stringify(dateCurenteAI.unghiuri_date)}</p>
                `;

                // Dacă avem relații suplimentare (ex: înălțimi, bisectoare), facem o listă cu buline
                if (dateCurenteAI.relatii_suplimentare && dateCurenteAI.relatii_suplimentare.length > 0) {
                    designFrumos += `<p><b>Construcții suplimentare:</b></p><ul>`;
                    dateCurenteAI.relatii_suplimentare.forEach(rel => {
                        designFrumos += `<li><b>${rel.tip.replace('_', ' ')}</b> (Punctul ${rel.nume_punct_nou}): <i>${rel.detalii}</i></li>`;
                    });
                    designFrumos += `</ul>`;
                }

                // Adăugăm cerințele la final
                if (dateCurenteAI.cerinte && dateCurenteAI.cerinte.length > 0) {
                    designFrumos += `<p><b>Cerințe:</b></p><ul>`;
                    dateCurenteAI.cerinte.forEach(cerinta => {
                        designFrumos += `<li>${cerinta}</li>`;
                    });
                    designFrumos += `</ul>`;
                }

                
                afisareAI.innerHTML = designFrumos;
                btnGenereaza.disabled = false;
                
            } else {
                afisareAI.innerHTML = "<i>Nu există date extrase pentru această versiune. Apasă pe butonul de extragere.</i>";
                btnGenereaza.disabled = true; 
            }

            const codCurent = coduriSalvate[indexCurent];
            console.log(typeof(codCurent));
            console.log(codCurent);

            if (codCurent && codCurent.trim() !==""){
                zonaCodGgb.style.display = 'block';
                textareaComenzi.value=codCurent;

                setTimeout(() => { deseneazaDinTextarea();},100);
            } else {
                zonaCodGgb.style.display='none';
                textareaComenzi.value="";
            }

            
        };

        btnExtrage.addEventListener('click', async function() {
            const originalText = btnExtrage.innerHTML;
            btnExtrage.innerHTML="Se extrag datele..."
            btnExtrage.disabled=true;
            afisareAI.textContent = "Se proceseaza problema...Mai asteapta"

            try{
                const idProblema = window.location.pathname.split('/').pop()
                const response = await fetch(`/api/extrage_date/${idProblema}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({index: indexCurent})
                });

                const data = await response.json();
                if (data.status === "succes"){
                    dateAiSalvate[indexCurent]=data.date;
                    updateUI();
                } else {
                    afisareAI.textContent = "Eroare: "+ data.mesaj;

                }
            } catch (error) {
                afisareAI.textContent = "Eroare de conexiune cu serverul.";
                console.error("Eroare fetch:", error);
            } finally {
                
                btnExtrage.innerHTML = originalText;
                btnExtrage.disabled = false;
            }
            
        });

        btnGenereaza.addEventListener('click', async function(){
            const originalText = btnGenereaza.innerHTML;
            btnGenereaza.innerHTML = "Se deseneaza..."
            btnGenereaza.disabled = true;

            try{
                const idProblema = window.location.pathname.split('/').pop();

                const response = await fetch(`/api/genereaza_figura/${idProblema}`,{
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({index: indexCurent})
                });

                const data = await response.json();

                if (data.status === "succes"){
                    console.log("Comenzi primite de la AI:", data.comenzi);

                    // ggbApplet.newConstruction();

                    // data.comenzi.forEach( comanda => {
                    //     ggbApplet.evalCommand(comanda);
                    // });

                    zonaCodGgb.style.display='block';

                    textareaComenzi.value = data.comenzi.join('\n');
                    deseneazaDinTextarea();
                } else {
                    alert("Eroare la desenare: " + data.mesaj);
                }
            } catch (error){
                console.error("Eroare fetch: ", error);
                alert("Eroare comunicare cu serverul.");
            } finally {
                btnGenereaza.innerHTML=originalText;
                btnGenereaza.disabled = false;
            }
        });

        async function deseneazaDinTextarea(incercareDeReparareDejaFacuta = false){
            const codNou = textareaComenzi.value;
            const liniiCod = codNou.split('\n').filter(linie => linie.trim() !== '');
            
            let mesajEroareCapturat = null;
            
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType !== 1) continue;
                        
                        const dialog = node.matches?.('div.dialogComponent[aria-label="Error"]') 
                            ? node 
                            : node.querySelector?.('div.dialogComponent[aria-label="Error"]');
                        
                        if (dialog) {
                            const labels = dialog.querySelectorAll('.gwt-Label');
                            const textEroare = Array.from(labels)
                                .map(l => l.textContent.trim())
                                .filter(t => t !== '')
                                .join(' | ');
                            
                            mesajEroareCapturat = textEroare;
                            
                            if (!MOD_DEBUG) {
                                setTimeout(() => {
                                    const btnClose = dialog.querySelector('button.dialogTextButton');
                                    if (btnClose) {
                                        btnClose.click();
                                    } else {
                                        console.warn("Butonul CLOSE nu a fost gasit");
                                    }
                                }, 50);
                            }
                        }
                    }
                }
            });
            
            observer.observe(document.body, { childList: true, subtree: true });
            
            ggbApplet.newConstruction();
            
            const raport = [];
            
            for (const comanda of liniiCod) {
                mesajEroareCapturat = null;
                
                const succes = ggbApplet.evalCommand(comanda.trim());
                
                await new Promise(resolve => setTimeout(resolve, 100));
                
                raport.push({
                    comanda: comanda.trim(),
                    succes: succes,
                    eroare: mesajEroareCapturat
                });
            }
            
            observer.disconnect();
            
            console.log("=== RAPORT EXECUTIE GEOGEBRA ===");
            console.table(raport);
            
            const idProblema = window.location.pathname.split('/').pop();
            
            await fetch(`/api/salveaza_cod_ggb/${idProblema}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ index: indexCurent, cod: codNou })
            });
            
            coduriSalvate[indexCurent] = codNou;
            
            const exista_erori = raport.some(item => item.succes === false);
            
            if (exista_erori) {
                console.log("Erori detectate, trimit raportul la backend...");
                
                const raportComplet = {
                    timestamp: new Date().toISOString(),
                    comenzi: raport
                };
                
                await fetch(`/api/salveaza_raport_erori/${idProblema}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        index: indexCurent, 
                        raport: raportComplet 
                    })
                });
                
                console.log("Raport salvat in MongoDB");
                
                // AUTO-REPARARE: doar la prima incercare
                if (!incercareDeReparareDejaFacuta) {
                    console.log("Incerc auto-repararea cu AI...");
                    const reusit = await incearcaRepararea();
                    if (reusit) return;  // Re-executia s-a facut deja in incearcaRepararea
                }
                
                // Daca am ajuns aici: ori am facut deja retry, ori repararea a esuat
                console.log("Activez butonul manual 'Repara cu AI'");
                btnReparaAI.disabled = false;
            } else {
                // Totul ok → dezactivam butonul manual
                btnReparaAI.disabled = true;
            }
        }

        async function incearcaRepararea(){
            const idProblema = window.location.pathname.split('/').pop();
            
            btnReparaAI.innerHTML = "Se repara...";
            btnReparaAI.disabled = true;
            
            try {
                const response = await fetch(`/api/repara_cod_ggb/${idProblema}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ index: indexCurent })
                });
                
                const data = await response.json();
                
                if (data.status !== "succes") {
                    console.error("AI nu a putut repara:", data.mesaj);
                    btnReparaAI.innerHTML = "Repara cu AI";
                    return false;
                }
                
                // Afisam in consola explicatiile pentru liniile schimbate
                console.log("=== REPARARI FACUTE DE AI ===");
                data.comenzi.forEach((linie, i) => {
                    if (linie.schimbat) {
                        console.log(`Linia ${i+1}: ${linie.comanda}`);
                        console.log(`   → ${linie.explicatie}`);
                    }
                });
                
                // Construim codul nou (doar comenzile, fara metadata)
                const codReparat = data.comenzi.map(linie => linie.comanda).join('\n');
                
                // Inlocuim in textarea
                textareaComenzi.value = codReparat;
                
                btnReparaAI.innerHTML = "Repara cu AI";
                
                // Re-executam (cu flag-ul ca am incercat deja repararea)
                await deseneazaDinTextarea(true);
                
                return true;
                
            } catch (error) {
                console.error("Eroare la reparare:", error);
                btnReparaAI.innerHTML = "Repara cu AI";
                return false;
            }
        }

        if (btnDeseneaza){
            btnDeseneaza.addEventListener('click',deseneazaDinTextarea);
        }

        if (btnReparaAI){
            btnReparaAI.addEventListener('click', incearcaRepararea);
        }


        btnPrev.addEventListener('click',function(){
                indexCurent-=1;
                updateUI();
            });

        btnNext.addEventListener('click',function(){
            indexCurent+=1;
            updateUI();
        })

        if(btnSterge){
            btnSterge.addEventListener('click',async function(){
                const confirmare = confirm("Esti sigura ca vrei sa stergi versiunea? Daca este singura, intreaga problema va fi stearsa.");

                if(!confirmare) return;

                try{
                    const idProblema=window.location.pathname.split('/').pop();
                    const response = await fetch(`/sterge_versiune/${idProblema}`,{
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({index: indexCurent})
                    });

                    const data = await response.json();

                    if (data.status === "succes"){
                        window.location.href = data.redirect;
                    }
                } catch (error){
                    console.error("Eroare: ", error);
                    alert("Eroare de comunicare cu serverul.")
                }
            })
        };

        //updateUI();
    }


    //butoane categorie problema
    const btnEditCateg = document.getElementById('btn-editeaza-categorii');
    const btnSalveazaCateg = document.getElementById('btn-salveaza-categorii');
    const btnAnuleazaCateg = document.getElementById('btn-anuleaza-categorii');

    if (btnEditCateg) {
        const afisare = document.getElementById('afisare-categorii');
        const form = document.getElementById('form-categorii');
        
        btnEditCateg.addEventListener('click', () => {
            afisare.style.display = 'none';
            form.style.display = 'block';
        });
        
        btnAnuleazaCateg.addEventListener('click', () => {
            form.style.display = 'none';
            afisare.style.display = 'block';
        });
        
        btnSalveazaCateg.addEventListener('click', async () => {
            const clasa = document.getElementById('clasa').value;
            const subcapitol = document.getElementById('subcapitol').value;
            
            if (!clasa || !subcapitol) {
                alert("Alege clasa și subcapitolul!");
                return;
            }
            
            const idProblema = window.location.pathname.split('/').pop();
            
            try {
                const response = await fetch(`/api/actualizeaza_categorii/${idProblema}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ clasa, subcapitol })
                });
                
                const data = await response.json();
                
                if (data.status === "succes") {
                    // actualizează textul afișat
                    document.getElementById('text-clasa').textContent = data.clasa;
                    document.getElementById('text-subcapitol').textContent = data.subcapitol;
                    
                    // ascunde form, afișează textul
                    form.style.display = 'none';
                    afisare.style.display = 'block';
                } else {
                    alert("Eroare: " + data.mesaj);
                }
            } catch (error) {
                console.error("Eroare:", error);
                alert("Eroare de comunicare cu serverul.");
            }
        });
    }

    };
});