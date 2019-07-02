function mark_as_read(notification_id) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove notification from page
            var notification_element = "notification_" + notification_id
            document.getElementById(notification_element).outerHTML = "";
        }
    };

    xhttp.open("POST", "/notification_read/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        notification_id: notification_id,
    }

    xhttp.send(JSON.stringify(message));
}

function confirm_friend_request(pk) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove friend_request from page
            var name_element_id = "request_" + pk
            var confirm_button_id = "request_" + pk + "_confirm_button"
            var delete_button_id = "request_" + pk + "_delete_button"

            document.getElementById(name_element_id).outerHTML = "";
            document.getElementById(confirm_button_id).outerHTML = "";
            document.getElementById(delete_button_id).outerHTML = "";
        }
    };

    xhttp.open("POST", "/friend_requests/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        friend_request: pk,
        state: "accepted"
    }

    xhttp.send(JSON.stringify(message));
}

function delete_friend_request(pk) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove friend_request from page
            var name_element_id = "request_" + pk
            var confirm_button_id = "request_" + pk + "_confirm_button"
            var delete_button_id = "request_" + pk + "_delete_button"

            document.getElementById(name_element_id).outerHTML = "";
            document.getElementById(confirm_button_id).outerHTML = "";
            document.getElementById(delete_button_id).outerHTML = "";
        }
    };

    xhttp.open("POST", "/friend_requests/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        friend_request: pk,
        state: "declined"
    }

    xhttp.send(JSON.stringify(message));
}
