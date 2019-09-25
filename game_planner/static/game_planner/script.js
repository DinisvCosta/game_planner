function mark_as_read(notification_id, elem) {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // Remove notification from page
            elem.parentNode.parentNode.removeChild(elem.parentNode);

            // Using the element id, change item color and remove mark as read button from the notification in the dropdown

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

function mark_all_as_read() {

    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            console.log("all notifications marked as read!");
        }
    }

    xhttp.open("POST", "/mark_all_as_read/", true);

    //Send the proper header information along with the request
    xhttp.setRequestHeader("Content-Type", "application/json");
    xhttp.setRequestHeader("X-CSRFToken", csrftoken);

    xhttp.send();
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

    if(notifications.length === 0) {
        var text_paragraph = document.createElement('p');
        text_paragraph.className = "d-flex justify-content-center default-top-spacer";
        var notif_text = document.createTextNode("You have no notifications.");
        text_paragraph.appendChild(notif_text);
        notification_list.appendChild(text_paragraph);
    }

    for(var i = notifications.length - 1; i >= 0; i--) {
        var notif_li = document.createElement('li');
        var text_paragraph = document.createElement('p');

        var text;

        if(notifications[i].notification_type === 0) {
            text = "<a href=\"" + notifications[i].user_href + "\">" + notifications[i].username + "</a> wants to be your friend.";
        } else if (notifications[i].notification_type === 1) {
            text = "<a href=\"" + notifications[i].user_href + "\">" + notifications[i].username + "</a> wants to join " + "<a href=\"" + notifications[i].game_href + "\">" + notifications[i].game_name + "</a>."
        } else if (notifications[i].notification_type === 2) {
            text = "<a href=\"" + notifications[i].user_href + "\">" + notifications[i].username + "</a> accepted your friend request.";
        } else if (notifications[i].notification_type === 3) {
            text = "You've been added to " + "<a href=\"" + notifications[i].game_href + "\">" + notifications[i].game_name + "</a>."
        }

        text_paragraph.innerHTML = text;

        var time_paragraph = document.createElement('p');
        time_paragraph.className = "time";

        var date = new Date(notifications[i].creation_datetime);

        var simple_date_string = date.toLocaleDateString("pt-PT");

        var detailed_options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        var detailed_date_string = date.toLocaleDateString("pt-PT", detailed_options);

        var notif_time = document.createTextNode(simple_date_string);

        time_paragraph.appendChild(notif_time);
        time_paragraph.title = detailed_date_string;

        if(notifications[i].read) {
            notif_li.className = "list-group-item";
            notif_li.appendChild(text_paragraph);
            notif_li.appendChild(time_paragraph);

            notification_list.appendChild(notif_li);
        } else {
            notif_li.className = "list-group-item list-group-item-secondary";
            
            notif_li.appendChild(text_paragraph);

            // buttons div
            var buttons_div = document.createElement('div');
            buttons_div.className = "col text-right";

            // Mark as read button
            var mark_as_read_button = document.createElement('a');
            mark_as_read_button.href = "";
            mark_as_read_button.className = "default-left-spacer";
            mark_as_read_button.id = "markAsReadButton";

            // TODO
            // mark as read changes the class of the li element to remove the secondary item and removes the buttons
            mark_as_read_button.onclick = function() { mark_as_read(notifications[i].id, "markAsReadButton"); }

            var mark_as_read_icon = document.createElement('i');
            mark_as_read_icon.className = "fas fa-check";
            mark_as_read_icon.title = "Mark as read";

            mark_as_read_button.appendChild(mark_as_read_icon);

            // Go to button
            if(notifications[i].notification_type === 0) {
                var go_to_button = document.createElement('a');
                
                go_to_button.href = "/"
                                    + "friend_requests"
                                    + "/?notif_id="
                                    + notifications[i].id;
            } else if (notifications[i].notification_type === 1) {
                var go_to_button = document.createElement('a');

                go_to_button.href = "/"
                                    + "manage_game"
                                    + "/"
                                    + notifications[i].game
                                    + "/?notif_id="
                                    + notifications[i].id;
            }

            if(go_to_button) {
                var go_to_icon = document.createElement('i');
                go_to_icon.className = "fas fa-external-link-alt";
                go_to_icon.title = "Go to";
                    
                go_to_button.appendChild(go_to_icon);
                buttons_div.appendChild(go_to_button);
                go_to_button = "";
            }

            buttons_div.appendChild(mark_as_read_button);
            notif_li.appendChild(buttons_div);
            notif_li.appendChild(time_paragraph);
            notification_list.appendChild(notif_li);
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