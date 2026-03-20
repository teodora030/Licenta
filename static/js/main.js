window.addEventListener('load', function () {

    const wrapper = document.getElementById('ggb-wrapper');

    const containerWidth = wrapper.offsetWidth;

    const ggbApp = new GGBApplet({
        appName: 'graphing',
        width: containerWidth,
        height: 600,
        showToolBar: true,
        showAlgebraInput: true,
        showMenuBar: true,
    }, true);

    ggbApp.inject('ggb-element');

    window.addEventListener('resize',function(){
        let newWidth = wrapper.offsetWidth;
        ggbApplet.setWidth(newWidth);
    });

    const cutieDate =  this.document.getElementById("date_versiuni");

    if(cutieDate){
        const versiuni = JSON.parse(cutieDate.dataset.versiuni);

        const cutieDateAI = this.document.getElementById("date_ai_salvate");
        let dateAiSalvate=[];
        if (cutieDateAI && cutieDateAI.dataset.ai){
            dateAiSalvate = JSON.parse(cutieDateAI.dataset.ai);
        }
        


        const btnExtrage = document.getElementById('btn_extrage_date');
        const btnGenereaza = document.getElementById('btn_genereaza_geogebra'); 
        const afisareAI = document.getElementById('afisare_datele_problemei'); 



        let indexCurent = versiuni.length -1;

        const textarea = this.document.getElementById('textarea_problema');
        const spanCurent = this.document.getElementById('versiune_curenta');
        const spanTotal= this.document.getElementById('total_versiuni');
        const btnPrev = document.getElementById('btn_prev');
        const btnNext = document.getElementById('btn_next');

        function updateUI(){
            textarea.value=versiuni[indexCurent];
            spanCurent.textContent=indexCurent+1;
            spanTotal.textContent=versiuni.length;

            btnPrev.disabled = (indexCurent===0);
            btnNext.disabled = (indexCurent===versiuni.length -1);
            
            const dateCurenteAI=dateAiSalvate[indexCurent];
            if (dateCurenteAI && dateCurenteAI !== null) {
                // Construim un design HTML frumos, bucată cu bucată
                let designFrumos = `
                    <h3 style="margin-top: 0; color: #2196F3;">Tip figură: <b>${dateCurenteAI.tip_figura.replace('_', ' ').toUpperCase()}</b></h3>
                    <p><b>Puncte principale:</b> ${dateCurenteAI.puncte_principale.join(', ')}</p>
                    <p><b>Laturi date:</b> ${JSON.stringify(dateCurenteAI.laturi_date)}</p>
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

            
        }

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





        btnPrev.addEventListener('click',function(){
                indexCurent-=1;
                updateUI();
            });

        btnNext.addEventListener('click',function(){
            indexCurent+=1;
            updateUI();
        })

        updateUI();
    }
});