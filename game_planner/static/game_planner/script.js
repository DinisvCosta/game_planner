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

function reply(func, state, pk, elem) {
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove friend_request from page
            elem.parentNode.parentNode.removeChild(elem.parentNode);
        }
    };

    xhttp.open("POST", func, true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        friend_request: pk,
        state: state
    }

    xhttp.send(JSON.stringify(message));
}