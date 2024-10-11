
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    
  
    
    if (sidebar.classList.contains('hidden')) {
        // Show the sidebar and adjust content
        sidebar.classList.remove('hidden');
        sidebar.classList.add('visible');
        content.classList.remove('expanded');
        content.classList.add('compressed');
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


// get morale
function get_morale(issueId) {
    $.ajax({
        url: "/get-morale/",  // Replace with the correct URL pattern
        method: "POST",
        data: {
            'issue_id': issueId,
            'csrfmiddlewaretoken': '{{ csrf_token }}'
        },
        success: function(response) {
            if (response.success) {
                // Display the sentiment as an alert
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
        
        // Change the button text accordingly
        if (descriptionContainer.classList.contains('description-expanded')) {
            toggleButton.textContent = '▲ Show less';
        } else {
            toggleButton.textContent = '▼ Show more';
        }
    });
});