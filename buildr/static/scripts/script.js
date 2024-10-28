
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    console.log("sidebar called");
  
    
    if (sidebar.classList.contains('hidden')) {
        // Show the sidebar and adjust content
        sidebar.classList.remove('hidden');
        sidebar.classList.add('visible');
        content.classList.remove('expanded');
        content.classList.add('compressed');
        console.log("sidebar called 1");
        sidebarToggle.style.display = 'none'; // Hide the toggle button
    } else {
        // Hide the sidebar and adjust content
        sidebar.classList.remove('visible');
        sidebar.classList.add('hidden');
        content.classList.remove('compressed');
        content.classList.add('expanded');
        sidebarToggle.style.display = 'block'; // Show the toggle button
    }
}

// for comments sidebar
function toggleComments() {
    const commentsSidebar = document.getElementById('commentsSidebar');
    const content = document.getElementById('content');
    const commentsToggle = document.getElementById('commentsToggle');
    // const sidebar=document.getElementById('sidebar'); //the navbar
    // const sidebarToggle = document.getElementById('sidebar-toggle');
    // if (sidebar.classList.contains('visible')) {
    //     sidebar.classList.remove('visible');
    //     sidebar.classList.add('hidden');
    //     content.classList.remove('compressed');
    //     content.classList.add('expanded');
    //     sidebarToggle.style.display = 'block';
    // }
    if (commentsSidebar.classList.contains('hidden')) {
        // Show the sidebar and adjust content
        commentsSidebar.classList.remove('hidden');
        commentsSidebar.classList.add('visible');
        content.classList.remove('expanded_comments');
        content.classList.add('compressed_comments');
        commentsToggle.style.display = 'none'; 
    } 
  
    else {
        // Hide the sidebar and adjust content
        commentsSidebar.classList.remove('visible');
        commentsSidebar.classList.add('hidden');
        content.classList.remove('compressed_comments');
        content.classList.add('expanded_comments');
        commentsToggle.style.display = 'block';// Show the toggle button
        // sidebar.classList.remove('hiddeen');
        // sidebar.classList.add('visible');
    }
}


$(document).ready(function(){
    
    var multipleCancelButton = new Choices('#choices-multiple-remove-button', {
       removeItemButton: true,
       searchResultLimit:5,
     }); 
    
    
});

$(document).ready(function(){
    var $j = jQuery.noConflict();
    $j('.input-daterange').datepicker({
        format: 'dd-mm-yyyy',
        autoclose: true,
        calendarWeeks : true,
        clearBtn: true,
        disableTouchKeyboard: true
    });
    
    });


$(document).ready(function(){
    $('#start').datepicker({
        format: 'dd-mm-yyyy',  // Set format to match the backend expectation
        autoclose: true
    });
});
$(document).ready(function(){
    $('#end').datepicker({
        format: 'dd-mm-yyyy',  // Set format to match the backend expectation
        autoclose: true
    });
});



var googleUser = {};
var startApp = function() {
  gapi.load('auth2', function(){
    // Retrieve the singleton for the GoogleAuth library and set up the client.
    auth2 = gapi.auth2.init({
      client_id: 'YOUR_CLIENT_ID.apps.googleusercontent.com',
      cookiepolicy: 'single_host_origin',
      // Request scopes in addition to 'profile' and 'email'
      //scope: 'additional_scope'
    });
    attachSignin(document.getElementById('customBtn'));
  });
};

function attachSignin(element) {
  console.log(element.id);
  auth2.attachClickHandler(element, {},
      function(googleUser) {
        document.getElementById('name').innerText = "Signed in: " +
            googleUser.getBasicProfile().getName();
      }, function(error) {
        alert(JSON.stringify(error, undefined, 2));
      });
}


// get morale
function get_morale(issueId) {
    $.ajax({
        url: "/get-morale/",  
        method: "POST",
        data: {
            'issue_id': issueId,
            'csrfmiddlewaretoken': '{{ csrf_token }}'
        },
        success: function(response) {
            if (response.success) {
            
                alert(`
                    Overall Sentiment: ${response.overall_sentiment}
                   
                `);
            } else {
                alert('Failed to fetch the sentiment analysis.');
            }
        },
        error: function(xhr, status, error) {
            alert('Error occurred: ' + error);
        }
    });
}



function copyTextClipboard() {
  
    var copyText = document.getElementById("code");

    copyText.select();
    copyText.setSelectionRange(0, 99999); 
  
   
    navigator.clipboard.writeText(copyText.value);
  
    var successMessage = document.getElementById("copySuccessMessage");
            successMessage.style.display = "block";

           
            setTimeout(function() {
                successMessage.style.display = "none";
            }, 2000);
       
  }


  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.querySelector('.toggle-btn');
    const descriptionContainer = document.querySelector('.description-container');

    toggleButton.addEventListener('click', function() {
        // Toggle the expanded class
        descriptionContainer.classList.toggle('description-expanded');

        if (descriptionContainer.classList.contains('description-expanded')) {
            toggleButton.textContent = '▲ Show less';
        } else {
            toggleButton.textContent = '▼ Show more';
        }
    });
});


// send email form


// Search icon click event
document.getElementById("search-icon").addEventListener("click", function() {
    const searchInput = document.getElementById("search-input");
    const searchIcon = document.getElementById("search-icon");
    
    // Show the search input and cancel icon, then focus on the input
    searchInput.classList.remove("d-none");
    searchIcon.classList.add("d-none");
    searchInput.focus();
});

// Cancel icon click event
// document.getElementById("cancel-icon").addEventListener("click", function() {
//     const searchInput = document.getElementById("search-input");
//     const searchIcon = document.getElementById("search-icon");

    
//     // Hide the search input and cancel icon
//     searchInput.classList.add("d-none");
//     searchIcon.classList.remove("d-none");
    
//     // Optional: clear the search input
//     searchInput.value = "";
// });
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

function cancelSearch() {
    const searchInputGroup = document.getElementById('search-input');
    const searchField = searchInputGroup.querySelector('input[name="search-input"]');
    const searchIcon = document.getElementById("search-icon");
    // Hide the search input group
    searchInputGroup.classList.add('d-none');
    searchIcon.classList.remove("d-none");
    // Clear the search field
    searchField.value = '';
} 

document.querySelector('#search-input input[name="search-input"]').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();  
        this.form.submit();      
    }
});