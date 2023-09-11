function getCourseCodes(apiKey, courseCode) {
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
    $.ajax({
        url: apiUrl,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(body), // Convert the data to a JSON string
        success: function (data, status) {
            // Handle the response data (JSON) here
            console.log(data);
        },
        error: function (xhr, textStatus, errorThrown) {
            // Handle any errors here
            console.error(xhr.statusText);
            console.log(xhr)
        }
    });
}