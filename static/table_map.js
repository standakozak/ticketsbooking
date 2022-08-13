function is_numeric(string){
    return /^-?\d+$/.test(string);
}

function zobraz_cenu(){
    data = document.querySelectorAll('[id^="field"]');
    celkova_cena = 0
    for (i=0;i<data.length;i++){
        input_value = data[i].value
        if (is_numeric(input_value)){
            celkova_cena += parseInt(input_value) * 300
            
        }
    }
    nastav_cenu(celkova_cena)
}

function nastav_cenu(cena){
    if (cena >= 0 && cena <= 21*300){
        vystup_elem = document.getElementById("cena")
        vystup_elem.innerHTML = "Total price: " + cena.toString() + " Kč"
    }
}

function show(id_divu, id_buttonu){
    // Nejprve vsechny schovej
    //document.getElementById("velky_sal_div").classList.add("skryte")
    //document.getElementById("levy_sal_div").classList.add("skryte")
    //document.getElementById("pravy_sal_div").classList.add("skryte")
    document.getElementById("prizemi_sal_div").classList.add("skryte")
    document.getElementById("galerie_div").classList.add("skryte")

    document.getElementById("show_velky_sal").classList.remove("sal_active")
    document.getElementById("show_levy_sal").classList.remove("sal_active")
    document.getElementById("show_pravy_sal").classList.remove("sal_active")
    document.getElementById("show_galerie").classList.remove("sal_active")

    document.getElementById(id_buttonu).classList.add("sal_active")
    document.getElementById(id_divu).classList.remove("skryte")
}


function oncheck(cislo_stolu, volnych_mist, cislo_v_salu, sal_str){
    text_field_div = document.getElementById("field_div"+cislo_stolu)
    if (!document.contains(text_field_div)){
        // Aktivace buttonu
        button_clicked = document.getElementById(cislo_stolu)
        button_clicked.classList.add("clicked")

        // Vytváření labelu k textovému poli
        new_label = document.createElement("label")
        new_label.setAttribute("id", "label" + cislo_stolu)
        new_label.setAttribute("for", "field" + cislo_stolu)
        new_label.innerHTML = "Table no. " + cislo_v_salu + " (" + sal_str + ") "

        
        // Vytváření inputu - textového field
        nove_field = document.createElement("input")
        nove_field.setAttribute("type", "number")
        nove_field.setAttribute("id", "field" + cislo_stolu)
        nove_field.setAttribute("min", "1")
        nove_field.setAttribute("max", volnych_mist)
        nove_field.setAttribute("value", volnych_mist)
        nove_field.name = "field"+cislo_stolu
        nove_field.setAttribute("oninput", oninput="this.value = this.value.replace(/[^1-"+ (volnych_mist).toString() + ".]/g," + volnych_mist.toString() + ").replace(/(\..*?)\..*/g, '$1');zobraz_cenu()")
        //console.log("this.value = this.value.replace(/[^0-"+ (volnych_mist + 1).toString() + ".]/g," + volnych_mist.toString() + ").replace(/(\..*?)\..*/g, '$1');")
        
        
        // Break line
        new_line = document.createElement("br")
        new_line.setAttribute("id", "br" + cislo_stolu)

        // Div, který obsahuje field, br, ...
        field_div = document.createElement("div")
        field_div.setAttribute("id", "field_div" + cislo_stolu)
        field_div.appendChild(nove_field)
        field_div.appendChild(new_label)
        field_div.appendChild(new_line)

        // Přidání všeho do jednoho divu
        container = document.getElementById("pocty_mist")
        container.appendChild(field_div)


    } else {

        // Deaktivace buttonu
        button_clicked = document.getElementById(cislo_stolu)
        button_clicked.classList.remove("clicked")
        

        // Odstraní všechny objekty
        text_field_div.remove()
    }

    zobraz_cenu() // Změní celkovou cenu
}