const inputField = document.getElementById('codeSearchField');

let typingTimer;
const doneTypingInterval = 1000;

inputField.addEventListener('input', function () {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () {
        // User has finished typing, perform request
        if(($('#codeSearchField').val() !== '' || $('#codeSearchField').val() !== ' ') && $('#codeSearchField').val().length >= 3){
            calcCodePicker($('#codeSearchField').val());
        }else{
            showSelected();
        }
    }, doneTypingInterval);
});

localStorage.setItem('courseCodesStor', $('#selectedCourseCodes').val());
$('#courseCodeLength').html('Kiválasztva: '+($('#selectedCourseCodes').val().split(';').length-1).toString()+' db - pld: '+localStorage.getItem('courseCodesStor').split(';')[0].toString());

async function calcCodePicker(text){
    try{
        arr = await getCourseCodes($('#apiKeyHolder').val(), text);
    }catch (e){
        console.log('Error with API: '+e);
        return;
    }
    document.getElementById('codeSelector').innerHTML = '';
    for(let i = 0; i < arr.data.length; i++){
        if(localStorage.getItem('courseCodesStor') && localStorage.getItem('courseCodesStor').includes(arr.data[i])){
            document.getElementById('codeSelector').innerHTML += '<button class="btn btn-warning ms-1 me-1 mt-1" id="corCd'+arr.data[i]+'" onclick="followCourseCode(\''+arr.data[i]+'\')">'+arr.data[i]+'</button>';
        }else{
            document.getElementById('codeSelector').innerHTML += '<button class="btn btn-primary ms-1 me-1 mt-1" id="corCd'+arr.data[i]+'" onclick="followCourseCode(\''+arr.data[i]+'\')">'+arr.data[i]+'</button>';
        }  
    }
}

async function getCourseCodes(apiKey, courseCode) {
    let body = {
        key: apiKey,
        course_code: courseCode
    };

    let currentDomain = window.location.origin;
    let apiUrl = currentDomain + "/api/resource";

    return $.ajax({
        url: apiUrl,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(body)
    });
}

function showSelected(){
    $('#codeSelector').html('');
    for(let i = 0; i < arr.data.length; i++){
        if(localStorage.getItem('courseCodesStor') && localStorage.getItem('courseCodesStor').includes(arr.data[i])){
            document.getElementById('codeSelector').innerHTML += '<button class="btn btn-warning ms-1 me-1 mt-1" id="corCd'+arr.data[i]+'" onclick="followCourseCode(\''+arr.data[i]+'\')">'+arr.data[i]+'</button>';
        }else{
            document.getElementById('codeSelector').innerHTML += '<button class="btn btn-primary ms-1 me-1 mt-1" id="corCd'+arr.data[i]+'" onclick="followCourseCode(\''+arr.data[i]+'\')">'+arr.data[i]+'</button>';
        }  
    }
}

function followCourseCode(courseID){
    if(document.getElementById('corCd'+courseID).classList.contains('btn-primary')){
        document.getElementById('corCd'+courseID).classList.add('btn-warning');
        document.getElementById('corCd'+courseID).classList.remove('btn-primary');

        document.getElementById('selectedCourseCodes').value = document.getElementById('selectedCourseCodes').value+courseID+';';
        localStorage.setItem('courseCodesStor', document.getElementById('selectedCourseCodes').value);
    }else{
        document.getElementById('corCd'+courseID).classList.add('btn-primary');
        document.getElementById('corCd'+courseID).classList.remove('btn-warning');

        let midlist = document.getElementById('selectedCourseCodes').value.split(";");
        document.getElementById('selectedCourseCodes').value = "";
        for(let i = 0; i < midlist.length-1; i++){
            if(midlist[i] != courseID){
                document.getElementById('selectedCourseCodes').value += midlist[i]+';';
            }
        }
        localStorage.setItem('courseCodesStor', $('#selectedCourseCodes').val());
    }
    $('#courseCodeLength').html('Kiválasztva: '+($('#selectedCourseCodes').val().split(';').length-1).toString()+' db - pld: '+localStorage.getItem('courseCodesStor').split(';')[0].toString());
}