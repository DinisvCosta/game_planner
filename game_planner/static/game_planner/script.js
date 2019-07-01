function mark_as_read(notification_id) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            console.log(xhttp.responseText);
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

function confirm_friend_request(from, to) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            console.log(xhttp.responseText);
        }
    };

    xhttp.open("POST", "/friend_requests/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        request_from: from,
        request_to: to,
        state: "accepted"
    }

    xhttp.send(JSON.stringify(message));
}

function delete_friend_request(from, to) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            console.log(xhttp.responseText);
        }
    };

    xhttp.open("POST", "/friend_requests/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        request_from: from,
        request_to: to,
        state: "declined"
    }

    xhttp.send(JSON.stringify(message));
}
