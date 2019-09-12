function mark_as_read(notification_id, elem) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove notification from page
            elem.parentNode.parentNode.removeChild(elem.parentNode);
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

function get_notifications() {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            make_notification_list(xhttp.responseText); 
        }
    };

    xhttp.open("GET", "/get_notifications/", true);
    xhttp.send();
}

function make_notification_list(notification_json) {
    var notifications = JSON.parse(notification_json);

    var notification_list = document.createElement('ul');
    notification_list.className = "list-group";

    for(notif in notifications) {
        var notif_li = document.createElement('li');

        var text_paragraph = document.createElement('p');
        var notif_text = document.createTextNode(notifications[notif].fields.text);

        text_paragraph.appendChild(notif_text);

        var time_paragraph = document.createElement('p');
        time_paragraph.className = "time";

        // TODO
        // use moment.js to format date:
        // ie. "1 week ago" text in the paragraph and "Tuesday, October 1, 2019" as paragraph title
        var notif_time = document.createTextNode(notifications[notif].fields.creation_datetime);

        time_paragraph.appendChild(notif_time);

        if(notifications[notif].fields.read) {
            notif_li.className = "list-group-item";
            notif_li.appendChild(text_paragraph);
            notif_li.appendChild(time_paragraph);

            notification_list.appendChild(notif_li);
        } else {
            notif_li.className = "list-group-item list-group-item-secondary";
            
            notif_li.appendChild(text_paragraph);

            // TODO
            // add "Mark as read" button
            // if notif has target url add "Go to" button

            notif_li.appendChild(time_paragraph);
        }
    }

    dropdown_content = document.getElementById("notificationsDropdownContent");

    setTimeout(function(){ 
        document.getElementById("notificationDropdownLoadingSpinner").outerHTML = "";
        dropdown_content.appendChild(notification_list);
    }, 1000);

}

function reply(func, state, pk, elem) {
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove request from page
            elem.parentNode.parentNode.removeChild(elem.parentNode);
        }
    };

    xhttp.open("POST", func, true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    message = 
    {
        request: pk,
        state: state
    }

    xhttp.send(JSON.stringify(message));
}