function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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
            var midlist = document.getElementById('valasztottak').value.split(";");
            document.getElementById('valasztottak').value = "";
            for(let i = 0; i < midlist.length-1; i++){
                if(midlist[i] != cardID){
                    console.log(midlist[i]);
                    document.getElementById('valasztottak').value += midlist[i]+';';
                }
            }
            try{
                document.getElementById('picker'+cardID).classList.add("btn-outline-primary");
                document.getElementById('picker'+cardID).classList.remove("btn-dark");
                document.getElementById('card'+cardID).classList.remove('text-bg-warning');
            }catch(e){
                console.log("can't find: "+cardID);
            }
            localStorage.setItem("cardPickStor", document.getElementById('valasztottak').value);
        }else{
            load = true
        }
    }
    
    if(load){
        console.log("Val norm:")
        document.getElementById('valasztottak').value = document.getElementById('valasztottak').value+cardID+';';
        console.log(document.getElementById('valasztottak').value);
        try{
            document.getElementById('picker'+cardID).classList.add("btn-dark");
            document.getElementById('picker'+cardID).classList.remove("btn-outline-primary");
            document.getElementById('card'+cardID).classList.add('text-bg-warning');
        }catch(e){
            console.log("can't find: "+cardID);
        }
        localStorage.setItem("cardPickStor", document.getElementById('valasztottak').value);
    }
}