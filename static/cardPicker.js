function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function selectAll(){
    let idstr = document.getElementById('elerheto').value;
    if(idstr == 'null'){
        document.getElementById('alertBox').innerText = 'Nincsenek kártyák, amiket ki lehetett volna választani, vagy nem szűrtél rá semmire.';
        document.getElementById('alertBox').classList.remove('d-none');
        await sleep(6000);
        document.getElementById('alertBox').classList.add('d-none');
        return
    }
    var midlist = idstr.split(';');
    var voltad = false;
    for(let i = 0; i < midlist.length; i++){
        if(document.getElementById('picker'+midlist[i]).classList.contains("btn-dark") == false){
            pickThis(midlist[i], false);
            voltad = true
        }
    }
    if(voltad == false){
        for(let i = 0; i < midlist.length; i++){
            pickThis(midlist[i], false);
        }
    }
}

async function redoSelections(){
    try{
        var midlist = localStorage.getItem("cardPickStor").split(";");
        if(midlist[0] != ""){
            for(let i = 0; i < midlist.length-1; i++){
                console.log(midlist[i]);
                await sleep(2);
                pickThis(midlist[i], true);
            }
        }
    }catch (e){
        console.log("Catched Exception: "+e);
        console.log("Card storage was: "+localStorage.getItem("cardPickStor"));
        await sleep(5);
    }
    await sleep(2);
    document.getElementById("underLoader").classList.remove("d-none");
    document.getElementById("loader").classList.add("d-none");
    document.getElementById("underLoader").style.removeProperty("display");
}

document.addEventListener('DOMContentLoaded', function() {
    if(localStorage.getItem('newsID') == null || localStorage.getItem('newsID') != "1"){
        localStorage.setItem('newsID', '1')
        const myModal = new bootstrap.Modal('#newsModal', {
            show: true
        })
        myModal.show()
    }
    redoSelections();
 }, false);

function clearSelections(){
    localStorage.removeItem("cardPickStor");
    document.location.reload();
}

function pickThis(cardID, load){
    console.log("start")
    if(!load){
        if(document.getElementById('picker'+cardID).classList.contains("btn-dark")){
            console.log("Val warn:")
            var midlist = document.getElementById('valasztottak1').value.split(";");
            document.getElementById('valasztottak1').value = "";
            for(let i = 0; i < midlist.length-1; i++){
                if(midlist[i] != cardID){
                    console.log(midlist[i]);
                    document.getElementById('valasztottak1').value += midlist[i]+';';
                }
            }
            document.getElementById('valasztottak2').value = document.getElementById('valasztottak1').value;
            document.getElementById('valasztottakDarab').innerText = 'Kiválasztva: '+(document.getElementById('valasztottak1').value.split(';').length - 1)+' darab kártya';
            try{
                document.getElementById('picker'+cardID).classList.add("btn-outline-primary");
                document.getElementById('picker'+cardID).classList.remove("btn-dark");
                document.getElementById('card'+cardID).classList.remove('text-bg-warning');
            }catch(e){
                console.log("can't find: "+cardID);
            }
            localStorage.setItem("cardPickStor", document.getElementById('valasztottak1').value);
        }else{
            load = true
        }
    }
    
    if(load){
        console.log("Val norm:")
        document.getElementById('valasztottak1').value = document.getElementById('valasztottak1').value+cardID+';';
        console.log(document.getElementById('valasztottak1').value);
        try{
            document.getElementById('picker'+cardID).classList.add("btn-dark");
            document.getElementById('picker'+cardID).classList.remove("btn-outline-primary");
            document.getElementById('card'+cardID).classList.add('text-bg-warning');
        }catch(e){
            console.log("can't find: "+cardID);
        }
        document.getElementById('valasztottak2').value = document.getElementById('valasztottak1').value;
        localStorage.setItem("cardPickStor", document.getElementById('valasztottak1').value);
        document.getElementById('valasztottakDarab').innerText = 'Kiválasztva: '+(document.getElementById('valasztottak1').value.split(';').length - 1)+' darab kártya';
    }
}