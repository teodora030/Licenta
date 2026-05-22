window.addEventListener('load', function() {
    const filtruClasa = document.getElementById('filtru-clasa');
    const filtruSubcap = document.getElementById('filtru-subcapitol');
    const filtruTip = document.getElementById('filtru-tip');
    // dacă nu suntem pe dashboard, ieșim
    if (!filtruClasa) return;
    
    const probleme = document.querySelectorAll('.card-problema');
    
    function filtreaza() {
        const clasaSelectata = filtruClasa.value;
        const subcapSelectat = filtruSubcap.value;
        const tipSelectat = filtruTip.value;
        console.log('----------Filtrez------------');
        console.log('Filtre:',{clasaSelectata,subcapSelectat,tipSelectat});
        
        let vizibile = 0;
        
        probleme.forEach((card,i) => {
            const clasaCard = card.dataset.clasa;
            const subcapCard = card.dataset.subcapitol;
            const tipCard = card.dataset.tip;
            
            // verifică dacă card-ul corespunde filtrelor
            const matchClasa = !clasaSelectata || clasaCard === clasaSelectata;
            const matchSubcap = !subcapSelectat || subcapCard === subcapSelectat;
            const matchTip = !tipSelectat || tipCard === tipSelectat;

             console.log(`Card ${i}:`, {
                tip_card: card.dataset.tip,
                tip_filtru: tipSelectat,
                matchTip,
                matchClasa,
                matchSubcap
            });
            
            if (matchClasa && matchSubcap && matchTip) {
                card.style.display = '';
                vizibile++;
            } else {
                card.style.display = 'none';
            }

            
        });

        console.log(`Vizibile: ${vizibile}/${probleme.length}`);
        
        // mesaj dacă nu sunt rezultate
        const mesajGol = document.getElementById('mesaj-niciun-rezultat');
        if (mesajGol) {
            mesajGol.style.display = vizibile === 0 ? 'block' : 'none';
        }
    }
    
    filtruClasa.addEventListener('change', filtreaza);
    filtruSubcap.addEventListener('change', filtreaza);
    filtruTip.addEventListener('change', filtreaza);
});