$(document).bind("scroll", scrolling);

let last_id = -1;
let inpCount = 3;
let block = false; // block live loading posts
let tournamentId = window.location.pathname.split('/')[2];
let statusPost = 1;

window.onload = loader;

function scrolling() {
    if (($(window).scrollTop() === $(document).height() - $(window).height()) && !block) {
        loader();
    }
}


$(document).ready(function () {
    let dropDownMenu = $('.dropdown'); // menu of selecting posts' filter
    let currentStatus = dropDownMenu.children('button#dropdownMenuButton');
    let allStatusButtons = dropDownMenu.find('button.dropdown-item');
    let container = $('#post_container');
    allStatusButtons.bind('click', function (target) {
        currentStatus.html($(target.target).html());
        statusPost = parseInt($(target.target).val(), 10);
        container.empty();
        reloadLoader();
    });

    let subscribeEmailInput = $('#subscribe-email-input');
    let subscribeVkInput = $('#subscribe-vk-input');
    // email notification turn on/off
    subscribeEmailInput.bind('change', function () {
        let status;
        if (this.checked) {
            status = 1;
        } else {
            status = 0
        }
        $.ajax({
            url: '/subscribe-email-tour',
            type: 'POST',
            data: {status: status, tour_id: tournamentId},
            error: holdErrorResponse,
        });
    });
    // VK notification turn on/off
    subscribeVkInput.bind('change', function () {
        let status;
        if (this.checked) {
            status = 1;
        } else {
            status = 0
        }
        $.ajax({
            url: '/subscribe-vk-tour',
            type: 'POST',
            data: {status: status, tour_id: tournamentId},
            error: holdErrorResponse,
        });
    });
});

function reloadLoader() { // reset settings of loading posts
    last_id = -1;
    block = false;
    loader();
}

function generateTemplateCard(card, title, content, datetime_info, post_id, status, now, tour_id) {
    // completing post card
    card.children(".title").html(title);
    card.children('.content').html(content);
    card.children(".datetime_info").html(datetime_info);
    card.data("post_id", post_id);
    card.data("status", status);
    card.data("now", now);
    card.data("tour_id", tour_id)
}

function loader() { // function for live loading posts
    if (block) {
        return
    }
    block = true;
    let type;
    // get post's status
    switch (statusPost) {
        case 0:
            type = 'hidden';
            break;
        case 1:
            type = 'visible';
            break;
        case 10:
            type = 'all';
            break;
    }
    let url = `tournament/${tournamentId}/posts?type=${type}&offset=${inpCount}`;
    if (~last_id) {
        url += `&last_id=${last_id}`;
    }

    $.ajax({
            url: API_URL + url,
            type: 'GET',
            error: holdErrorResponse,
        }
    ).done(function (data) {
        let container = $('#post_container');
        let posts = data.posts;

        posts.forEach(post => {
            let card;
            if (post.status === 1) { // checking if post is visible
                card = $(document.querySelector('template#visible-card-post').content).children(".post_card").clone();
            } else if (post.status === 0) { // checking if post is invisible
                card = $(document.querySelector('template#not-visible-card-post').content).children(".post_card").clone();
            }
            // create a post card
            generateTemplateCard(card, post.title, post.content,
                post.created_info, post.id, post.status, post.now, post.tournament.id);
            container.prepend(card); // adding post in container
        });
        // checking loading process
        if (posts.length < inpCount) {
            block = true;
        } else {
            last_id = posts.pop().id;
            block = false
        }
    });
}

$(document).on('click', '.edit', function (event) {
    // opening post's edit page
    let targetElem = $(event.target);
    let card = targetElem.parents('div.post_card');
    let postId = card.data('post_id');
    window.location.href = `/tournament/${tournamentId}/edit_post/${postId}`;
});

$(document).on('click', '.hide', function (event) {
    // editing post's status (visible/invisible)
    let targetElem = $(event.target);
    let container = $('#post_container');
    let card = targetElem.parents('div.post_card');

    let title = card.find('.title').html();
    let content = card.find('.content').html();
    let dateTimeInfo = card.find('.datetime_info').html();
    let postId = card.data('post_id');
    let status = card.data('status');
    let tourId = card.data('tour_id');
    let now = card.data('now');

    let newStatus;
    if (status === 0) {
        newStatus = 1;
    } else if (status === 1) {
        newStatus = 0;
    }

    let data = {
        tour_id: tourId,
        post_id: postId
    };
    $.ajax({  // changing post's status
        url: API_URL + `post/${postId}`,
        type: 'PUT',
        data: {
            status: newStatus
        },
        error: holdErrorResponse,
    }).done(function () {
        if (now) {
            now = false;
            notifications(data, true);  // sending email & VK notifications about a new post
        }
        if (statusPost === 10) { // checking if post's filter is 'all'
            card.empty();
            if (newStatus === 0) {
                card.html($($('template#not-visible-card-post').html()).html());
            } else if (newStatus === 1) {
                card.html($($('template#visible-card-post').html()).html());
            }
            generateTemplateCard(card, title, content, dateTimeInfo, postId, newStatus, now, tourId);
        } else {
            card.remove();
        }
        if (container.children('div').length === 0) {
            reloadLoader();
        }
    });
});


$(document).on('click', '.delete', function (event) {
    // deleting post
    let targetElem = $(event.target);
    let card = targetElem.parents('div.post_card');
    let postId = card.data('post_id');
    let container = $('#post_container');
    $.ajax({
        url: API_URL + `post/${postId}`,
        type: 'DELETE',
        error: holdErrorResponse,
    }).done(function () {
        card.remove();
    }).always(function () {
        if (container.children('div').length === 0) {
            reloadLoader();
        }
    });
});