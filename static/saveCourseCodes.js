const inputField = document.getElementById('codeSearchField');

let typingTimer;
const doneTypingInterval = 1000;

inputField.addEventListener('input', function () {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () {
        // User has finished typing, perform request
        console.log('User finished typing');
        if(($('#codeSearchField').val() !== '' || $('#codeSearchField').val() !== ' ') && $('#codeSearchField').val().length >= 3){
            calcCodePicker($('#codeSearchField').val());
        }
    }, doneTypingInterval);
});

async function calcCodePicker(text){
    try{
        arr = await getCourseCodes($('#apiKeyHolder').val(), text);
    }catch (e){
        console.log('Error with API: '+e);
        return;
    }
    document.getElementById('codeSelector').innerHTML = '';
    for(let i = 0; i < arr.data.length; i++){
        document.getElementById('codeSelector').innerHTML += '<div class="row"><div class="col-8"><p>'+arr.data[i]+'</p></div><div class="col-4"><button class="btn btn-primary" onclick="followCourseCode(\''+arr.data[i]+'\')">Kiválaszt</button></div></div>';
    }
}

async function getCourseCodes(apiKey, courseCode) {
    // Create a JSON object with the API key and course code
    let body = {
        key: apiKey,
        course_code: courseCode
    };

    // Get the current domain (origin) of the web page
    let currentDomain = window.location.origin;

    // Construct the API endpoint URL
    let apiUrl = currentDomain + "/api/resource";

    // Set up AJAX settings to send a JSON request
    return $.ajax({
        url: apiUrl,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(body)
    });
}

function followCourseCode(courseID){
    console.log(courseID);
}