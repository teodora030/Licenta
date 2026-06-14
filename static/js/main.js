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
            appletOnLoad: async function(){
                console.log("Geogebra e gata");
                if (updateUI) updateUI();
                
            }
        }, true);

        ggbApp.inject('ggb-element');

        window.addEventListener('resize',function(){
            let newWidth = wrapper.offsetWidth;
            ggbApplet.setWidth(newWidth);
        });

        // toate versiunile problemei transmise la finalul paginii "vizualizeaza problema"
        const cutieDate =  document.getElementById("date_versiuni");

        if(cutieDate){
            initVizualizareProbleme(cutieDate); 
        }

        initCategorii();

        function initVizualizareProbleme(cutieDate){
            //partajare date
            const versiuni = JSON.parse(cutieDate.dataset.versiuni);
            let indexCurent = versiuni.length -1;
            const cutieDateAI = document.getElementById("date_ai_salvate");

            let dateAiSalvate=[];
            if (cutieDateAI && cutieDateAI.dataset.ai){dateAiSalvate = JSON.parse(cutieDateAI.dataset.ai);}

            let coduriSalvate = [];
            const cutieCoduri = document.getElementById("date_cod_ggb");
            if (cutieCoduri && cutieCoduri.dataset.coduri){coduriSalvate = JSON.parse(cutieCoduri.dataset.coduri);}

            let ultimulTipRaport = null;

            //elemente interactionare cu versiunile problemei
            const textarea = document.getElementById('textarea_problema');
            const spanCurent = document.getElementById('versiune_curenta');
            const spanTotal= document.getElementById('total_versiuni');
            const btnPrev = document.getElementById('btn_prev');
            const btnNext = document.getElementById('btn_next');
            const btnSterge = document.getElementById('btn_sterge_versiune');

            //elemente interactionare cu codul geogebra
            const zonaCodGgb = document.getElementById('zona_cod_geogebra');
            const textareaComenzi = document.getElementById('textarea_cod_geogebra');
            const btnDeseneaza = document.getElementById('btn_deseneaza');

            //elemente generare cu call api
            const btnExtrage = document.getElementById('btn_extrage_date');
            const btnGenereaza = document.getElementById('btn_genereaza_geogebra'); 
            const btnReparaAI = document.getElementById('btn_repara_ai');
            
            const afisareAI = document.getElementById('afisare_datele_problemei'); 
            const afisareAItot = document.getElementById('afisare_toate_datele_problemei');

            //updateUI - reactioneaza cand apar date noi, se schimba versiunea problemei

            updateUI= function(){
                textarea.value=versiuni[indexCurent];
                spanCurent.textContent=indexCurent+1;
                spanTotal.textContent=versiuni.length;

                btnPrev.disabled = (indexCurent===0);
                btnNext.disabled = (indexCurent===versiuni.length -1);
                
                const dateCurenteAI=dateAiSalvate[indexCurent];
                if (dateCurenteAI && dateCurenteAI !== null) {
                    // Compatibilitate: tip_figura poate fi string (schema veche) sau array (schema noua)
                    let tipFiguraDisplay;
                    if (Array.isArray(dateCurenteAI.tip_figura)) {
                        tipFiguraDisplay = dateCurenteAI.tip_figura
                            .map(t => t.replace(/_/g, ' ').toUpperCase())
                            .join(' + ');
                    } else if (typeof dateCurenteAI.tip_figura === 'string') {
                        tipFiguraDisplay = dateCurenteAI.tip_figura.replace(/_/g, ' ').toUpperCase();
                    } else {
                        tipFiguraDisplay = 'NECUNOSCUT';
                    }

                    let designFrumos = `
                        <h3 style="margin-top: 0; color: #2196F3;">Tip figură: <b>${tipFiguraDisplay}</b></h3>
                        <p><b>Puncte principale:</b> ${(dateCurenteAI.puncte_principale || []).join(', ')}</p>
                        <p><b>Puncte mentionate:</b> ${(dateCurenteAI.puncte_mentionate || []).join(', ')}</p>
                        <p><b>Laturi mentionate:</b> ${(dateCurenteAI.laturi_mentionate || []).join(', ')}</p>
                        <p><b>Laturi date:</b> ${JSON.stringify(dateCurenteAI.laturi_date || {})}</p>
                        <p><b>Unghiuri mentionate:</b> ${(dateCurenteAI.unghiuri_mentionate || []).join(', ')}</p>
                        <p><b>Unghiuri date:</b> ${JSON.stringify(dateCurenteAI.unghiuri_date || {})}</p>
                    `;

                    // Campuri noi (doar daca exista in document)
                    if (dateCurenteAI.proprietati_varfuri && Object.keys(dateCurenteAI.proprietati_varfuri).length > 0) {
                        designFrumos += `<p><b>Proprietăți vârfuri:</b> ${JSON.stringify(dateCurenteAI.proprietati_varfuri)}</p>`;
                    }
                    if (dateCurenteAI.aria !== null && dateCurenteAI.aria !== undefined) {
                        designFrumos += `<p><b>Aria dată:</b> ${dateCurenteAI.aria}</p>`;
                    }
                    if (dateCurenteAI.perimetru !== null && dateCurenteAI.perimetru !== undefined) {
                        designFrumos += `<p><b>Perimetrul dat:</b> ${dateCurenteAI.perimetru}</p>`;
                    }
                    if (dateCurenteAI.relatii_intre_laturi && dateCurenteAI.relatii_intre_laturi.length > 0) {
                        designFrumos += `<p><b>Relații între laturi:</b> ${dateCurenteAI.relatii_intre_laturi.join(', ')}</p>`;
                    }
                    if (dateCurenteAI.formula_functie) {
                        designFrumos += `<p><b>Funcție:</b> f(x) = ${dateCurenteAI.formula_functie} (${dateCurenteAI.tip_functie || '?'})</p>`;
                    }

                    // Relatii suplimentare
                    if (dateCurenteAI.relatii_suplimentare && dateCurenteAI.relatii_suplimentare.length > 0) {
                        designFrumos += `<p><b>Construcții suplimentare:</b></p><ul>`;
                        dateCurenteAI.relatii_suplimentare.forEach(rel => {
                            designFrumos += `<li><b>${rel.tip.replace(/_/g, ' ')}</b>${rel.nume_punct_nou ? ` (Punctul ${rel.nume_punct_nou})` : ''}: <i>${rel.detalii || ''}</i></li>`;
                        });
                        designFrumos += `</ul>`;
                    }

                    // Cerintele
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
            
            //desenare
            function parsezaLatura(latura) {
                // "AB" -> ["A", "B"], "CC'" -> ["C", "C'"], "A'B'" -> ["A'", "B'"]
                const tokenuri = latura.match(/[A-Z]'?/g);
                return tokenuri || [];
            }

            function parsezaUnghi(unghi) {
                // "BAC" -> ["B", "A", "C"] (varful = al doilea)
                return parsezaLatura(unghi);
            }

            async function validezaMasuratori(dateProblema) {
                const TOLERANTA = 0.001;
                const raport = {
                    laturi: [],
                    unghiuri: [],
                    toate_valide: true
                };

                const laturiDeValidat = dateProblema.laturi_date_complete || dateProblema.laturi_date;

                if (laturiDeValidat) {
                    for (const [latura, valoareAsteptata] of Object.entries(laturiDeValidat)) {
                        const puncte = parsezaLatura(latura);
                        if (puncte.length !== 2) {
                            console.warn(`Nu pot parsa latura "${latura}"`);
                            continue;
                        }
                        
                        const [p1, p2] = puncte;
                        const valoareReala = ggbApplet.getValue(`Distance(${p1}, ${p2})`);
                        
                        // Daca punctele nu exista, getValue returneaza 0 sau NaN
                        if (isNaN(valoareReala) || valoareReala === 0) {
                            console.warn(`Nu pot masura ${latura} (puncte lipsa?)`);
                            continue;
                        }
                        
                        const diferenta = Math.abs(valoareReala - valoareAsteptata);
                        const valid = diferenta < TOLERANTA;
                        
                        raport.laturi.push({
                            latura, asteptat: valoareAsteptata, real: valoareReala, diferenta, valid
                        });
                        
                        if (!valid) raport.toate_valide = false;
                    }
                }
                
                // Validam unghiurile
                if (dateProblema.unghiuri_date) {
                    for (const [unghi, valoareAsteptata] of Object.entries(dateProblema.unghiuri_date)) {
                        const puncte = parsezaUnghi(unghi);
                        
                        // Unghi cu 3 puncte (BAC) - varful in mijloc
                        // Unghi cu 1 punct (B) - GeoGebra are nevoie de context, sarim
                        if (puncte.length !== 3) {
                            console.warn(`Sar unghiul "${unghi}" - necesita 3 puncte`);
                            continue;
                        }
                        
                        const [p1, varf, p2] = puncte;
                        // Angle in radians, transformam in grade
                        const valoareReala = ggbApplet.getValue(`Angle(${p1}, ${varf}, ${p2})`) * (180 / Math.PI);
                        
                        if (isNaN(valoareReala)) {
                            console.warn(`Nu pot masura unghiul ${unghi}`);
                            continue;
                        }
                        
                        const diferenta = Math.abs(valoareReala - valoareAsteptata);
                        const valid = diferenta < TOLERANTA;
                        
                        raport.unghiuri.push({
                            unghi, asteptat: valoareAsteptata, real: valoareReala, diferenta, valid
                        });
                        
                        if (!valid) raport.toate_valide = false;
                    }
                }
                
                return raport;
            }
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
                                        // Cautam butonul de inchidere - poate fi dialogTextButton (Close) sau dialogContainedButton (OK)
                                        let btnClose = dialog.querySelector('button.dialogTextButton');
                                        if (!btnClose) {
                                            btnClose = dialog.querySelector('button.dialogContainedButton');
                                        }
                                        if (!btnClose) {
                                            // Fallback: primul buton din dialog
                                            btnClose = dialog.querySelector('button');
                                        }
                                        
                                        if (btnClose) {
                                            btnClose.click();
                                        } else {
                                            console.warn("Nu am gasit niciun buton de inchidere");
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
                    
                    await new Promise(resolve => setTimeout(resolve, 50));
                    
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
                    console.log("Erori de executie detectate, trimit raportul la backend...");
                    
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
                    
                    console.log("Raport erori salvat in MongoDB");
                    ultimulTipRaport = 'executie';
                    
                    if (!incercareDeReparareDejaFacuta) {
                        console.log("Incerc auto-repararea cu AI...");
                        const reusit = await incearcaRepararea('executie');
                        if (reusit) return;
                    }
                    
                    console.log("Activez butonul manual 'Repara cu AI'");
                    btnReparaAI.disabled = false;
                } else {
                    console.log("Executie curata. Verific corectitudinea matematica...");
                    
                    const dateAi = dateAiSalvate[indexCurent];
                    if (dateAi) {
                        const raportMasuratori = await validezaMasuratori(dateAi);
                        console.log("=== RAPORT VALIDARE MATEMATICA ===");
                        console.table([...raportMasuratori.laturi, ...raportMasuratori.unghiuri]);
                        
                        if (!raportMasuratori.toate_valide) {
                            console.warn("Imprecizii matematice detectate!");
                            
                            const raportImprecizii = {
                                timestamp: new Date().toISOString(),
                                masuratori: raportMasuratori
                            };
                            
                            await fetch(`/api/salveaza_raport_imprecizii/${idProblema}`, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({ 
                                    index: indexCurent, 
                                    raport: raportImprecizii 
                                })
                            });
                            
                            console.log("Raport imprecizii salvat in MongoDB");
                            
                            ultimulTipRaport = 'imprecizii';
                            
                            if (!incercareDeReparareDejaFacuta) {
                                console.log("Incerc auto-repararea pentru imprecizii...");
                                const reusit = await incearcaRepararea('imprecizii');
                                if (reusit) return;
                            }
                            
                            // Daca am ajuns aici, auto-repararea nu a mers sau am facut deja
                            console.log("Activez butonul manual 'Repara cu AI'");
                            btnReparaAI.disabled = false;
                        } else {
                            console.log("✓ Figura este matematic corecta!");
                            btnReparaAI.disabled = true;
                        }
                    } else {
                        console.log("Nu am date_ai pentru validare matematica");
                        btnReparaAI.disabled = true;
                    }
                }
            }
            async function incearcaRepararea(tipRaport = 'executie'){
                const idProblema = window.location.pathname.split('/').pop();
                
                btnReparaAI.innerHTML = "Se repara...";
                btnReparaAI.disabled = true;
                
                try {
                    const response = await fetch(`/api/repara_cod_ggb/${idProblema}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            index: indexCurent,
                            tip_raport: tipRaport
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status !== "succes") {
                        console.error("AI nu a putut repara:", data.mesaj);
                        btnReparaAI.innerHTML = "Repara cu AI";
                        return false;
                    }
                    
                    console.log(`=== REPARARI FACUTE DE AI (${tipRaport}) ===`);
                    data.comenzi.forEach((linie, i) => {
                        if (linie.schimbat) {
                            console.log(`Linia ${i+1}: ${linie.comanda}`);
                            console.log(`   → ${linie.explicatie}`);
                        }
                    });
                    
                    const codReparat = data.comenzi.map(linie => linie.comanda).join('\n');
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

            //grupuri de actiuni
            configureazaPipelineAI();
            configureazaNavigare();
            configureazaEditorGgb();

            function configureazaPipelineAI(){
                async function ruleazaExtragere() {
                    const originalText = btnExtrage.innerHTML;
                    btnExtrage.innerHTML = "Se extrag datele...";
                    btnExtrage.disabled = true;
                    afisareAI.textContent = "Se proceseaza problema...Mai asteapta";
                    try {
                        const idProblema = window.location.pathname.split('/').pop();
                        const response = await fetch(`/api/extrage_date/${idProblema}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({index: indexCurent})
                        });
                        const data = await response.json();
                        if (data.status === "succes") {
                            dateAiSalvate[indexCurent] = data.date;
                            updateUI();
                            return true;
                        } else {
                            afisareAI.textContent = "Eroare: " + data.mesaj;
                            return false;
                        }
                    } catch (error) {
                        afisareAI.textContent = "Eroare de conexiune cu serverul.";
                        console.error("Eroare fetch:", error);
                        return false;
                    } finally {
                        btnExtrage.innerHTML = originalText;
                        btnExtrage.disabled = false;
                    }
                }

                async function ruleazaGenerare() {
                    const originalText = btnGenereaza.innerHTML;
                    btnGenereaza.innerHTML = "Se deseneaza...";
                    btnGenereaza.disabled = true;
                    try {
                        const idProblema = window.location.pathname.split('/').pop();
                        const response = await fetch(`/api/genereaza_figura/${idProblema}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({index: indexCurent})
                        });
                        const data = await response.json();

                        if (data.status === "succes") {
                            console.log("Comenzi primite de la AI:", data.comenzi);

                            if (data.laturi_date_complete && dateAiSalvate[indexCurent]) {
                                dateAiSalvate[indexCurent].laturi_date_complete = data.laturi_date_complete;
                            }
                            if (data.unghiuri_date_complete && dateAiSalvate[indexCurent]) {
                                dateAiSalvate[indexCurent].unghiuri_date_complete = data.unghiuri_date_complete;
                            }

                            zonaCodGgb.style.display = 'block';
                            textareaComenzi.value = data.comenzi.join('\n');
                            deseneazaDinTextarea();
                            return true;
                        } else {
                            alert("Eroare la desenare: " + data.mesaj);
                            return false;
                        }
                    } catch (error) {
                        console.error("Eroare fetch: ", error);
                        alert("Eroare comunicare cu serverul.");
                        return false;
                    } finally {
                        btnGenereaza.innerHTML = originalText;
                        btnGenereaza.disabled = false;
                    }
                }

                btnGenereaza.addEventListener('click', ruleazaGenerare);
                btnExtrage.addEventListener('click', ruleazaExtragere);


                const params = new URLSearchParams(window.location.search);
                if (params.get('auto_genereaza') === '1') {
                    history.replaceState(null, '', window.location.pathname);
                    (async () => {
                        const ok = await ruleazaExtragere();
                        if (ok) await ruleazaGenerare();
                    })();
                }


            }

            function configureazaNavigare(){
                btnPrev.addEventListener('click',() => {indexCurent-=1; updateUI();});
                btnNext.addEventListener('click',() => {indexCurent+=1; updateUI();});
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
            }

            function configureazaEditorGgb(){
                if (btnDeseneaza){
                    btnDeseneaza.addEventListener('click',deseneazaDinTextarea);
                }

                if (btnReparaAI){
                        btnReparaAI.addEventListener('click', () => incearcaRepararea(ultimulTipRaport || 'executie'));
                    }
            }

        }

        function initCategorii(){
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
        }

    };
});