window.addEventListener('load', async function() {
    const selectClasa = document.getElementById('clasa') 
                     || document.getElementById('filtru-clasa');
    const selectSubcap = document.getElementById('subcapitol') 
                      || document.getElementById('filtru-subcapitol');
    
    // dacă nu există nici un dropdown pe pagina asta, ieșim
    if (!selectClasa) return;
    
    // ia categoriile de la backend
    const response = await fetch('/api/categorii');
    const categorii = await response.json();
    
    // populează clasele
    for (const clasa of Object.keys(categorii)) {
        const option = document.createElement('option');
        option.value = clasa;
        option.textContent = clasa;
        selectClasa.appendChild(option);
    }
    
    // pre-selectează valoarea existentă (pentru editare)
    const clasaInitiala = selectClasa.dataset.valoare;
    if (clasaInitiala) {
        selectClasa.value = clasaInitiala;
        populeazaSubcapitole(clasaInitiala);
    }
    
    // listener pentru schimbarea clasei
    selectClasa.addEventListener('change', (e) => {
        populeazaSubcapitole(e.target.value);
    });
    
    function populeazaSubcapitole(clasa) {
        if (!selectSubcap) return;
        
        // primul option (placeholder)
        const placeholder = selectSubcap.querySelector('option[value=""]');
        selectSubcap.innerHTML = '';
        if (placeholder) selectSubcap.appendChild(placeholder);
        
        if (clasa && categorii[clasa]) {
            selectSubcap.disabled = false;
            for (const subcap of categorii[clasa]) {
                const option = document.createElement('option');
                option.value = subcap;
                option.textContent = subcap;
                selectSubcap.appendChild(option);
            }
            
            // pre-selectare la editare
            const subcapInitial = selectSubcap.dataset.valoare;
            if (subcapInitial) selectSubcap.value = subcapInitial;
        } else {
            selectSubcap.disabled = true;
        }
    }
});